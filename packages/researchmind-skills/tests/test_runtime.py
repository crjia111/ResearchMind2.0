import asyncio
import csv
import io
import json
import subprocess
import sys
import pytest

from researchmind_skills.api import Runtime, create_local_context
from researchmind_skills.runtime.store import Store
from researchmind_skills.runtime.registry import LEGACY_ALIASES, BUNDLES, CAPABILITIES
from researchmind_skills.runtime.contracts import CapabilityError


@pytest.fixture
def context(tmp_path):
    return create_local_context(tmp_path, "one")


def run(operation, payload, context, **kw):
    return asyncio.run(Runtime().execute(operation, payload, context, **kw))


def test_all_legacy_capabilities_are_mapped():
    assert len(LEGACY_ALIASES) == 42
    assert set(LEGACY_ALIASES.values()) <= CAPABILITIES.keys()
    assert [len(v) for v in BUNDLES.values()] == [4, 1, 4]


def test_unicode_segments_are_lossless_and_session_isolated(context):
    text = "中文研究🙂\nαβγ\n" * 13
    artifact = Store(context).artifact("论文.txt", text)
    fragments = []
    offset = 0
    while True:
        reply = run(
            "papers.content.read_segment",
            {"artifact_id": artifact["artifact_id"], "start": offset, "length": 7},
            context,
            skill_name="paper-analysis",
        )
        assert reply["status"] == "completed"
        data = reply["data"]
        fragments.append(data["content"])
        offset = data["next_start"]
        assert data["total_length"] == len(text)
        if not data["has_more"]:
            break
    assert "".join(fragments) == text
    other = create_local_context(context.workspace, "two")
    denied = run(
        "papers.content.read",
        {"artifact_id": artifact["artifact_id"]},
        other,
        skill_name="paper-analysis",
    )
    assert denied["error"]["code"] == "ARTIFACT_NOT_FOUND"


def test_csv_exports_round_trip_quotes_newlines_and_lists(context):
    records = [
        {"paper_id": "p1", "title": '中文,"quoted"\nline', "authors": ["A", "B"]}
    ]
    reply = run(
        "papers.export_csv",
        {"records": records},
        context,
        skill_name="literature-search",
    )
    path = Store(context).resolve(reply["artifacts"][0]["artifact_id"])
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    assert rows[0]["title"] == records[0]["title"]
    assert json.loads(rows[0]["authors"]) == ["A", "B"]


def test_parameters_bindings_and_ranges_reject_invalid_inputs(context):
    response = run(
        "papers.content.read_segment", {"artifact_id": "x", "length": 0}, context
    )
    assert response["error"]["code"] == "INVALID_ARGUMENT"
    response = run("papers.export_csv", {}, context, skill_name="phonon-analysis")
    assert response["error"]["code"] == "ACCESS_DENIED"
    response = run("papers.export_csv", {"user_id": "forged"}, context)
    assert response["error"]["code"] == "INVALID_ARGUMENT"
    response = run("not.a.capability", {}, context)
    assert response["error"]["code"] == "CAPABILITY_UNAVAILABLE"


def test_import_and_selection_survive_runtime_restart(context):
    artifact = Store(context).artifact("paper.txt", "Evidence from uploaded paper.")
    reply = run(
        "papers.import_uploads",
        {"artifact_ids": [artifact["artifact_id"]]},
        context,
        skill_name="literature-search",
    )
    assert reply["status"] == "completed"
    ids = [p["paper_id"] for p in reply["data"]["papers"]]
    run("papers.selection.update", {"paper_ids": ids}, context)
    restored = run(
        "papers.selection.get", {}, create_local_context(context.workspace, "one")
    )
    assert restored["data"]["paper_ids"] == ids


def test_idempotency_reuses_artifact_and_rejects_changed_payload(context):
    first = run(
        "papers.export_csv", {"records": [{"x": 1}]}, context, request_id="same"
    )
    second = run(
        "papers.export_csv", {"records": [{"x": 1}]}, context, request_id="same"
    )
    assert first == second
    invalid = run(
        "papers.export_csv", {"records": [{"x": 2}]}, context, request_id="same"
    )
    assert invalid["error"]["code"] == "INVALID_ARGUMENT"


def test_paths_cannot_escape_workspace(context, tmp_path):
    with pytest.raises(CapabilityError):
        Store(context).artifact("../outside.txt", "bad")
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret")
    with pytest.raises(CapabilityError):
        Store(context).import_file(outside)
    with pytest.raises(CapabilityError):
        Store(context).path("../../outside")


