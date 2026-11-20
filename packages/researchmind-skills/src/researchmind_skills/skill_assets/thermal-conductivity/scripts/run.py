"""Fixed-skill entry point; no scientific implementation or framework dependency."""
import json
from pathlib import Path
import sys
manifest=json.loads((Path(__file__).resolve().parents[1]/"skill.json").read_text(encoding="utf-8"))
try:
    from researchmind_skills import __version__
    from researchmind_skills.cli import main
except ImportError:
    print(json.dumps({"schema_version":"1.0","operation":"skill-entry","request_id":"","status":"failed","data":{},"artifacts":[],"warnings":[],"usage":{"successful_units":0,"real_compute_units":0},"error":{"code":"DEPENDENCY_UNAVAILABLE","message":"Install researchmind-skills==0.1.0 in this Python environment","retryable":False}}))
    raise SystemExit(4)
if __version__!=manifest["runtime_version"] or manifest["schema_version"]!="1.0":
    print(json.dumps({"schema_version":"1.0","operation":"skill-entry","request_id":"","status":"failed","data":{},"artifacts":[],"warnings":[],"usage":{"successful_units":0,"real_compute_units":0},"error":{"code":"RUNTIME_VERSION_MISMATCH","message":"Skill/runtime contract mismatch","retryable":False}}))
    raise SystemExit(4)
raise SystemExit(main(fixed_skill=manifest["name"]))
