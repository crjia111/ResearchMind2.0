"""Bounded HTTP and an OpenAI-compatible model port, independent of Agent frameworks."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from .contracts import CapabilityError


def request(url, payload=None, headers=None, raw=False, timeout=60):
    parts = urllib.parse.urlsplit(url)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise CapabilityError(
            "INVALID_ARGUMENT", "Expected an HTTP(S) URL without embedded credentials"
        )
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "ResearchMind/0.1",
            **({"Content-Type": "application/json"} if body else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read(30_000_001)
        if len(content) > 30_000_000:
            raise CapabilityError(
                "INVALID_ARGUMENT", "Remote content exceeds 30 MB limit"
            )
        return content if raw else json.loads(content)
    except (urllib.error.URLError, TimeoutError) as exc:
        # Do not include request headers or credentials in user-visible errors.
        raise CapabilityError(
            "SOURCE_UNAVAILABLE", f"Request to {parts.hostname} failed", True
        ) from exc


def model_complete(
    prompt,
    system="Provide evidence-based materials research. Cite supplied sources; do not invent results.",
):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise CapabilityError(
            "MISSING_CREDENTIAL", "Configure OPENAI_API_KEY for model-based analysis"
        )
    model = os.environ.get("MODEL_USE", "openai/gpt-4o-mini")
    if model.split("/")[0] in ("openai", "deepseek", "anthropic"):
        model = model.split("/", 1)[-1]
    url = (
        os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        + "/chat/completions"
    )
    data = request(
        url,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        {"Authorization": "Bearer " + key},
    )
    return data["choices"][0]["message"]["content"], dict(
        data.get("usage", {}), model=model
    )


def embed(texts):
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        model = os.environ.get("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":batchEmbedContents"
        )
        data = request(
            url,
            {
                "requests": [
                    {"model": "models/" + model, "content": {"parts": [{"text": t}]}}
                    for t in texts
                ]
            },
            {"x-goog-api-key": google_key},
        )
        return [x["values"] for x in data["embeddings"]], "google/" + model
    key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_EMBEDDING_MODEL")
    if not key or not model:
        raise CapabilityError(
            "MISSING_CREDENTIAL",
            "Configure Google embedding credentials or OPENAI_EMBEDDING_MODEL and OPENAI_API_KEY",
        )
    data = request(
        os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        + "/embeddings",
        {"model": model, "input": texts},
        {"Authorization": "Bearer " + key},
    )
    return [
        x["embedding"] for x in sorted(data["data"], key=lambda x: x["index"])
    ], "openai/" + model
