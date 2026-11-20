"""Regression checks for operation without platform credentials."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest
from websockets.legacy.client import connect
from websockets.server import serve

from services.http_server import HTTPServer
from services.launcher import check_ports, load_local_config
from services.local_context import LOCAL_USER_ID
from services.session_manager import SessionManager
from services.usage_context import ConversationUsageContextManager
from services.websocket_server import WebSocketServer


def test_http_works_without_credentials():
    app = HTTPServer().get_app()
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/usage/local").json()["data"]["user_id"] == LOCAL_USER_ID
    assert client.get("/api/usage/global").status_code == 200
    assert client.get("/api/auth/me").status_code == 404
    assert client.post("/api/billing/charge", json={}).status_code == 404
    assert not any(path.startswith(("/api/auth", "/api/billing")) for path in app.openapi()["paths"])


@pytest.mark.asyncio
async def test_websocket_accepts_chat_without_authentication(monkeypatch):
    monkeypatch.setattr(SessionManager, "get_session", lambda _: {"id": "test-session"})
    coordinator = SimpleNamespace(process_chat_message=AsyncMock())
    server = WebSocketServer(coordinator)
    async with serve(server.handle_client, "127.0.0.1", 0) as listener:
        port = listener.sockets[0].getsockname()[1]
        async with connect(f"ws://127.0.0.1:{port}/ws/test-client") as websocket:
            assert json.loads(await websocket.recv())["type"] == "connected"
            assert json.loads(await websocket.recv())["type"] == "agents_list"
            state = server.client_sessions["test-client"]
            assert state["user_id"] == LOCAL_USER_ID
            assert "cookie_credentials" not in state
            await websocket.send(json.dumps({"type": "chat", "content": "test local chat",
                                              "agentId": "deep_research_agent", "sessionId": "test-session"}))
            for _ in range(50):
                if coordinator.process_chat_message.await_count:
                    break
                await asyncio.sleep(0.01)
            coordinator.process_chat_message.assert_awaited_once()
            assert coordinator.process_chat_message.await_args.kwargs["content"] == "test local chat"
            await websocket.send(json.dumps({"type": "ping"}))
            assert json.loads(await websocket.recv())["type"] == "pong"


def test_local_usage_is_thread_safe_and_isolated():
    manager = ConversationUsageContextManager()
    first = manager.get_or_create_context("first", "old-client-id")
    second = manager.get_or_create_context("second", "another-client-id")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: first.update_token_usage(3), range(100)))
    second.update_token_usage(7)
    assert first.get_snapshot()["total_tokens"] == 300
    assert second.get_snapshot()["total_tokens"] == 7
    total = manager.get_user_total_usage()
    assert total["user_id"] == LOCAL_USER_ID
    assert total["total_tokens"] == 307
    assert total["total_requests"] == 101


def test_launcher_rejects_duplicate_ports(tmp_path):
    config = tmp_path / ".env"
    config.write_text("RESEARCHMIND_HTTP_PORT=50102\nRESEARCHMIND_WS_PORT=50102\n")
    env = load_local_config(config)
    with pytest.raises(RuntimeError, match="Duplicate port"):
        check_ports(env)
