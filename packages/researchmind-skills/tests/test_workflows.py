import pytest
from researchmind_skills.api import Runtime, create_local_context
from researchmind_skills.runtime.store import Store
from researchmind_skills.runtime import papers, network
from researchmind_skills.runtime.contracts import CapabilityError


def test_analysis_reuses_saved_evidence_and_report_requires_real_citations(
    tmp_path, monkeypatch
):
    ctx = create_local_context(tmp_path)
    store = Store(ctx)
    content = store.artifact(
        "source.txt", "Observed result: conductivity improves at fixed temperature."
    )
    store.set(
        "papers",
        [
            dict(
                paper_id="p1",
                title="Source paper",
                url="https://example.org/source",
                source="arxiv",
                content_artifact_id=content["artifact_id"],
                evidence="fulltext",
            )
        ],
    )
    calls = []

    def complete(prompt, *args, **kw):
        calls.append(prompt)
        return ("Research findings [p1].", {"total_tokens": 12, "model": "fixture"})

    monkeypatch.setattr(network, "model_complete", complete)
    first = papers.dispatch("papers.analyze", {"paper_ids": ["p1"]}, ctx)
    assert first["data"]["analyses"][0]["paper_id"] == "p1"
    second = papers.dispatch("papers.analyze", {"paper_ids": ["p1"]}, ctx)
    assert len(calls) == 1
    assert second["data"]["analyses"][0]["evidence"] == "fulltext"
    report = papers.dispatch(
        "papers.report", {"topic": "test", "paper_ids": ["p1"]}, ctx
    )
    assert "[p1]" in report["data"]["report_summary"]
    assert len(calls) == 2
    monkeypatch.setattr(
        network,
        "model_complete",
        lambda *a, **k: ("Unsupported conclusion [invented].", {}),
    )
    with pytest.raises(CapabilityError):
        papers.dispatch("papers.report", {"topic": "test", "paper_ids": ["p1"]}, ctx)


def test_abstract_fallback_remains_explicit(tmp_path, monkeypatch):
    ctx = create_local_context(tmp_path)
    store = Store(ctx)
    store.set(
        "papers",
        [
            dict(
                paper_id="p1",
                title="Source",
                abstract="Only an abstract",
                url="https://example.test/paper",
            )
        ],
    )

    def offline(*a, **k):
        raise CapabilityError("SOURCE_UNAVAILABLE", "offline")

    monkeypatch.setattr(network, "request", offline)
    content = papers.get_content(store, "p1")
    assert content["evidence"] == "abstract"
    assert content["warnings"]
    assert Store(ctx).get("papers")[0]["evidence"] == "abstract"


@pytest.mark.asyncio
async def test_event_sink_failure_does_not_change_success(tmp_path):
    ctx = create_local_context(tmp_path)

    def broken(event):
        raise OSError("socket is closed")

    ctx.event_sink = broken
    result = await Runtime().execute("papers.export_csv", {"records": [{"x": 1}]}, ctx)
    assert result["status"] == "completed"
    assert Runtime().get_job_result(result["job_id"], ctx) == result
