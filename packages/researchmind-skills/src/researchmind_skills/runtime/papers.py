"""Portable paper discovery, saved content, analysis and knowledge workflows."""

import csv
import hashlib
import io
import json
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from . import network
from .contracts import CapabilityError
from .store import Store


def export_csv(store, records, name="papers.csv", fields=None):
    fields = fields or list(dict.fromkeys(k for record in records for k in record))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                k: json.dumps(v, ensure_ascii=False)
                if isinstance(v, (list, dict))
                else v
                for k, v in record.items()
            }
        )
    return store.artifact(name, output.getvalue(), "csv")


def arxiv(query, limit):
    if ":" not in query:
        query = 'all:"' + query.replace('"', " ") + '"'
    url = "https://export.arxiv.org/api/query?" + urlencode(
        dict(
            {"id_list": query[3:]}
            if query.startswith("id:")
            else {"search_query": query},
            max_results=limit,
            sortBy="relevance",
        )
    )
    root = ET.fromstring(network.request(url, raw=True))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    records = []
    for item in root.findall("a:entry", ns):
        ident = item.findtext("a:id", default="", namespaces=ns).rsplit("/", 1)[-1]
        records.append(
            dict(
                paper_id=ident,
                title=item.findtext("a:title", default="", namespaces=ns).strip(),
                abstract=item.findtext("a:summary", default="", namespaces=ns).strip(),
                authors=[
                    a.findtext("a:name", namespaces=ns)
                    for a in item.findall("a:author", ns)
                ],
                published=item.findtext("a:published", namespaces=ns),
                url="https://arxiv.org/abs/" + ident,
                pdf_url="https://arxiv.org/pdf/" + ident,
                source="arxiv",
            )
        )
    return records


def tavily(query, limit, topic="general"):
    import os

    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise CapabilityError("MISSING_CREDENTIAL", "Configure TAVILY_API_KEY")
    data = network.request(
        "https://api.tavily.com/search",
        {"api_key": key, "query": query, "max_results": limit, "topic": topic},
    )
    return [
        dict(
            paper_id=hashlib.sha256(x["url"].encode()).hexdigest()[:24],
            title=x.get("title", ""),
            abstract=x.get("content", ""),
            url=x["url"],
            source="tavily",
        )
        for x in data.get("results", [])
    ]


