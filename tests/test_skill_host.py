from researchmind_skills.runtime.store import Store
from services.skill_runtime import context_for
import json
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from services.http_server import HTTPServer
from services.session_manager import SessionManager
from services.launcher import endpoints, load_local_config


def test_default_launcher_has_no_mcp_processes(tmp_path):
    path = tmp_path / ".env"
    path.write_text("")
    assert [e[0] for e in endpoints(load_local_config(path))] == [
        "HTTP API",
        "WebSocket",
        "UI",
    ]


def test_portable_upload_selection_and_download(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEARCHMIND_WORKSPACE", str(tmp_path / "work"))
    monkeypatch.setattr(
        SessionManager,
        "get_session",
        lambda session: {"id": session} if session == "local-test" else None,
    )
    client = TestClient(HTTPServer().get_app())
    reply = client.post(
        "/api/upload/documents?session_id=local-test",
        files=[("files", ("论文.txt", "中文方法与研究结果".encode(), "text/plain"))],
    )
    assert reply.status_code == 200, reply.text
    body = reply.json()
    ids = [p["paper_id"] for p in body["papers"]]
    response = client.put(
        "/api/papers/selection?session_id=local-test", json={"paper_ids": ids}
    )
    assert response.status_code == 200
    assert (
        client.get("/api/papers/selection?session_id=local-test").json()["data"][
            "paper_ids"
        ]
        == ids
    )
    legacy = client.post(
        "/api/mcp/call_tool",
        json={
            "tool_name": "list_papers_from_csv",
            "arguments": {
                "session_id": "local-test",
                "csv_file_path": body["csv_file_path"],
            },
        },
    )
    assert legacy.json()["total_papers"] == 1
    file = client.get(body["csv_download_url"])
    assert file.status_code == 200 and "paper_id" in file.text
    assert (
        client.get(
            body["csv_download_url"].replace("local-test", "different")
        ).status_code
        == 400
    )
    assert client.get("/api/auth/me").status_code == 404
    assert client.post("/api/billing/charge", json={}).status_code == 404


@pytest.mark.asyncio
async def test_chat_returns_to_socket_reader_while_task_runs():
    from services.message_handler import MessageHandler
    from types import SimpleNamespace

    waiting = asyncio.Event()

    async def process(**kwargs):
        await waiting.wait()

    coordinator = SimpleNamespace(process_chat_message=AsyncMock(side_effect=process))
    await asyncio.wait_for(
        MessageHandler().handle_chat_message(
            "c",
            object(),
            {"content": "hello", "agentId": "deep_research_agent", "sessionId": "s"},
            coordinator,
        ),
        timeout=0.5,
    )
    await asyncio.sleep(0)
    coordinator.process_chat_message.assert_awaited_once()
    waiting.set()
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_coordinator_reconnect_restores_real_agentscope_state(
    monkeypatch, tmp_path
):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from agentscope.model import OpenAIChatModel
    from agentscope.credential import OpenAICredential
    from services.agent_coordinator import AgentCoordinator
    import services.agent_coordinator as coordinator_module

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            body = {
                "id": "reply",
                "object": "chat.completion",
                "created": 1,
                "model": "fixture",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "保存的研究结论。"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            }
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Socket:
        closed = False

        def __init__(self):
            self.messages = []

        async def send(self, value):
            self.messages.append(json.loads(value))

    monkeypatch.setenv("RESEARCHMIND_WORKSPACE", str(tmp_path / "work"))
    monkeypatch.setattr(SessionManager, "get_session", lambda session: {"id": session})
    monkeypatch.setattr(SessionManager, "load_history", lambda session: [])
    monkeypatch.setattr(SessionManager, "save_history_summary", lambda *a, **k: None)
    monkeypatch.setattr(
        coordinator_module,
        "configured_model",
        lambda: OpenAIChatModel(
            credential=OpenAICredential(
                api_key="test", base_url=f"http://127.0.0.1:{server.server_port}/v1"
            ),
            model="fixture",
            stream=False,
            max_retries=0,
        ),
    )
    try:
        first = Socket()
        await AgentCoordinator().process_chat_message(
            "first-client",
            first,
            "第一次研究",
            "deep_research_agent",
            "persistent-session",
        )
        assert any(m["type"] == "message" for m in first.messages)
        assert not any(m["type"] == "error" for m in first.messages)
        second = Socket()
        await AgentCoordinator().process_chat_message(
            "reconnected-client",
            second,
            "继续研究",
            "deep_research_agent",
            "persistent-session",
        )
        assert not any(m["type"] == "error" for m in second.messages)
        assert any(
            "第一次研究" in str(m.get("content")) for m in requests[-1]["messages"]
        )
        history = Store(context_for("persistent-session")).get("history")
        assert len(history) == 4
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