def test_cli_json_and_invalid_input(context, tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps({"records": [{"x": "中文"}]}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "researchmind_skills",
            "run",
            "papers.export_csv",
            "--skill",
            "literature-search",
            "--input-file",
            str(input_file),
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["status"] == "completed"
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "researchmind_skills",
            "run",
            "papers.export_csv",
            "--unknown",
        ],
        capture_output=True,
        encoding="utf-8",
    )
    assert bad.returncode == 2
    assert json.loads(bad.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_multisource_partial_failure_preserves_success(context, monkeypatch):
    from researchmind_skills.runtime import papers

    monkeypatch.setattr(
        papers,
        "arxiv",
        lambda q, n: [
            dict(paper_id="a", title="A", source="arxiv", url="https://example.test/a")
        ],
    )

    def unavailable(*args, **kw):
        raise CapabilityError("MISSING_CREDENTIAL", "No key")

    monkeypatch.setattr(papers, "tavily", unavailable)
    reply = run(
        "papers.search", {"query": "battery", "sources": ["arxiv", "tavily"]}, context
    )
    assert reply["status"] == "partial"
    assert len(reply["data"]["papers"]) == 1
    assert reply["data"]["failures"][0]["source"] == "tavily"


def test_database_provider_failures_are_partial(context, monkeypatch):
    from researchmind_skills.runtime import materials

    def query(source, formula, limit):
        if source == "mp":
            raise CapabilityError("MISSING_CREDENTIAL", "No MP key")
        return [{"name": "NaCl"}]

    monkeypatch.setattr(materials, "query", query)
    reply = run(
        "materials.search", {"formula": "NaCl", "sources": ["mp", "oqmd"]}, context
    )
    assert reply["status"] == "partial"
    assert reply["data"]["records"][0]["source"] == "oqmd"


CIF = """data_Si
_cell_length_a 5.43
_cell_length_b 5.43
_cell_length_c 5.43
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_symmetry_space_group_name_H-M 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0 0 0
Si2 Si 0.25 0.25 0.25
"""


def test_strict_cif_parsing(context):
    valid = run(
        "simulation.validate_cif",
        {"cif_content": CIF},
        context,
        skill_name="structure-optimization",
    )
    assert valid["status"] == "completed" and valid["data"]["num_atoms"] == 2
    invalid = run(
        "simulation.validate_cif",
        {"cif_content": "data_fake\n_cell_length_a 5"},
        context,
    )
    assert invalid["status"] == "failed"
    assert invalid["error"]["code"] == "INVALID_ARGUMENT"


def test_real_compute_missing_model_is_not_mock_success(context, monkeypatch):
    monkeypatch.delenv("MATTERSIM_MODEL_PATH", raising=False)
    reply = run(
        "simulation.energy",
        {"cif_content": CIF},
        context,
        skill_name="structure-optimization",
        wait=True,
    )
    assert reply["status"] == "failed"
    assert reply["error"]["code"] == "MODEL_NOT_FOUND"
    assert reply["usage"]["real_compute_units"] == 0


def test_async_submission_requires_persistent_worker(context):
    reply = run("simulation.energy", {"cif_content": CIF}, context, wait=False)
    assert reply["error"]["code"] == "CAPABILITY_UNAVAILABLE"


def test_maintenance_defaults_to_preview(context):
    artifact = Store(context).artifact(
        "papers.csv", "paper_id,title\np1,Valid\nunknown,bad\n", "csv"
    )
    reply = run("papers.clean_csv", {"artifact_id": artifact["artifact_id"]}, context)
    assert reply["data"]["dry_run"] is True
    assert reply["data"]["valid_count"] == 1
    assert "unknown" in Store(context).resolve(artifact["artifact_id"]).read_text()


def test_install_bundle_and_single_uninstall_preserves_shared_resources(tmp_path):
    from researchmind_skills.installer import install, uninstall

    install(tmp_path, skill="paper-analysis")
    install(tmp_path, bundle="literature")
    install(tmp_path, bundle="literature")
    assert len(list(tmp_path.glob("*/SKILL.md"))) == 4
    uninstall(tmp_path, bundle="literature")
    assert (tmp_path / "paper-analysis/SKILL.md").is_file()
    assert len(list(tmp_path.glob("*/SKILL.md"))) == 1
    uninstall(tmp_path, skill="paper-analysis")
    assert not list(tmp_path.glob("*/SKILL.md"))


def test_batch_cif_validation_preserves_success_and_per_item_failure(context):
    valid = Store(context).artifact("valid.cif", CIF, "cif")
    invalid = Store(context).artifact("invalid.cif", "not a CIF", "cif")
    reply = run(
        "simulation.validate_cif",
        {"artifact_ids": [valid["artifact_id"], invalid["artifact_id"]]},
        context,
        skill_name="structure-optimization",
    )
    assert reply["status"] == "partial"
    assert reply["data"]["completed"] == 1 and reply["data"]["failed"] == 1
    assert reply["data"]["results"][1]["error"]["code"] == "INVALID_ARGUMENT"
    assert reply["usage"]["real_compute_units"] == 0


def test_cache_cleanup_is_scoped_to_current_session(context):
    current = context.workspace / ".researchmind" / "compute-cache" / "one" / "job"
    current.mkdir(parents=True)
    (current / "temporary.txt").write_text("temporary")
    other = context.workspace / ".researchmind" / "compute-cache" / "two" / "job"
    other.mkdir(parents=True)
    (other / "keep.txt").write_text("keep")
    reply = run("simulation.cache.clear", {"dry_run": False}, context)
    assert reply["status"] == "completed"
    assert not current.exists()
    assert (other / "keep.txt").read_text() == "keep"


def test_unicode_search_offsets_reference_original_text(context):
    artifact = Store(context).artifact("unicode.txt", "ßABC中文研究")
    reply = run(
        "papers.content.find",
        {"artifact_id": artifact["artifact_id"], "search_term": "abc"},
        context,
        skill_name="paper-analysis",
    )
    assert reply["data"]["matches"][0]["position"] == 1


def test_trusted_host_principals_have_separate_stores(tmp_path):
    first = create_local_context(tmp_path, "same-session", principal_id="first")
    second = create_local_context(tmp_path, "same-session", principal_id="second")
    artifact = Store(first).artifact("private.txt", "first principal")
    Store(first).set("selection", ["p1"])
    assert Store(second).get("selection", []) == []
    reply = run("papers.content.read", {"artifact_id": artifact["artifact_id"]}, second)
    assert reply["error"]["code"] == "ARTIFACT_NOT_FOUND"
