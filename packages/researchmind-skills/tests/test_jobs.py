import asyncio
import subprocess
import sys
import time
import pytest
from researchmind_skills.api import Runtime, create_local_context
from researchmind_skills.runtime.store import Store
from test_runtime import CIF


@pytest.mark.asyncio
async def test_worker_accepts_and_persists_real_dependency_failure(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("MATTERSIM_MODEL_PATH", raising=False)
    worker = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "researchmind_skills.worker",
            "--workspace",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ctx = create_local_context(tmp_path, "job-session")
    store = Store(ctx)
    runtime = Runtime()
    try:
        for _ in range(100):
            with store.db() as db:
                alive = db.execute(
                    "SELECT 1 FROM workers WHERE heartbeat>?", (time.time() - 15,)
                ).fetchone()
            if alive:
                break
            await asyncio.sleep(0.05)
        assert alive
        response = await runtime.execute(
            "simulation.energy",
            {"cif_content": CIF},
            ctx,
            skill_name="structure-optimization",
            wait=False,
        )
        assert response["status"] == "accepted"
        job = response["job_id"]
        for _ in range(150):
            response = runtime.get_job_result(job, ctx)
            if response["status"] != "accepted":
                break
            await asyncio.sleep(0.05)
        assert response["status"] == "failed"
        assert response["error"]["code"] == "MODEL_NOT_FOUND"
        assert (
            Runtime().get_job_result(job, create_local_context(tmp_path, "job-session"))
            == response
        )
    finally:
        worker.terminate()
        worker.wait(timeout=10)


@pytest.mark.asyncio
async def test_compute_timeout_terminates_child_tree(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class SlowHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(5)
            try:
                self.send_response(500)
                self.end_headers()
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("OPENAI_API_KEY", "test-only")
        monkeypatch.setenv(
            "OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1"
        )
        ctx = create_local_context(tmp_path)
        store = Store(ctx)
        content = store.artifact("paper.txt", "Some scientific evidence.")
        store.set(
            "papers",
            [
                {
                    "paper_id": "p1",
                    "title": "Source",
                    "source": "arxiv",
                    "content_artifact_id": content["artifact_id"],
                    "evidence": "fulltext",
                }
            ],
        )
        result = await Runtime({"compute_timeout": 0.5}).execute(
            "papers.report",
            {"topic": "test", "paper_ids": ["p1"]},
            ctx,
            skill_name="research-report",
            wait=True,
        )
        assert result["status"] == "failed"
        assert result["error"]["code"] == "COMPUTE_TIMEOUT"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
