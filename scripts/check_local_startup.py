"""Exercise the real local stack on separate ports without external API calls."""

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from websockets.legacy.client import connect

ROOT = Path(__file__).resolve().parents[1]


async def check_websocket(port):
    async with connect(f"ws://127.0.0.1:{port}/ws/local-smoke", open_timeout=10) as ws:
        assert json.loads(await ws.recv())["type"] == "connected"
        assert json.loads(await ws.recv())["type"] == "agents_list"
        await ws.send(json.dumps({"type": "ping"}))
        assert json.loads(await ws.recv())["type"] == "pong"
        await ws.send(json.dumps({"type": "get_user_stats"}))
        stats = json.loads(await ws.recv())
        assert stats["data"]["data"]["user_id"] == "local_user"


def main():
    ports = []
    for port in range(50102, 50200):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                ports.append(port)
            except OSError:
                continue
        if len(ports) == 6:
            break
    if len(ports) != 6:
        raise RuntimeError("Six available local test ports are required")
    with tempfile.TemporaryDirectory(prefix="researchmind-local-check-") as folder:
        temp = Path(folder)
        config = temp / ".env"
        lines = ["MODEL_USE=openai/local-test", "OPENAI_API_KEY=local-test-not-a-secret",
                 "OPENAI_BASE_URL=http://127.0.0.1:9/v1", "TAVILY_API_KEY=", "MP_API_KEY=",
                 "GOOGLE_API_KEY=", "REDIS_HOST=127.0.0.1", "REDIS_PORT=1",
                 "VITE_API_URL=/api", "VITE_WS_URL=/ws", "VITE_API_PORT=", "VITE_WS_PORT=",
                 f"SESSION_DATA_ROOT={temp / 'sessions'}", f"PAPERS_ROOT={temp / 'papers'}",
                 f"PHONON_ROOT={temp / 'simulation'}", f"CHROMA_PERSIST_DIR={temp / 'chroma'}"]
        prefixes = ["RESEARCHMIND_HTTP", "RESEARCHMIND_WS", "PAPER_SEARCH_MCP",
                    "SIMULATION_MCP", "DATABASE_MCP", "VITE_FRONTEND"]
        for prefix, port in zip(prefixes, ports):
            lines.extend([f"{prefix}_HOST=127.0.0.1", f"{prefix}_PORT={port}"])
            if prefix.endswith("MCP"):
                lines.append(f"{prefix}_URL=http://127.0.0.1:{port}/sse")
        config.write_text("\n".join(lines) + "\n")
        env = os.environ.copy()
        env["RESEARCHMIND_LOG_DIR"] = str(temp / "logs")
        with open(temp / "launcher.log", "w+") as log:
            child = subprocess.Popen([sys.executable, "-m", "services.launcher", "--env-file", str(config), "--stop-file", str(temp / "stop")],
                                     cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 190
                while time.monotonic() < deadline:
                    log.flush()
                    output = (temp / "launcher.log").read_text()
                    if child.poll() is not None:
                        raise RuntimeError(output)
                    if "No login required." in output:
                        print(output, flush=True)
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError("Local startup timed out")
                origin = f"http://127.0.0.1:{ports[-1]}"
                with httpx.Client(base_url=origin, timeout=20, trust_env=False) as client:
                    assert client.get("/").status_code == 200
                    assert client.get("/api/health").json()["status"] == "healthy"
                    assert client.get("/api/usage/local").json()["data"]["user_id"] == "local_user"
                    assert client.get("/api/auth/me").status_code == 404
                    assert client.post("/api/billing/charge", json={}).status_code == 404
                asyncio.run(check_websocket(ports[-1]))
                print("PASS: real UI, API proxy, WebSocket proxy and local stats work without credentials", flush=True)
            finally:
                (temp / "stop").touch()
                child.wait(timeout=20)
            for port in ports:
                with socket.socket() as sock:
                    assert sock.connect_ex(("127.0.0.1", port)) != 0, f"Service left running on {port}"
            print("PASS: launcher stopped all test services", flush=True)


if __name__ == "__main__":
    main()
