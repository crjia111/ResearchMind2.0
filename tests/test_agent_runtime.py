from services.agent_runtime import RuntimeEvent, get_runtime, runtime_info


def test_runtime_event_uses_stable_envelope():
    event = RuntimeEvent("text_delta", {"text": "hello"})
    assert event.to_dict() == {"type": "text_delta", "text": "hello"}


def test_unknown_runtime_is_rejected_without_loading_a_provider():
    try:
        get_runtime("missing-provider")
    except ValueError as error:
        assert "Unsupported agent runtime" in str(error)
    else:
        raise AssertionError("Unknown runtime should be rejected")


def test_runtime_info_exposes_capability_metadata():
    class FakeRuntime:
        def capabilities(self):
            from services.agent_runtime import RuntimeCapabilities

            return RuntimeCapabilities(
                "fixture", "Fixture Runtime", "1.0", ("research",), {"streaming": True}
            )

        def status(self):
            from services.agent_runtime import RuntimeStatus

            return RuntimeStatus("ready")

    assert runtime_info(FakeRuntime()) == {
        "runtime_id": "fixture",
        "display_name": "Fixture Runtime",
        "version": "1.0",
        "agent_ids": ["research"],
        "features": {"streaming": True},
        "status": "ready",
    }
