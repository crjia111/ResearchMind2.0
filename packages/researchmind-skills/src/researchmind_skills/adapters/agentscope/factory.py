"""Per-session professional agents and bounded delegation; no global mutable agents."""

import json
from importlib.resources import files
from agentscope.agent import Agent
from agentscope.tool import Toolkit, FunctionTool, ToolChunk
from agentscope.skill import LocalSkillLoader
from agentscope.message import UserMsg, TextBlock, ToolResultState
from agentscope.permission import PermissionDecision, PermissionBehavior
from .bindings import build_bound_tools
from ...runtime.registry import BUNDLES
from ...runtime.contracts import CapabilityError

ROLE_SKILLS = {
    "deep_research_agent": BUNDLES["literature"],
    "database_agent": BUNDLES["materials-db"],
    "simulation_agent": BUNDLES["simulation"],
    "research_coordinator": [],
    "experiment_plan_agent": [],
}


def create_agent(role, runtime, context, model, skill_root=None, depth=0, state=None):
    if role not in ROLE_SKILLS:
        raise CapabilityError("INVALID_ARGUMENT", "Unknown agent role")
    skills = ROLE_SKILLS[role]
    root = skill_root or str(files("researchmind_skills").joinpath("skill_assets"))
    tools = build_bound_tools(runtime, context, skills)
    if not skills:
        allowed = ["deep_research_agent", "database_agent", "simulation_agent"]
        if role == "research_coordinator":
            allowed.append("experiment_plan_agent")

        async def delegate(agent_id, task):
            if depth >= 2 or agent_id not in allowed:
                return ToolChunk(
                    content=[TextBlock(text="Delegation limit or invalid specialist")],
                    state=ToolResultState.ERROR,
                )
            specialist = create_agent(
                agent_id, runtime, context, model, root, depth + 1
            )
            answer = await specialist.reply(UserMsg(name="user", content=task))
            return ToolChunk(
                content=[
                    TextBlock(
                        text=json.dumps(
                            answer.model_dump(mode="json"), ensure_ascii=False
                        )
                    )
                ],
                state=ToolResultState.SUCCESS,
            )

        tools.append(
            FunctionTool(
                delegate,
                name="delegate_research",
                description="Delegate a bounded scientific task and pass existing artifact IDs. Do not repeat completed operations.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "enum": allowed},
                        "task": {"type": "string"},
                    },
                    "required": ["agent_id", "task"],
                    "additionalProperties": False,
                },
                permission=PermissionDecision(
                    PermissionBehavior.ALLOW, "Only configured professional agents"
                ),
            )
        )
    loaders = [
        LocalSkillLoader(directory=str(__import__("pathlib").Path(root) / skill))
        for skill in skills
    ]
    prompt = (
        "You are ResearchMind's "
        + role
        + ". Respond in the user's language. Use loaded skills and host-enabled tools. "
        "Preserve artifact IDs, evidence source, units and real computation status. Never invent scientific results or silently relax structures. "
        "Only perform the requested workflow. Reuse saved selections, content and analyses. Missing tools/models/keys must be reported. "
        "Tools may return partial/failed; accepted is not final completion. ResearchMind is local and has no login or platform billing. "
        "When planning experiments, distinguish literature claims, computed predictions and untested hypotheses."
    )
    return Agent(
        name=role,
        system_prompt=prompt,
        model=model,
        state=state,
        toolkit=Toolkit(tools=tools, skills_or_loaders=loaders),
    )
