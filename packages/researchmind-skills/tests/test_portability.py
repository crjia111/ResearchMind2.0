"""Build/install the real wheel into a clean Python with no Agent framework."""

import json
from pathlib import Path
import subprocess
import sys
import venv


def test_wheel_runs_outside_repository_without_frameworks(tmp_path):
    package = Path(__file__).resolve().parents[1]
    wheels = tmp_path / "wheels"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheels),
            str(package),
        ],
        check=True,
        capture_output=True,
    )
    environment = tmp_path / "python"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    wheel = next(wheels.glob("*.whl"))
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        check=True,
        capture_output=True,
    )
    code = "import importlib.util; assert all(importlib.util.find_spec(n) is None for n in ['agentscope','google','mcp','fastmcp']); import researchmind_skills.api"
    subprocess.run(
        [str(python), "-I", "-c", code], check=True, cwd=tmp_path, capture_output=True
    )
    target = tmp_path / "skills"
    installed = subprocess.run(
        [
            str(python),
            "-m",
            "researchmind_skills",
            "install",
            "--bundle",
            "literature",
            "--target",
            str(target),
        ],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert len(json.loads(installed.stdout)["data"]["installed"]) == 4
    payload = tmp_path / "request.json"
    payload.write_text(
        '{"records":[{"paper_id":"p1","title":"中文"}]}', encoding="utf-8"
    )
    script = target / "literature-search/scripts/run.py"
    reply = subprocess.run(
        [
            str(python),
            str(script),
            "run",
            "papers.export_csv",
            "--input-file",
            str(payload),
            "--workspace",
            str(tmp_path / "work"),
            "--wait",
        ],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert reply.returncode == 0, reply.stderr
    result = json.loads(reply.stdout)
    assert result["status"] == "completed"
    assert result["artifacts"][0]["kind"] == "csv"
    # The same installed script cannot call another skill's compute capability.
    denied = subprocess.run(
        [
            str(python),
            str(script),
            "run",
            "simulation.energy",
            "--input-file",
            str(payload),
            "--workspace",
            str(tmp_path / "work"),
        ],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert denied.returncode in (2, 4)
    assert json.loads(denied.stdout)["status"] == "failed"
