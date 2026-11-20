import time
from researchmind_skills.api import Runtime, create_local_context
from researchmind_skills.runtime.store import Store
from researchmind_skills.runtime.history import normalize_history


def test_doctor_checks_credentials_and_models_without_loading_frameworks(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MATTERSIM_MODEL_PATH", raising=False)
    paper = {x["operation"]: x for x in Runtime().doctor("paper-analysis")}
    assert not paper["papers.analyze"]["available"]
    assert "OPENAI_API_KEY" in paper["papers.analyze"]["missing"]
    energy = {x["operation"]: x for x in Runtime().doctor("structure-optimization")}
    assert not energy["simulation.energy"]["available"]
    assert "MATTERSIM_MODEL_PATH" in energy["simulation.energy"]["missing"]


def test_old_history_conversion_preserves_text_and_tool_records():
    old = [
        {"role": "user", "parts": [{"text": "原始问题"}]},
        {
            "role": "model",
            "parts": [
                {
                    "function_call": {
                        "id": "t1",
                        "name": "calculate_energy",
                        "args": {"x": 1},
                    }
                }
            ],
        },
        {
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "id": "t1",
                        "name": "calculate_energy",
                        "response": {"energy": -1},
                    }
                }
            ],
        },
        {"role": "model", "parts": [{"text": "结论"}]},
    ]
    normalized = normalize_history(old)
    assert normalized[0]["content"] == "原始问题"
    assert normalized[1]["content_blocks"][0]["tool_call_id"] == "t1"
    assert normalized[2]["content_blocks"][0]["result"] == {"energy": -1}
    assert normalized[-1]["content"] == "结论"
    assert old[0].get("schema_version") is None


def test_stale_job_recovery_never_reexecutes_science(tmp_path):
    context = create_local_context(tmp_path)
    store = Store(context)
    runtime = Runtime()
    with store.db() as db:
        db.execute(
            "INSERT INTO jobs(id,session,operation,payload,skill,status,request,updated) VALUES(?,?,?,?,?,?,?,?)",
            (
                "old",
                "default",
                "simulation.energy",
                "{}",
                "structure-optimization",
                "running",
                "default:req",
                time.time() - 100,
            ),
        )
    runtime.recover_stale_jobs(context)
    result = runtime.get_job_result("old", context)
    assert result["status"] == "failed"
    assert result["error"]["code"] == "WORKER_LOST"
    assert runtime.get_job("old", context)["status"] == "failed"
