"""Read-only normalization of legacy ADK history and neutral messages."""

import uuid


def normalize_history(records):
    messages = []
    for record in records:
        role = record.get("role", record.get("author", ""))
        if role == "model":
            role = "assistant"
        parts = record.get("content_blocks") or record.get("parts") or []
        if not parts and isinstance(record.get("content"), str):
            parts = [{"text": record["content"]}]
        blocks = []
        for part in parts:
            if part.get("text"):
                blocks.append({"type": "text", "text": part["text"]})
            call = part.get("function_call") or part.get("functionCall")
            response = part.get("function_response") or part.get("functionResponse")
            if call:
                blocks.append(
                    {
                        "type": "tool_call",
                        "name": call.get("name"),
                        "arguments": call.get("args", {}),
                        "tool_call_id": call.get("id"),
                    }
                )
            if response:
                blocks.append(
                    {
                        "type": "tool_result",
                        "name": response.get("name"),
                        "result": response.get("response", {}),
                        "tool_call_id": response.get("id"),
                    }
                )
        if role not in ("user", "assistant", "tool", "system"):
            continue
        messages.append(
            {
                "schema_version": "1.0",
                "message_id": record.get("message_id", uuid.uuid4().hex),
                "role": role,
                "content": "".join(b["text"] for b in blocks if b["type"] == "text"),
                "content_blocks": blocks,
                "timestamp": record.get("timestamp"),
                "legacy": record.get("schema_version") != "1.0",
            }
        )
    return messages
