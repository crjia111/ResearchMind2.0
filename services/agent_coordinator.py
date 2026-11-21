"""AgentScope host coordinator with durable, framework-neutral scientific state."""

import asyncio
import json
import logging
from collections import defaultdict
from researchmind_skills.runtime.store import Store
from .skill_runtime import context_for, configured_model
from .session_manager import SessionManager
from .message_handler import MessageHandler
from .usage_stats import get_usage_service
from .local_context import LOCAL_USER_ID
from .agent_runtime import get_runtime

logger = logging.getLogger(__name__)


class AgentCoordinator:
    def __init__(self, agents=None, agent_runtime=None, scientific_runtime=None):
        from researchmind_skills.api import Runtime

        self.runtime = scientific_runtime or Runtime()
        self.agent_runtime = agent_runtime or get_runtime(scientific_runtime=self.runtime)
        runtime_agents = self.agent_runtime.capabilities().agent_ids
        self.agents = agents or {role: role for role in runtime_agents}
        self.active_tasks = {}
        self.instances = {}
        self.locks = defaultdict(asyncio.Lock)

    async def process_chat_message(
        self,
        client_id,
        websocket,
        content,
        agent_id,
        session_id=None,
        retry_count=0,
        attachments=None,
        allow_router=True,
    ):
        key = (client_id, agent_id, session_id)
        async with self.locks[(agent_id, session_id)]:
            task = asyncio.current_task()
            self.active_tasks[key] = task
            try:
                context = context_for(session_id)
                store = Store(context)

                async def scientific_event(event):
                    if event.get("type") == "job_status":
                        await MessageHandler.send_message(
                            websocket,
                            "status",
                            {
                                "status": "working",
                                "message": "Scientific task " + event["status"],
                                "sessionId": session_id,
                                "jobId": event["job_id"],
                            },
                        )
                        return
                    if event.get("type") != "capability_result":
                        return
                    response = event["result"]
                    await MessageHandler.send_message(
                        websocket,
                        "tool_result",
                        {
                            "sessionId": session_id,
                            "agentId": agent_id,
                            "result": response,
                        },
                    )
                    for call in response.get("usage", {}).get("model_calls", []):
                        tokens = call.get(
                            "total_tokens",
                            call.get("prompt_tokens", 0)
                            + call.get("completion_tokens", 0),
                        )
                        get_usage_service().record_token_usage(
                            session_id,
                            LOCAL_USER_ID,
                            tokens,
                            call.get("model", "unknown"),
                        )
                    for artifact in response.get("artifacts", []):
                        ident = artifact["artifact_id"]
                        path = store.resolve(ident)
                        url = f"/api/skills/artifacts/{session_id}/{ident}"
                        kind = artifact["kind"]
                        if kind == "markdown":
                            kind = "md"
                        await MessageHandler.send_message(
                            websocket,
                            "file_data",
                            {
                                "sessionId": session_id,
                                "agentId": agent_id,
                                "files": [
                                    {
                                        "name": path.name,
                                        "type": kind,
                                        "downloadUrl": url,
                                        "url": url,
                                        "filePath": ident,
                                    }
                                ],
                            },
                        )
                        if kind in ("csv", "md"):
                            metadata = {
                                (
                                    "csv_download_url"
                                    if kind == "csv"
                                    else "md_download_url"
                                ): url,
                                (
                                    "csv_file_path"
                                    if kind == "csv"
                                    else "report_file_path"
                                ): ident,
                            }
                            await MessageHandler.send_message(
                                websocket,
                                "file_metadata",
                                {
                                    "agentId": agent_id,
                                    "sessionId": session_id,
                                    "metadata": metadata,
                                },
                            )
                        if kind == "cif":
                            from .structure_converter import StructureConverter

                            structure = StructureConverter.convert_cif_to_structure(
                                path.read_text(encoding="utf-8"),
                                path.stem,
                                path.stem,
                                "Computed",
                            )
                            if structure:
                                await MessageHandler.send_message(
                                    websocket,
                                    "structure_data",
                                    {
                                        "structures": [structure],
                                        "sessionId": session_id,
                                    },
                                )
                        if kind in ("png", "jpg", "jpeg", "svg"):
                            await MessageHandler.send_message(
                                websocket,
                                "image_data",
                                {"url": url, "imageUrl": url, "sessionId": session_id},
                            )

                context.event_sink = scientific_event
                if agent_id not in self.agents:
                    raise ValueError("Unknown agent")
                # Always restore the latest durable state, including after a client reconnect.
                model = configured_model()
                state = None
                saved = store.get("agent-state:" + agent_id)
                if saved and (
                    saved.get("runtime_id") == self.agent_runtime.runtime_id
                    or saved.get("adapter") == "agentscope-2.0.12"
                ):
                    state = saved.get("state")
                agent = self.agent_runtime.create_session(
                    agent_id, context, model, state=state
                )
                if state is None:
                    from researchmind_skills.runtime.history import normalize_history

                    old = normalize_history(SessionManager.load_history(session_id))
                    agent.restore_history(old[-16:])
                self.instances[key] = agent
                references = []
                for attachment in attachments or []:
                    candidate = (
                        attachment.get("path")
                        or attachment.get("file_path")
                        or attachment.get("filePath")
                    )
                    if candidate:
                        artifact = store.import_file(candidate)
                        references.append(artifact)
                    elif attachment.get("content"):
                        name = (
                            __import__("pathlib")
                            .Path(attachment.get("filename", "upload.cif"))
                            .name
                        )
                        references.append(
                            store.artifact(
                                name, attachment["content"], name.rsplit(".", 1)[-1]
                            )
                        )
                prompt = content + (
                    "\nUploaded artifacts: "
                    + json.dumps(references, ensure_ascii=False)
                    if references
                    else ""
                )
                await MessageHandler.send_message(
                    websocket,
                    "status",
                    {
                        "status": "working",
                        "sessionId": session_id,
                        "message": "正在研究...",
                    },
                )
                text = []
                tokens = 0
                tool_calls = []
                async for event in agent.run(prompt):
                    normal = event.to_dict()
                    if normal["type"] == "text_delta":
                        text.append(normal["text"])
                    elif normal["type"] == "usage":
                        count = normal["input_tokens"] + normal["output_tokens"]
                        tokens += count
                        get_usage_service().record_token_usage(
                            session_id, LOCAL_USER_ID, count
                        )
                    elif normal["type"] == "tool_result":
                        tool_calls.append(normal)
                    await MessageHandler.send_message(
                        websocket,
                        "agent_event",
                        {"agentId": agent_id, "sessionId": session_id, "event": normal},
                    )
                agent_state = agent.export_state()
                if agent_state is not None:
                    store.set(
                        "agent-state:" + agent_id,
                        {
                            "schema_version": "1.0",
                            "runtime_id": self.agent_runtime.runtime_id,
                            "state": agent_state,
                        },
                    )
                history = store.get("history", [])
                history.extend(
                    [
                        {"schema_version": "1.0", "role": "user", "content": content},
                        {
                            "schema_version": "1.0",
                            "role": "assistant",
                            "agent_id": agent_id,
                            "content": "".join(text),
                            "tool_calls": tool_calls,
                        },
                    ]
                )
                store.set("history", history)
                # Keep the existing history endpoint readable without overwriting legacy snapshots.
                SessionManager.save_history_summary(
                    session_id, {"schema_version": "1.0", "messages": history}
                )
                await MessageHandler.send_agent_response(
                    websocket,
                    agent_id,
                    "".join(text),
                    tool_calls=tool_calls,
                    billing={"tokens": tokens},
                )
            except asyncio.CancelledError:
                await MessageHandler.send_message(
                    websocket, "status", {"status": "stopped", "sessionId": session_id}
                )
            except Exception as exc:
                logger.exception("Agent runtime request failed")
                await MessageHandler.send_error(websocket, str(exc))
            finally:
                self.active_tasks.pop(key, None)
                await MessageHandler.send_message(
                    websocket, "status", {"status": "idle", "sessionId": session_id}
                )

    def stop_current_task(self, client_id, agent_id, session_id=None):
        for key, task in list(self.active_tasks.items()):
            if (
                key[0] == client_id
                and (not agent_id or key[1] == agent_id)
                and (not session_id or key[2] == session_id)
            ):
                task.cancel()

    def clear_session(self, client_id, agent_id, session_id=None):
        self.stop_current_task(client_id, agent_id, session_id)
        for key in list(self.instances):
            if (
                key[0] == client_id
                and key[1] == agent_id
                and (not session_id or key[2] == session_id)
            ):
                self.instances.pop(key, None)

    def clear_all_sessions(self, client_id):
        self.stop_current_task(client_id, None)
        self.instances = {k: v for k, v in self.instances.items() if k[0] != client_id}

    def get_session_count(self):
        return len(self.instances)

    def get_client_session_count(self, client_id):
        return sum(k[0] == client_id for k in self.instances)

    def get_session_info(self, client_id, agent_id, session_id=None):
        return {
            "agent_id": agent_id,
            "session_id": session_id,
            "runtime": self.agent_runtime.runtime_id,
        }
