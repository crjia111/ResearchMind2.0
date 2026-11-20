import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
from agentscope.model import OpenAIChatModel
from agentscope.credential import OpenAICredential
from agentscope.message import UserMsg, ToolResultState
from researchmind_skills.api import Runtime, create_local_context
from researchmind_skills.adapters.agentscope.factory import create_agent, ROLE_SKILLS
from researchmind_skills.adapters.agentscope.bindings import (
    build_bound_tools,
    to_tool_chunk,
)
from researchmind_skills.runtime.contracts import failure, CapabilityError
from researchmind_skills.runtime.store import Store


def test_failure_maps_to_real_framework_error():
    response = failure(
        "simulation.energy", "r", CapabilityError("MODEL_NOT_FOUND", "missing")
    )
    chunk = to_tool_chunk(response)
    assert chunk.state == ToolResultState.ERROR
    assert chunk.metadata["researchmind_result"] == response


def test_structured_tools_are_deduplicated_and_match_schema(tmp_path):
    runtime = Runtime()
    ctx = create_local_context(tmp_path)
    tools = build_bound_tools(runtime, ctx, ROLE_SKILLS["deep_research_agent"])
    names = [t.name for t in tools]
    assert len(names) == len(set(names))
    assert names.count("rm_papers_export_csv") == 1
    tool = next(t for t in tools if t.name == "rm_papers_content_read_segment")
    assert (
        tool.input_schema
        == runtime.describe("papers.content.read_segment")["input_schema"]
    )
    assert "rm_simulation_relax" not in names


@pytest.mark.asyncio
async def test_actual_agentscope_tool_loop_with_local_model_protocol(tmp_path):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            tool_messages = [m for m in body["messages"] if m["role"] == "tool"]
            if not tool_messages:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "test-export",
                            "type": "function",
                            "function": {
                                "name": "rm_papers_export_csv",
                                "arguments": json.dumps(
                                    {
                                        "records": [
                                            {"paper_id": "p1", "title": "Test paper"}
                                        ]
                                    }
                                ),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            else:
                message = {"role": "assistant", "content": "已导出文献列表。"}
                reason = "stop"
            response = {
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "local-test",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            }
            data = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        model = OpenAIChatModel(
            credential=OpenAICredential(
                api_key="local-test",
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
            ),
            model="local-test",
            stream=False,
            max_retries=0,
        )
        ctx = create_local_context(tmp_path)
        agent = create_agent("deep_research_agent", Runtime(), ctx, model)
        events = [
            e
            async for e in agent.reply_stream(
                UserMsg(
                    name="user",
                    content="Export this existing list; do not analyze or write a report.",
                )
            )
        ]
        results = [e for e in events if getattr(e, "type", None) == "TOOL_RESULT_END"]
        assert results
        assert results[0].metadata["researchmind_result"]["status"] == "completed"
        artifact = results[0].metadata["researchmind_result"]["artifacts"][0][
            "artifact_id"
        ]
        assert "Test paper" in Store(ctx).resolve(artifact).read_text()
        assert len(requests) == 2
        assert [x["function"]["name"] for x in requests[0]["tools"]].count(
            "rm_papers_export_csv"
        ) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
