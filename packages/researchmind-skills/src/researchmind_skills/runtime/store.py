"""SQLite-backed workspace/session ownership, artifacts and durable records."""

from contextlib import contextmanager
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from .contracts import CapabilityError


class Store:
    def __init__(self, context):
        self.context = context
        self.root = context.workspace / ".researchmind"
        if context.principal_id != "local":
            self.root = self.root / "principals" / context.principal_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "runtime.sqlite"
        with self.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS state(session TEXT,key TEXT,value TEXT,PRIMARY KEY(session,key))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,session TEXT,path TEXT,kind TEXT,hash TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,session TEXT,operation TEXT,payload TEXT,skill TEXT,status TEXT,result TEXT,request TEXT UNIQUE,cancel INTEGER DEFAULT 0)"
            )
            if "updated" not in {
                row[1] for row in db.execute("PRAGMA table_info(jobs)")
            }:
                db.execute(
                    "ALTER TABLE jobs ADD COLUMN updated REAL NOT NULL DEFAULT 0"
                )
            db.execute(
                "CREATE TABLE IF NOT EXISTS workers(id TEXT PRIMARY KEY,heartbeat REAL)"
            )

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, key, default=None):
        with self.db() as db:
            row = db.execute(
                "SELECT value FROM state WHERE session=? AND key=?",
                (self.context.session_id, key),
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def set(self, key, value):
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO state VALUES(?,?,?)",
                (self.context.session_id, key, json.dumps(value, ensure_ascii=False)),
            )

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise CapabilityError("ACCESS_DENIED", "Path escapes workspace")
        return path

    def artifact(self, name, content, kind="text"):
        if Path(name).name != name or name in (".", "..") or not name:
            raise CapabilityError(
                "INVALID_ARGUMENT", "Artifact name must be a filename"
            )
        ident = uuid.uuid4().hex
        path = self.path(Path("artifacts") / self.context.session_id / ident / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = content.encode("utf-8") if isinstance(content, str) else content
        path.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        with self.db() as db:
            db.execute(
                "INSERT INTO artifacts VALUES(?,?,?,?,?)",
                (
                    ident,
                    self.context.session_id,
                    str(path.relative_to(self.root)),
                    kind,
                    digest,
                ),
            )
        return dict(artifact_id=ident, name=name, kind=kind, sha256=digest)

    def resolve(self, ident):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM artifacts WHERE id=? AND session=?",
                (ident, self.context.session_id),
            ).fetchone()
        if not row:
            raise CapabilityError(
                "ARTIFACT_NOT_FOUND", "Artifact not found in current session"
            )
        path = self.path(row["path"])
        if not path.is_file():
            raise CapabilityError("ARTIFACT_NOT_FOUND", "Artifact file is missing")
        return path

    def import_file(self, path):
        path = Path(path).resolve()
        roots = [self.context.workspace] + [
            Path(p).resolve() for p in self.context.input_roots
        ]
        if not any(path.is_relative_to(root) for root in roots):
            raise CapabilityError(
                "ACCESS_DENIED", "Input is outside configured import roots"
            )
        if not path.is_file():
            raise CapabilityError("ARTIFACT_NOT_FOUND", "Input file is missing")
        return self.artifact(
            path.name, path.read_bytes(), path.suffix.lstrip(".") or "file"
        )
