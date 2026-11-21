"""AgentScope implementation of the host AgentRuntime contract."""

from collections.abc import AsyncIterator

from researchmind_skills.adapters.agentscope.events import normalized_event
from researchmind_skills.adapters.agentscope.factory import ROLE_SKILLS, create_agent
from agentscope.message import UserMsg

from .contracts import RuntimeCapabilities, RuntimeEvent, RuntimeStatus


class AgentScopeSession:
    def __init__(self, agent):
        self._agent = agent

    @property
    def state(self):
        return self._agent.state

    @property
    def context(self):
        return self._agent.state.context

    async def run(self, prompt: str) -> AsyncIterator[RuntimeEvent]:
        async for event in self._agent.reply_stream(UserMsg(name="user", content=prompt)):
            normalized = normalized_event(event)
            event_type = normalized.pop("type", "agent_event")
            yield RuntimeEvent(event_type, normalized)

    def export_state(self):
        state = getattr(self._agent, "state", None)
        if state is None:
            return None
        return state.model_dump(mode="json")

    def restore_history(self, messages):
        from agentscope.message import AssistantMsg, UserMsg

        for message in messages:
            if not message.get("content") or message.get("role") not in (
                "user",
                "assistant",
            ):
                continue
            message_type = UserMsg if message["role"] == "user" else AssistantMsg
            self.context.append(
                message_type(
                    name="user" if message["role"] == "user" else self._agent.name,
                    content=message["content"],
                )
            )


class AgentScopeRuntime:
    runtime_id = "agentscope"

    def __init__(self, scientific_runtime):
        self._scientific_runtime = scientific_runtime
        # The adapter is in-process; it is usable before the optional lifecycle
        # handshake that the host performs during startup.
        self._connected = True

    async def connect(self):
        self._connected = True

    def close(self):
        self._connected = False

    def status(self):
        return RuntimeStatus("ready" if self._connected else "disconnected")

    def capabilities(self):
        return RuntimeCapabilities(
            runtime_id=self.runtime_id,
            display_name="AgentScope",
            version="2.0.12",
            agent_ids=tuple(ROLE_SKILLS),
            features={"streaming": True, "session_state": True, "delegation": True},
        )

    def list_agents(self):
        return self.capabilities().agent_ids

    def create_session(self, agent_id, context, model, state=None):
        if isinstance(state, dict):
            from agentscope.state import AgentState

            state = AgentState.model_validate(state)
        agent = create_agent(
            agent_id,
            self._scientific_runtime,
            context,
            model,
            state=state,
        )
        return AgentScopeSession(agent)
