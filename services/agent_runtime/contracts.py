"""Framework-neutral contracts for agent runtimes and turn events."""

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class RuntimeCapabilities:
    runtime_id: str
    display_name: str
    version: str
    agent_ids: Sequence[str]
    features: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeStatus:
    state: str
    detail: str = ""


@dataclass(frozen=True)
class RuntimeEvent:
    type: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"type": self.type, **self.data}


class AgentSession(Protocol):
    async def run(self, prompt: str) -> AsyncIterator[RuntimeEvent]: ...

    def export_state(self) -> Mapping[str, Any] | None: ...

    def restore_history(self, messages: Sequence[Mapping[str, Any]]) -> None: ...


class AgentRuntime(Protocol):
    runtime_id: str

    async def connect(self) -> None: ...

    def close(self) -> None: ...

    def status(self) -> RuntimeStatus: ...

    def capabilities(self) -> RuntimeCapabilities: ...

    def list_agents(self) -> Sequence[str]: ...

    def create_session(
        self, agent_id: str, context: Any, model: Any, state: Mapping[str, Any] | None = None
    ) -> AgentSession: ...
