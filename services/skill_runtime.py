"""Local host composition. The portable runtime never imports this module."""

import os
from pathlib import Path
from researchmind_skills.api import create_local_context
from .config import server_config
from .session_manager import SessionManager


def context_for(session_id, event_sink=None):
    if not session_id or not SessionManager.get_session(session_id):
        from researchmind_skills.runtime.contracts import CapabilityError

        raise CapabilityError("ACCESS_DENIED", "Unknown local session")
    workspace = os.environ.get("RESEARCHMIND_WORKSPACE") or str(
        Path(server_config.SESSION_DATA_DIR) / "skill-runtime"
    )
    return create_local_context(
        workspace,
        session_id,
        event_sink=event_sink,
        input_roots=(server_config.SESSION_DATA_DIR,),
    )


def configured_model():
    from agentscope.model import OpenAIChatModel
    from agentscope.credential import OpenAICredential

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "Configure OPENAI_API_KEY and MODEL_USE before sending AI requests"
        )
    model = os.environ.get("MODEL_USE", "openai/gpt-4o-mini")
    if model.split("/")[0] in ("openai", "deepseek", "anthropic"):
        model = model.split("/", 1)[-1]
    return OpenAIChatModel(
        credential=OpenAICredential(
            api_key=key, base_url=os.environ.get("OPENAI_BASE_URL")
        ),
        model=model,
    )
