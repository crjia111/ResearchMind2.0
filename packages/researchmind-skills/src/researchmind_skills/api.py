"""Public execution API. All frameworks and the CLI use this boundary."""

import asyncio
import importlib.util
import json
import logging
import os
import time
import uuid
from pathlib import Path
from .runtime.context import (
    create_local_context as create_local_context,
    ExecutionContext as ExecutionContext,
)
from .runtime.contracts import CapabilityError, failure, result, validate
from .runtime.registry import SKILLS, describe, list_capabilities
from .runtime.store import Store

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, config=None):
        self.config = config or {}

    @classmethod
    def from_config(cls, config_path=None):
        return cls(
            json.loads(Path(config_path).read_text(encoding="utf-8"))
            if config_path
            else {}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def describe(self, operation):
        return describe(operation)

    def list_capabilities(self, skill_name=None):
        return list_capabilities(skill_name)

    def doctor(self, skill_name=None):
        diagnostics = []
        for spec in list_capabilities(skill_name):
            operation = spec["operation"]
            required = []
            if spec["dependency"]:
                required.append(spec["dependency"])
            if operation == "papers.import_uploads":
                required.append("pypdf")
            if operation in (
                "materials.query_mp",
                "materials.query_oqmd",
                "materials.query_cod",
                "materials.query_aflow",
                "materials.search",
                "materials.recommend",
            ):
                required.append("pymatgen")
            if operation.startswith("simulation.") and operation not in (
                "simulation.generate",
                "simulation.cache.clear",
            ):
                required.append("ase")
            if operation in ("simulation.generate", "simulation.kappa"):
                required.extend(["torch", "pymatgen", "pandas"])
            if operation == "simulation.generate":
                required.extend(["omegaconf", "zmq"])
            missing = []
            for dependency in sorted(set(required)):
                try:
                    available = importlib.util.find_spec(dependency) is not None
                except (ImportError, ValueError):
                    available = False
                if not available:
                    missing.append(dependency)
            variables = []
            if operation in ("papers.plan", "papers.analyze", "papers.report"):
                variables.append("OPENAI_API_KEY")
            if operation in ("papers.web_search", "papers.news_search"):
                variables.append("TAVILY_API_KEY")
            if operation == "materials.query_mp":
                variables.append("MP_API_KEY")
            model_paths = {}
            if operation in (
                "simulation.energy",
                "simulation.relax",
                "simulation.phonon",
            ):
                model_paths["MATTERSIM_MODEL_PATH"] = False
            if operation == "simulation.generate":
                model_paths["CRYSTALLM_MODEL_DIR"] = True
            if operation == "simulation.kappa":
                model_paths.update(KAPPA_MODEL_DIR=True, KAPPA_ATOM_INIT=False)
            for name in variables:
                if not os.environ.get(name):
                    missing.append(name)
            for name, directory in model_paths.items():
                path = Path(os.environ.get(name, "")).expanduser()
                if not os.environ.get(name) or not (
                    path.is_dir() if directory else path.is_file()
                ):
                    missing.append(name)
            if operation in ("papers.index", "papers.semantic_search") and not (
                os.environ.get("GOOGLE_API_KEY")
                or (
                    os.environ.get("OPENAI_API_KEY")
                    and os.environ.get("OPENAI_EMBEDDING_MODEL")
                )
            ):
                missing.append("embedding_credentials")
            diagnostics.append(
                dict(
                    operation=operation,
                    available=not missing,
                    missing=missing,
                    network_verified=False,
                )
            )
        return diagnostics

    def recover_stale_jobs(self, context):
        store = Store(context)
        with store.db() as db:
            rows = db.execute(
                "SELECT * FROM jobs WHERE status IN ('starting','running') AND updated<? AND result IS NULL",
                (time.time() - 30,),
            ).fetchall()
            for row in rows:
                response = failure(
                    row["operation"],
                    row["request"].split(":", 1)[1],
                    CapabilityError(
                        "WORKER_LOST",
                        "The task supervisor stopped; inspect outputs before explicitly retrying",
                    ),
                )
                db.execute(
                    "UPDATE jobs SET status='failed',result=? WHERE id=? AND result IS NULL",
                    (json.dumps(response), row["id"]),
                )

    async def execute(
        self, operation, payload, context, skill_name=None, wait=True, request_id=None
    ):
        request_id = request_id or uuid.uuid4().hex
        try:
            spec = describe(operation)
            if skill_name:
                from importlib.resources import files

                if skill_name not in SKILLS:
                    raise CapabilityError("INVALID_ARGUMENT", "Unknown skill")
                manifest = json.loads(
                    files("researchmind_skills")
                    .joinpath("skill_assets", skill_name, "skill.json")
                    .read_text(encoding="utf-8")
                )
                from . import __version__

                if manifest.get("runtime_version") != __version__:
                    raise CapabilityError(
                        "RUNTIME_VERSION_MISMATCH", "Skill/runtime versions differ"
                    )
                if manifest.get("schema_version") != "1.0":
                    raise CapabilityError(
                        "SCHEMA_VERSION_UNSUPPORTED", "Unsupported skill schema"
                    )
            validate(spec["input_schema"], payload)
            if skill_name:
                if skill_name not in spec["skills"]:
                    raise CapabilityError(
                        "ACCESS_DENIED", "Capability is not bound to this Skill"
                    )
                if context.allowed_skills and skill_name not in context.allowed_skills:
                    raise CapabilityError(
                        "ACCESS_DENIED", "Skill is not enabled by the host"
                    )
            elif context.allowed_skills and not set(spec["skills"]).intersection(
                context.allowed_skills
            ):
                raise CapabilityError(
                    "ACCESS_DENIED", "Capability is not enabled by the host"
                )
            store = Store(context)
            # request IDs are scoped to a session; payload fingerprints prevent accidental reuse.
            scoped = context.session_id + ":" + request_id
            encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            with store.db() as db:
                old = db.execute(
                    "SELECT * FROM jobs WHERE request=?", (scoped,)
                ).fetchone()
                if old:
                    if old["operation"] != operation or old["payload"] != encoded:
                        raise CapabilityError(
                            "INVALID_ARGUMENT",
                            "Request ID already used with different arguments",
                        )
                    if old["result"]:
                        return json.loads(old["result"])
                    return result(operation, request_id, "accepted", job_id=old["id"])
            if not wait and spec["long_running"]:
                with store.db() as db:
                    live = db.execute(
                        "SELECT 1 FROM workers WHERE heartbeat>?", (time.time() - 15,)
                    ).fetchone()
                if not live:
                    raise CapabilityError(
                        "CAPABILITY_UNAVAILABLE", "Start a worker or use --wait"
                    )
            ident = uuid.uuid4().hex
            with store.db() as db:
                # SQLite UNIQUE is authoritative for concurrent duplicate submissions.
                try:
                    db.execute(
                        "INSERT INTO jobs(id,session,operation,payload,skill,status,request,updated) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            ident,
                            context.session_id,
                            operation,
                            encoded,
                            skill_name,
                            "queued"
                            if not wait and spec["long_running"]
                            else "starting",
                            scoped,
                            time.time(),
                        ),
                    )
                except __import__("sqlite3").IntegrityError:
                    old = db.execute(
                        "SELECT * FROM jobs WHERE request=?", (scoped,)
                    ).fetchone()
                    if old["operation"] != operation or old["payload"] != encoded:
                        raise CapabilityError(
                            "INVALID_ARGUMENT",
                            "Request ID already used with different arguments",
                        )
                    return (
                        json.loads(old["result"])
                        if old["result"]
                        else result(operation, request_id, "accepted", job_id=old["id"])
                    )
            if not wait and spec["long_running"]:
                return result(operation, request_id, "accepted", job_id=ident)
            if spec["long_running"]:
                return await self._wait_job(ident, context)
            return await self._perform(ident, context)
        except CapabilityError as exc:
            return failure(operation, request_id, exc)
        except (ImportError, ModuleNotFoundError) as exc:
            return failure(
                operation,
                request_id,
                CapabilityError(
                    "DEPENDENCY_UNAVAILABLE",
                    f"Install the optional dependency: {exc.name}",
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Capability failed: %s", operation)
            return failure(
                operation,
                request_id,
                CapabilityError(
                    "INTERNAL_ERROR", "Unexpected runtime error; inspect the local log"
                ),
            )

    async def _perform(self, job_id, context):
        store = Store(context)
        row = self._job(job_id, context)
        request_id = row["request"].split(":", 1)[1]
        operation = row["operation"]
        with store.db() as db:
            db.execute(
                "UPDATE jobs SET status='running',updated=? WHERE id=?",
                (time.time(), job_id),
            )
        if context.event_sink:
            await self._emit(
                context,
                dict(
                    type="job_status",
                    job_id=job_id,
                    status="running",
                    operation=operation,
                    session_id=context.session_id,
                ),
            )
        try:
            payload = json.loads(row["payload"])
            dispatch_task = asyncio.create_task(
                asyncio.to_thread(self._dispatch, operation, payload, context)
            )
            while not dispatch_task.done():
                done, _ = await asyncio.wait({dispatch_task}, timeout=5)
                if not done:
                    with store.db() as db:
                        db.execute(
                            "UPDATE jobs SET updated=? WHERE id=?",
                            (time.time(), job_id),
                        )
            output = await dispatch_task
            usage = output.pop("usage", {})
            usage.setdefault(
                "successful_units",
                1 if output.get("status", "completed") == "completed" else 0,
            )
            usage.setdefault(
                "real_compute_units",
                1
                if operation.startswith("simulation.")
                and operation != "simulation.validate_cif"
                and output.get("status", "completed") == "completed"
                else 0,
            )
            response = result(
                operation, request_id, job_id=job_id, usage=usage, **output
            )
        except CapabilityError as exc:
            response = failure(operation, request_id, exc)
        except ImportError as exc:
            response = failure(
                operation,
                request_id,
                CapabilityError(
                    "DEPENDENCY_UNAVAILABLE", f"Missing optional dependency: {exc.name}"
                ),
            )
        except asyncio.CancelledError:
            response = failure(
                operation,
                request_id,
                CapabilityError("CANCELLED", "Task was cancelled"),
            )
            self._save_job(store, job_id, response)
            raise
        except Exception:
            logger.exception("Execution error: %s", operation)
            response = failure(
                operation,
                request_id,
                CapabilityError(
                    "INTERNAL_ERROR", "Execution failed; inspect local logs"
                ),
            )
        self._save_job(store, job_id, response)
        if context.event_sink:
            await self._emit(
                context,
                dict(
                    type="capability_result",
                    job_id=job_id,
                    result=response,
                    session_id=context.session_id,
                ),
            )
        return response

    def _dispatch(self, operation, payload, context):
        if operation.startswith("papers."):
            from .runtime.papers import dispatch
        elif operation.startswith("materials."):
            from .runtime.materials import dispatch
        elif operation.startswith("simulation."):
            from .runtime.simulation import dispatch
        elif operation.startswith("diagnostics."):
            return {
                "data": {
                    "capabilities": self.doctor(
                        "materials-search"
                        if operation.endswith("materials")
                        else "structure-optimization"
                    )
                }
            }
        else:
            raise CapabilityError("CAPABILITY_UNAVAILABLE", operation)
        if (
            operation.startswith("simulation.")
            and operation != "simulation.validate_cif"
        ):
            from .runtime.resources import compute_slot

            with compute_slot(context):
                return dispatch(operation, payload, context)
        return dispatch(operation, payload, context)

    async def _emit(self, context, event):
        try:
            outcome = context.event_sink(event)
            if hasattr(outcome, "__await__"):
                await outcome
        except Exception:
            logger.exception(
                "Host event delivery failed; scientific result remains persisted"
            )

    def _save_job(self, store, ident, response):
        with store.db() as db:
            db.execute(
                "UPDATE jobs SET status=?,result=? WHERE id=? AND result IS NULL",
                (
                    response["status"],
                    json.dumps(response, ensure_ascii=False, default=str),
                    ident,
                ),
            )

    def _job(self, ident, context):
        store = Store(context)
        self.recover_stale_jobs(context)
        with store.db() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE id=? AND session=?",
                (ident, context.session_id),
            ).fetchone()
        if row is None:
            raise CapabilityError(
                "ARTIFACT_NOT_FOUND", "Task not found in this session"
            )
        return dict(row)

    def get_job(self, job_id, context):
        row = self._job(job_id, context)
        return {k: row[k] for k in ("id", "operation", "status", "cancel")}

    def get_job_result(self, job_id, context):
        row = self._job(job_id, context)
        return (
            json.loads(row["result"])
            if row["result"]
            else result(
                row["operation"],
                row["request"].split(":", 1)[1],
                "accepted",
                job_id=job_id,
            )
        )

    async def subscribe_events(self, job_id, context, poll_interval=0.25):
        previous = None
        while True:
            status = self.get_job(job_id, context)
            if status != previous:
                yield {
                    "type": "job_status",
                    "job_id": job_id,
                    "session_id": context.session_id,
                    **status,
                }
                previous = status
            if status["status"] in ("completed", "partial", "failed"):
                yield {
                    "type": "capability_result",
                    "job_id": job_id,
                    "result": self.get_job_result(job_id, context),
                    "session_id": context.session_id,
                }
                return
            await asyncio.sleep(poll_interval)

    def cancel_job(self, job_id, context):
        row = self._job(job_id, context)
        if row["status"] in ("completed", "partial", "failed"):
            return self.get_job(job_id, context)
        store = Store(context)
        with store.db() as db:
            db.execute("UPDATE jobs SET cancel=1 WHERE id=?", (job_id,))
        return self.get_job(job_id, context)

    async def _wait_job(self, job_id, context):
        import subprocess
        import sys

        command = [
            sys.executable,
            "-m",
            "researchmind_skills.worker",
            "--workspace",
            str(context.workspace),
            "--session",
            context.session_id,
            "--principal",
            context.principal_id,
            "--job",
            job_id,
        ]
        log = Store(context).root / (job_id + ".log")
        with log.open("ab") as stream:
            options = (
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            child = subprocess.Popen(command, stdout=stream, stderr=stream, **options)
            if context.event_sink:
                await self._emit(
                    context,
                    dict(
                        type="job_status",
                        job_id=job_id,
                        status="running",
                        operation=self._job(job_id, context)["operation"],
                        session_id=context.session_id,
                    ),
                )
            started = time.monotonic()
            timeout = float(
                self.config.get(
                    "compute_timeout",
                    os.environ.get("RESEARCHMIND_COMPUTE_TIMEOUT", "3600"),
                )
            )

            def stop():
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    import signal

                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                child.wait(timeout=10)

            try:
                while child.poll() is None:
                    with Store(context).db() as db:
                        db.execute(
                            "UPDATE jobs SET updated=? WHERE id=?",
                            (time.time(), job_id),
                        )
                    timed_out = time.monotonic() - started > timeout
                    if timed_out or self._job(job_id, context)["cancel"]:
                        stop()
                        response = failure(
                            self._job(job_id, context)["operation"],
                            self._job(job_id, context)["request"].split(":", 1)[1],
                            CapabilityError(
                                "COMPUTE_TIMEOUT" if timed_out else "CANCELLED",
                                "Task timed out" if timed_out else "Task cancelled",
                            ),
                        )
                        self._save_job(Store(context), job_id, response)
                        return response
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                self.cancel_job(job_id, context)
                await asyncio.to_thread(stop)
                row = self._job(job_id, context)
                self._save_job(
                    Store(context),
                    job_id,
                    failure(
                        row["operation"],
                        row["request"].split(":", 1)[1],
                        CapabilityError("CANCELLED", "Task cancelled"),
                    ),
                )
                raise
        row = self._job(job_id, context)
        if not row["result"]:
            response = failure(
                row["operation"],
                row["request"].split(":", 1)[1],
                CapabilityError("INTERNAL_ERROR", "Worker exited without a result"),
            )
            self._save_job(Store(context), job_id, response)
        response = self.get_job_result(job_id, context)
        if context.event_sink:
            await self._emit(
                context,
                dict(
                    type="capability_result",
                    job_id=job_id,
                    result=response,
                    session_id=context.session_id,
                ),
            )
        return response
