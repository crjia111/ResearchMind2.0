from dataclasses import dataclass
from pathlib import Path
import hashlib
import re


@dataclass
class ExecutionContext:
    workspace: Path
    session_id: str = "default"
    principal_id: str = "local"
    event_sink: object = None
    input_roots: tuple = ()
    allowed_skills: tuple = ()

    def __post_init__(self):
        self.workspace = Path(self.workspace).expanduser().resolve()
        for name in ("session_id", "principal_id"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", getattr(self, name)):
                raise ValueError(f"Invalid {name}")
        self.workspace.mkdir(parents=True, exist_ok=True)

    @property
    def workspace_id(self):
        return hashlib.sha256(str(self.workspace).encode()).hexdigest()[:24]


def create_local_context(workspace, session_id="default", **kwargs):
    return ExecutionContext(Path(workspace), session_id, **kwargs)
