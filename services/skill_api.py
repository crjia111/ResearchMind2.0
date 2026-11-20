"""Domain HTTP routes over the same runtime used by the CLI and agents."""

import csv
from pathlib import Path
import uuid
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import FileResponse
from researchmind_skills.api import Runtime
from researchmind_skills.runtime.store import Store
from researchmind_skills.runtime.contracts import CapabilityError
from .skill_runtime import context_for
from .session_manager import SessionManager

router = APIRouter()
runtime = Runtime()


def context(session_id):
    try:
        return context_for(session_id)
    except (CapabilityError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


async def call(operation, payload, session_id):
    response = await runtime.execute(operation, payload, context(session_id), wait=True)
    if response["status"] == "failed":
        raise HTTPException(400, response["error"])
    return response


@router.get("/api/skills/capabilities")
async def capabilities():
    return runtime.list_capabilities()


@router.get("/api/skills/artifacts/{session_id}/{artifact_id}")
async def artifact(session_id: str, artifact_id: str):
    try:
        return FileResponse(Store(context(session_id)).resolve(artifact_id))
    except CapabilityError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/papers")
async def papers(session_id: str):
    return await call("papers.list", {}, session_id)


@router.get("/api/papers/topics")
async def topics(session_id: str):
    return await call("papers.topics", {}, session_id)


@router.get("/api/papers/selection")
async def selection(session_id: str):
    return await call("papers.selection.get", {}, session_id)


@router.put("/api/papers/selection")
async def set_selection(request: Request, session_id: str):
    payload = await request.json()
    return await call(
        "papers.selection.update",
        {"paper_ids": payload.get("paper_ids", [])},
        session_id,
    )


@router.delete("/api/papers/selection")
async def clear_selection(session_id: str):
    return await call("papers.selection.clear", {}, session_id)


@router.get("/api/skills/jobs/{session_id}/{job_id}")
async def job(session_id: str, job_id: str):
    try:
        return runtime.get_job_result(job_id, context(session_id))
    except CapabilityError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/api/skills/jobs/{session_id}/{job_id}")
async def cancel_job(session_id: str, job_id: str):
    try:
        return runtime.cancel_job(job_id, context(session_id))
    except CapabilityError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/api/mcp/call_tool")
async def legacy_paper_call(request: Request):
    body = await request.json()
    name = body.get("tool_name")
    args = body.get("arguments", {})
    session = args.get("session_id")
    ctx = context(session)
    store = Store(ctx)
    if name == "list_papers_from_csv":
        old = args.get("csv_file_path")
        if old and not store.get("papers"):
            try:
                path = store.resolve(old)
            except CapabilityError:
                path = Path(old).resolve()
                from .config import server_config

                root = Path(server_config.SESSION_DATA_DIR).resolve()
                if not path.is_relative_to(root) or session not in path.parts:
                    raise HTTPException(
                        400, "Legacy CSV is outside the session directory"
                    )
            if path.is_file():
                store.set(
                    "papers", list(csv.DictReader(path.open(encoding="utf-8-sig")))
                )
        data = (
            await call(
                "papers.list",
                {"fields": args["fields"]} if args.get("fields") else {},
                session,
            )
        )["data"]
        return dict(data, status="success", session_id=session, csv_file_path=old)
    if name == "select_papers":
        ids = args.get("paper_ids", [])
        previous = store.get("selection", [])
        mode = args.get("mode", "replace")
        if mode == "add":
            ids = list(dict.fromkeys(previous + ids))
        elif mode == "remove":
            ids = [x for x in previous if x not in ids]
        elif mode != "replace":
            raise HTTPException(400, "Unknown selection mode")
        response = await call("papers.selection.update", {"paper_ids": ids}, session)
        return dict(
            response["data"],
            status="success",
            session_id=session,
            selected_ids=ids,
            selected_count=len(ids),
        )
    raise HTTPException(
        404, "This compatibility route only supports paper list and selection"
    )


@router.post("/api/upload/documents")
async def upload_documents(
    files: list[UploadFile] = File(...),
    session_id: str | None = Query(None),
    topic: str | None = Query(None),
    client_id: str | None = Query(None),
):
    if not files or len(files) > 50:
        raise HTTPException(400, "Upload between 1 and 50 documents")
    if not session_id:
        session_id = "upload_" + uuid.uuid4().hex[:12]
        SessionManager.create_session(
            session_id=session_id,
            client_id=client_id or "local",
            agent_id="deep_research_agent",
            title=topic or "Uploaded documents",
        )
    ctx = context(session_id)
    store = Store(ctx)
    artifacts = []
    for file in files:
        name = Path(file.filename or "upload.txt").name
        if Path(name).suffix.lower() not in (".pdf", ".docx", ".txt", ".md", ".html"):
            raise HTTPException(400, "Unsupported document type")
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Document exceeds 10 MB")
        artifacts.append(store.artifact(name, content, Path(name).suffix.lstrip(".")))
    response = await call(
        "papers.import_uploads",
        {"artifact_ids": [x["artifact_id"] for x in artifacts]},
        session_id,
    )
    csv_artifact = next((a for a in response["artifacts"] if a["kind"] == "csv"), None)
    data = dict(
        status="success",
        session_id=session_id,
        topic=topic or "uploaded_documents",
        papers=response["data"]["papers"],
        uploaded_files=[
            dict(
                filename=a["name"],
                file_path=a["artifact_id"],
                download_url=f"/api/skills/artifacts/{session_id}/{a['artifact_id']}",
            )
            for a in artifacts
        ],
    )
    if csv_artifact:
        data.update(
            csv_file_path=csv_artifact["artifact_id"],
            csv_download_url=f"/api/skills/artifacts/{session_id}/{csv_artifact['artifact_id']}",
        )
    return data