def text_from_file(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if suffix == ".docx":
        from docx import Document

        return "\n".join(p.text for p in Document(path).paragraphs)
    text = path.read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        from html.parser import HTMLParser

        class Extractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []
                self.hidden = 0

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style"):
                    self.hidden += 1

            def handle_endtag(self, tag):
                if tag in ("script", "style"):
                    self.hidden = max(0, self.hidden - 1)

            def handle_data(self, data):
                if not self.hidden:
                    self.parts.append(data)

        parser = Extractor()
        parser.feed(text)
        text = "\n".join(parser.parts)
    return text


def find_paper(store, ident):
    paper = next((r for r in store.get("papers", []) if r["paper_id"] == ident), None)
    if paper:
        return paper
    return None


def get_content(store, paper_id=None, url=None):
    paper = find_paper(store, paper_id) if paper_id else None
    if paper and paper.get("content_artifact_id"):
        return dict(
            paper_id=paper_id,
            artifact_id=paper["content_artifact_id"],
            evidence=paper.get("evidence", "fulltext"),
        )
    if paper is None and not url and paper_id:
        paper = next(iter(arxiv("id:" + paper_id, 1)), None)
    target = url or (paper or {}).get("pdf_url") or (paper or {}).get("url")
    if not target:
        raise CapabilityError(
            "INVALID_ARGUMENT", "Supply an existing paper_id or content URL"
        )
    warnings = []
    try:
        body = network.request(target, raw=True)
        name = "download.pdf" if body.startswith(b"%PDF") else "download.html"
        source = store.artifact(name, body, name.rsplit(".", 1)[-1])
        text = text_from_file(store.resolve(source["artifact_id"]))
        evidence = "fulltext"
        if not text.strip():
            raise CapabilityError("SOURCE_UNAVAILABLE", "No extractable text")
    except (CapabilityError, ImportError, ValueError):
        if not paper or not paper.get("abstract"):
            raise
        text = paper["abstract"]
        evidence = "abstract"
        warnings.append("Full text unavailable; analysis is based on the abstract.")
    content = store.artifact((paper_id or "content").replace("/", "_") + ".txt", text)
    if paper and find_paper(store, paper["paper_id"]):
        records = store.get("papers", [])
        for record in records:
            if record["paper_id"] == paper["paper_id"]:
                record.update(
                    content_artifact_id=content["artifact_id"], evidence=evidence
                )
        store.set("papers", records)
    return dict(
        paper_id=paper_id,
        artifact_id=content["artifact_id"],
        evidence=evidence,
        warnings=warnings,
    )


def dispatch(operation, payload, context):
    store = Store(context)
    papers = store.get("papers", [])
    usage = {}
    artifacts = []
    warnings = []
    op = operation.removeprefix("papers.")
    if op in ("list", "filter"):
        rows = [
            r
            for r in papers
            if not payload.get("topic") or r.get("topic") == payload["topic"]
        ]
        if payload.get("fields"):
            rows = [{k: r.get(k) for k in payload["fields"]} for r in rows]
        data = {"papers": rows, "total_papers": len(rows)}
    elif op == "topics":
        data = {"topics": sorted(set(r.get("topic", "") for r in papers))}
    elif op.startswith("selection."):
        selected = store.get("selection", [])
        if op == "selection.update":
            selected = payload["paper_ids"]
            unknown = set(selected) - {r["paper_id"] for r in papers}
            if unknown:
                raise CapabilityError("INVALID_ARGUMENT", "Unknown paper selection")
            store.set("selection", selected)
        if op == "selection.clear":
            selected = []
            store.set("selection", [])
        data = {
            "paper_ids": selected,
            "papers": [r for r in papers if r["paper_id"] in selected],
        }
    elif op in ("search", "search_by_author", "web_search", "news_search"):
        query = payload.get("query") or "au:" + payload["author"]
        limit = payload.get("max_results", 10)
        sources = payload.get(
            "sources", ["arxiv"] if op in ("search", "search_by_author") else ["tavily"]
        )
        records = []
        failures = []
        for source in sources:
            try:
                if source == "arxiv":
                    rows = arxiv(query, limit)
                elif source == "tavily":
                    rows = tavily(
                        query, limit, "news" if op == "news_search" else "general"
                    )
                else:
                    url = (
                        "https://api.semanticscholar.org/graph/v1/paper/search?"
                        + urlencode(
                            {
                                "query": query,
                                "limit": limit,
                                "fields": "title,abstract,authors,year,url,openAccessPdf",
                            }
                        )
                    )
                    raw = network.request(url)
                    rows = [
                        dict(
                            paper_id=r["paperId"],
                            title=r["title"],
                            abstract=r.get("abstract", ""),
                            authors=[a["name"] for a in r.get("authors", [])],
                            year=r.get("year"),
                            url=r.get("url"),
                            pdf_url=(r.get("openAccessPdf") or {}).get("url"),
                            source="semantic_scholar",
                        )
                        for r in raw.get("data", [])
                    ]
                for r in rows:
                    if (
                        payload.get("year_from")
                        and int(str(r.get("year") or r.get("published") or "0")[:4])
                        < payload["year_from"]
                    ):
                        continue
                    r["topic"] = query
                    records.append(r)
            except CapabilityError as exc:
                failures.append(
                    {"source": source, "code": exc.code, "message": str(exc)}
                )
        if len(failures) == len(sources):
            raise CapabilityError(
                "SOURCE_UNAVAILABLE",
                "All requested sources failed: " + json.dumps(failures),
            )
        unique = {r["paper_id"]: r for r in papers}
        # Deduplicate matching source IDs and DOI/URL without deleting earlier metadata.
        seen = set()
        records = [
            r
            for r in records
            if not (
                (r.get("url") or r["paper_id"]) in seen
                or seen.add(r.get("url") or r["paper_id"])
            )
        ]
        unique.update({r["paper_id"]: r for r in records})
        store.set("papers", list(unique.values()))
        artifacts.append(export_csv(store, list(unique.values())))
        data = {"papers": records, "total_papers": len(records), "failures": failures}
        return {
            "data": data,
            "artifacts": artifacts,
            "status": "partial" if failures else "completed",
            "warnings": failures,
        }
    elif op == "info":
        paper = find_paper(store, payload["paper_id"])
        if paper is None:
            paper = next(iter(arxiv("id:" + payload["paper_id"], 1)), None)
        if paper is None:
            raise CapabilityError("SOURCE_UNAVAILABLE", "Paper was not found")
        data = paper
    elif op == "import_uploads":
        imported = []
        for ident in payload["artifact_ids"]:
            path = store.resolve(ident)
            text = text_from_file(path)
            paper_id = hashlib.sha256(path.read_bytes()).hexdigest()[:24]
            content = store.artifact(paper_id + ".txt", text)
            artifacts.append(content)
            imported.append(
                dict(
                    paper_id=paper_id,
                    title=path.stem,
                    abstract=text[:1000],
                    source="upload",
                    evidence="fulltext",
                    content_artifact_id=content["artifact_id"],
                )
            )
        merged = {r["paper_id"]: r for r in papers}
        merged.update({r["paper_id"]: r for r in imported})
        store.set("papers", list(merged.values()))
        data = {"papers": imported}
        artifacts.append(export_csv(store, list(merged.values())))
    elif op == "download":
        body = network.request(payload["url"], raw=True)
        artifacts.append(store.artifact(payload.get("name", "paper.pdf"), body, "file"))
        data = artifacts[0]
    elif op in ("content.get", "content.batch_get"):
        ids = payload.get("paper_ids", [payload.get("paper_id")])
        rows = []
        failures = []
        for ident in ids:
            try:
                rows.append(get_content(store, ident, payload.get("url")))
            except CapabilityError as exc:
                failures.append(
                    {"paper_id": ident, "error": str(exc), "code": exc.code}
                )
        if not rows:
            raise CapabilityError("SOURCE_UNAVAILABLE", str(failures))
        data = {"contents": rows, "failures": failures}
        return {
            "data": data,
            "status": "partial" if failures else "completed",
            "warnings": failures,
        }
    elif op in ("content.read", "content.read_segment", "content.find"):
        text = store.resolve(payload["artifact_id"]).read_text(encoding="utf-8")
        if op == "content.find":
            term = payload["search_term"]
            n = payload.get("context_length", 200)
            matches = []
            start = 0
            import re
            from itertools import islice

            for match in islice(
                re.finditer(re.escape(term), text, re.IGNORECASE), 1000
            ):
                pos = match.start()
                matches.append(
                    dict(position=pos, context=text[max(0, pos - n) : match.end() + n])
                )
            data = {"matches": matches, "total_matches": len(matches)}
        else:
            start = payload.get("start", 0)
            length = (
                payload.get("length", len(text))
                if op.endswith("read_segment")
                else len(text)
            )
            part = text[start : start + length]
            next_start = min(len(text), start + len(part))
            data = dict(
                content=part,
                start=start,
                length=len(part),
                total_length=len(text),
                next_start=next_start,
                has_more=next_start < len(text),
            )
    elif op == "export_csv":
        records = payload.get("records", papers)
        artifacts.append(
            export_csv(
                store, records, payload.get("name", "papers.csv"), payload.get("fields")
            )
        )
        data = {"rows": len(records)}
    elif op == "clean_csv":
        path = store.resolve(payload["artifact_id"])
        rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        valid = [
            r
            for r in rows
            if any(v for v in r.values())
            and "unknown" not in str(r.get("ID", r.get("paper_id", ""))).lower()
        ]
        data = {
            "original_count": len(rows),
            "valid_count": len(valid),
            "invalid_count": len(rows) - len(valid),
            "dry_run": payload.get("dry_run", True),
        }
        if not data["dry_run"]:
            if payload.get("backup", True):
                artifacts.append(
                    store.artifact("backup-" + path.name, path.read_bytes(), "csv")
                )
            artifacts.append(export_csv(store, valid, "cleaned-" + path.name))
    elif op in ("plan", "analyze", "report"):
        ids = (
            payload.get("paper_ids")
            or store.get("selection", [])
            or [r["paper_id"] for r in papers]
        )
        evidence = []
        evidence_failures = []
        analyses = store.get("analyses", {})
        for ident in [] if op == "plan" else ids:
            try:
                paper = find_paper(store, ident)
                if paper is None:
                    raise CapabilityError("INVALID_ARGUMENT", "Unknown paper " + ident)
                content = get_content(store, ident)
                text = store.resolve(content["artifact_id"]).read_text(encoding="utf-8")
                evidence.append(
                    dict(
                        paper_id=ident,
                        title=paper["title"],
                        url=paper.get("url"),
                        evidence=content["evidence"],
                        text=text[:24000],
                        truncated=len(text) > 24000,
                        analysis=analyses.get(ident),
                    )
                )
            except CapabilityError as exc:
                evidence_failures.append(
                    {"paper_id": ident, "code": exc.code, "message": str(exc)}
                )
        if op != "plan" and not evidence:
            raise CapabilityError(
                "SOURCE_UNAVAILABLE",
                "No usable paper evidence: " + str(evidence_failures),
            )
        if evidence_failures:
            warnings.extend(evidence_failures)
        if op == "analyze":
            completed = []
            for item in evidence:
                key = hashlib.sha256(
                    (
                        item["text"]
                        + payload.get("instruction", "")
                        + __import__("os").environ.get("MODEL_USE", "")
                    ).encode()
                ).hexdigest()
                cached = analyses.get(item["paper_id"], {})
                if cached.get("input_hash") == key:
                    completed.append(cached)
                    continue
                text, used = network.model_complete(
                    "Analyze the supplied paper in Chinese. State evidence limits, methods, findings, limitations. "
                    + payload.get("instruction", "")
                    + "\n"
                    + json.dumps(item, ensure_ascii=False)
                )
                usage.setdefault("model_calls", []).append(used)
                cached = dict(
                    paper_id=item["paper_id"],
                    input_hash=key,
                    analysis=text,
                    evidence=item["evidence"],
                )
                analyses[item["paper_id"]] = cached
                completed.append(cached)
                store.set("analyses", analyses)
            artifacts.append(
                store.artifact(
                    "analysis.md",
                    "\n\n".join(r["analysis"] for r in completed),
                    "markdown",
                )
            )
            artifacts.append(export_csv(store, completed, "analysis.csv"))
            data = {
                "analyses": [
                    dict(
                        row,
                        analysis=row["analysis"][:500],
                        truncated=len(row["analysis"]) > 500,
                    )
                    for row in completed
                ]
            }
            usage["successful_units"] = len(completed)
            if evidence_failures:
                return {
                    "status": "partial",
                    "data": dict(data, failures=evidence_failures),
                    "artifacts": artifacts,
                    "warnings": warnings,
                    "usage": usage,
                }
        else:
            if op == "report" and not evidence:
                raise CapabilityError(
                    "INVALID_ARGUMENT",
                    "Select or import papers before writing a report",
                )
            prompt = (
                ("Generate a research search plan for " + payload["query"])
                if op == "plan"
                else (
                    "Write a cited research report in Chinese for "
                    + payload["topic"]
                    + "\nUse only the supplied evidence, cite [paper_id] and URLs; distinguish abstract/excerpt evidence.\n"
                    + json.dumps(evidence, ensure_ascii=False)
                )
            )
            text, used = network.model_complete(prompt)
            usage["model_calls"] = [used]
            if op == "report":
                import re

                references = set(re.findall(r"\[([^\[\]\n]+)\]", text))
                known = {item["paper_id"] for item in evidence}
                unknown = {
                    r
                    for r in references
                    if r not in known
                    and ("http" in r or re.fullmatch(r"[a-zA-Z0-9._/-]+", r))
                }
                if unknown:
                    raise CapabilityError(
                        "INVALID_ARGUMENT", "Report contains unverifiable citation IDs"
                    )
                if not references.intersection(known):
                    raise CapabilityError(
                        "INVALID_ARGUMENT",
                        "Report is missing traceable paper-ID citations",
                    )
            artifacts.append(store.artifact(op + ".md", text, "markdown"))
            data = {
                op + "_summary": text[:500],
                "truncated": len(text) > 500,
                "paper_ids": [item["paper_id"] for item in evidence],
                "evidence_sources": [
                    {k: item[k] for k in ("paper_id", "evidence", "truncated")}
                    for item in evidence
                ],
            }
            if op == "report" and evidence_failures:
                return {
                    "status": "partial",
                    "data": dict(data, failures=evidence_failures),
                    "artifacts": artifacts,
                    "warnings": warnings,
                    "usage": usage,
                }
    elif op in ("index", "semantic_search"):
        return vector_dispatch(op, payload, context, store, papers)
    else:
        raise CapabilityError("CAPABILITY_UNAVAILABLE", operation)
    return {"data": data, "artifacts": artifacts, "warnings": warnings, "usage": usage}


def vector_dispatch(op, payload, context, store, papers):
    import chromadb

    scope = context.session_id + "-" + payload.get("collection_name", "papers")
    model_id = (
        __import__("os").environ.get("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001")
        if __import__("os").environ.get("GOOGLE_API_KEY")
        else __import__("os").environ.get("OPENAI_EMBEDDING_MODEL", "")
    )
    collection_name = (
        "rm-"
        + hashlib.sha256((scope + model_id + "chunks-v1").encode()).hexdigest()[:40]
    )
    client = chromadb.PersistentClient(path=str(store.root / "vectors"))
    if op == "index":
        docs = []
        ids = []
        metadata = []
        for ident in payload["paper_ids"]:
            paper = find_paper(store, ident)
            if not paper or paper.get("source") != "arxiv":
                raise CapabilityError(
                    "UNSUPPORTED_SOURCE",
                    "Initial vector ingestion supports saved arXiv papers only",
                )
            content = get_content(store, ident)
            text = store.resolve(content["artifact_id"]).read_text(encoding="utf-8")
            for offset in range(0, len(text), 2000):
                docs.append(text[offset : offset + 2000])
                ids.append(ident + "-" + str(offset))
                metadata.append(
                    dict(
                        paper_id=ident, start=offset, artifact_id=content["artifact_id"]
                    )
                )
        if not docs:
            raise CapabilityError("INVALID_ARGUMENT", "No content to index")
        vectors, embedding_model = network.embed(docs)
        collection = client.get_or_create_collection(
            collection_name,
            embedding_function=None,
            metadata={"embedding_model": embedding_model, "chunk_version": "1"},
        )
        collection.upsert(
            ids=ids, documents=docs, embeddings=vectors, metadatas=metadata
        )
        return {
            "data": {
                "ingested_documents": len(payload["paper_ids"]),
                "chunks": len(docs),
                "collection_name": collection_name,
            }
        }
    try:
        collection = client.get_collection(collection_name, embedding_function=None)
    except Exception as exc:
        raise CapabilityError(
            "ARTIFACT_NOT_FOUND", "No compatible index; ingest first"
        ) from exc
    vectors, _ = network.embed([payload["query"]])
    return {
        "data": collection.query(
            query_embeddings=vectors,
            n_results=min(payload.get("top_k", 5), max(1, collection.count())),
        )
    }
