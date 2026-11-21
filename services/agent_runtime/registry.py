"""Runtime selection and capability discovery for the ResearchMind host."""

import os


def get_runtime(runtime_id=None, scientific_runtime=None):
    selected = (
        runtime_id or os.getenv("RESEARCHMIND_AGENT_RUNTIME") or "agentscope"
    ).strip().lower()
    if selected == "agentscope":
        from .agentscope import AgentScopeRuntime

        if scientific_runtime is None:
            from researchmind_skills.api import Runtime

            scientific_runtime = Runtime()
        return AgentScopeRuntime(scientific_runtime)
    raise ValueError(f"Unsupported agent runtime: {selected}")


def runtime_info(runtime=None):
    runtime = runtime or get_runtime()
    capabilities = runtime.capabilities()
    return {
        "runtime_id": capabilities.runtime_id,
        "display_name": capabilities.display_name,
        "version": capabilities.version,
        "agent_ids": list(capabilities.agent_ids),
        "features": dict(capabilities.features),
        "status": runtime.status().state if hasattr(runtime, "status") else "ready",
    }
