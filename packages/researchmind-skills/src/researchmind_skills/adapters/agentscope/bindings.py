"""AgentScope 2.0.12 bindings generated from the public capability registry."""

import json
from agentscope.tool import FunctionTool, ToolChunk
from agentscope.message import TextBlock, ToolResultState
from agentscope.permission import PermissionBehavior, PermissionDecision
from ...runtime.registry import list_capabilities


def to_tool_chunk(response):
    state = (
        ToolResultState.ERROR
        if response["status"] == "failed"
        else ToolResultState.SUCCESS
    )
    if response.get("error", {}) and response["error"]["code"] == "ACCESS_DENIED":
        state = ToolResultState.DENIED
    return ToolChunk(
        content=[TextBlock(text=json.dumps(response, ensure_ascii=False, default=str))],
        state=state,
        metadata={"researchmind_result": response},
    )


def build_bound_tools(runtime, context, skill_names, include_shared=True):
    tools = []
    seen = set()
    for skill in skill_names:
        for spec in list_capabilities(skill):
            operation = spec["operation"]
            if operation in seen:
                continue
            seen.add(operation)

            def bind(operation, skill):
                async def invoke(**kwargs):
                    response = await runtime.execute(
                        operation, kwargs, context, skill_name=skill, wait=True
                    )
                    return to_tool_chunk(response)

                return invoke

            tools.append(
                FunctionTool(
                    bind(operation, skill),
                    name="rm_" + operation.replace(".", "_"),
                    description=operation
                    + "; execute using the loaded workflow instructions.",
                    input_schema=spec["input_schema"],
                    is_concurrency_safe=False,
                    permission=PermissionDecision(
                        PermissionBehavior.ALLOW,
                        "Host-enabled scientific capability with runtime validation",
                    ),
                )
            )
    return tools
