# Agent runtime migration

ResearchMind2.0 keeps the materials-science capabilities from ResearchMind and
adopts the runtime boundary used by Open Science.

## Runtime boundary

The UI and WebSocket layer call `services.agent_runtime.AgentRuntime` through
`AgentCoordinator`. The coordinator no longer creates an AgentScope agent
directly. The selected provider is resolved by `services.agent_runtime.registry`
using `RESEARCHMIND_AGENT_RUNTIME`.

The built-in `agentscope` adapter is implemented in
`services/agent_runtime/agentscope.py`. It translates AgentScope stream events
to the framework-neutral `RuntimeEvent` contract while preserving the existing
scientific MCP tools, artifacts, session state, and history format.

## Preserved domain layer

- `packages/researchmind-skills` remains the scientific capability layer.
- Literature, materials database, simulation, and experiment planning roles are
  still discovered from `ROLE_SKILLS`.
- MCP services and artifact handling keep their existing session-scoped behavior.
- Existing WebSocket messages and HTTP endpoints remain compatible.

## Open Science concepts adopted

- Runtime selection is explicit and discoverable.
- Runtime lifecycle is explicit through `connect`, `status`, and `close`.
- Agent sessions are created per request and can restore durable state.
- Streaming output is normalized into runtime events before presentation.
- Runtime capabilities are exposed at `GET /api/agent-runtime`.

## Extension point

To add another provider, implement `AgentRuntime` and `AgentSession` from
`services/agent_runtime/contracts.py`, register it in `get_runtime`, and keep
the adapter responsible for translating the provider's native events. The
domain skills and WebSocket protocol do not need to know the provider's SDK.

The current adapter is intentionally local and in-process. An OpenCode or ACP
adapter can later implement the same contract without moving the scientific
skills or changing the frontend protocol.
