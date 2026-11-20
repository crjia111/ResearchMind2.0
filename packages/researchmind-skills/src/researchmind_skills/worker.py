"""Durable worker. Each scientific task executes in its own child process."""

import argparse
import asyncio
import time
import uuid
from .api import Runtime, create_local_context
from .runtime.store import Store


async def serve(workspace, principal_id="local"):
    worker_id = uuid.uuid4().hex
    context = create_local_context(workspace, principal_id=principal_id)
    store = Store(context)
    runtime = Runtime()
    active = {}
    try:
        while True:
            runtime.recover_stale_jobs(context)
            with store.db() as db:
                db.execute(
                    "INSERT OR REPLACE INTO workers VALUES(?,?)",
                    (worker_id, time.time()),
                )
                rows = db.execute(
                    "SELECT id,session FROM jobs WHERE status='queued' AND cancel=0 LIMIT 1"
                ).fetchall()
                # Claim atomically before spawning to avoid duplicate workers.
                claimed = []
                for row in [] if active else rows:
                    if db.execute(
                        "UPDATE jobs SET status='starting',updated=? WHERE id=? AND status='queued'",
                        (time.time(), row["id"]),
                    ).rowcount:
                        claimed.append(dict(row))
            for row in claimed:
                ctx = create_local_context(
                    workspace, row["session"], principal_id=principal_id
                )
                active[row["id"]] = asyncio.create_task(
                    runtime._wait_job(row["id"], ctx)
                )
            active = {key: task for key, task in active.items() if not task.done()}
            with store.db() as db:
                cancelled = db.execute(
                    "SELECT id,session,operation,request FROM jobs WHERE status='queued' AND cancel=1"
                ).fetchall()
            from .runtime.contracts import failure, CapabilityError

            for row in cancelled:
                runtime._save_job(
                    store,
                    row["id"],
                    failure(
                        row["operation"],
                        row["request"].split(":", 1)[1],
                        CapabilityError("CANCELLED", "Cancelled before execution"),
                    ),
                )
            await asyncio.sleep(0.5)
    finally:
        for task in active.values():
            task.cancel()
        await asyncio.gather(*active.values(), return_exceptions=True)
        with store.db() as db:
            db.execute("DELETE FROM workers WHERE id=?", (worker_id,))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--session", default="default")
    parser.add_argument("--job")
    parser.add_argument("--principal", default="local")
    args = parser.parse_args()
    if args.job:
        asyncio.run(
            Runtime()._perform(
                args.job,
                create_local_context(
                    args.workspace, args.session, principal_id=args.principal
                ),
            )
        )
    else:
        asyncio.run(serve(args.workspace, args.principal))


if __name__ == "__main__":
    main()
