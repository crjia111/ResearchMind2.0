"""Translate only presentation events; scientific outputs remain framework-neutral."""


def event_data(event):
    return (
        event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
    )


def normalized_event(event):
    data = event_data(event)
    kind = data.get("type")
    if kind == "TEXT_BLOCK_DELTA":
        return {"type": "text_delta", "text": data["delta"]}
    if kind == "MODEL_CALL_END":
        return {
            "type": "usage",
            "input_tokens": data.get("input_tokens", 0),
            "output_tokens": data.get("output_tokens", 0),
        }
    if kind == "TOOL_RESULT_END":
        return {
            "type": "tool_result",
            "tool_call_id": data.get("tool_call_id"),
            "metadata": data.get("metadata", {}),
        }
    return {"type": "agent_event", "event": data}
