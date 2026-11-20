"""Stable JSON CLI. Scientific/log output is confined to stderr."""

import argparse
import asyncio
import contextlib
import json
from pathlib import Path
import sys
from .api import Runtime, create_local_context
from .runtime.contracts import CapabilityError, failure, result
from .runtime.registry import BUNDLES, SKILLS, list_capabilities, describe
from .runtime.store import Store
from .installer import install, uninstall


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CapabilityError("INVALID_ARGUMENT", message)


def parser():
    root = Parser(prog="researchmind-skills")
    sub = root.add_subparsers(dest="command", required=True, parser_class=Parser)
    for command in ("install", "uninstall", "list", "doctor"):
        cmd = sub.add_parser(command)
        cmd.add_argument("--target", default="./skills")
        cmd.add_argument("--bundle", choices=BUNDLES)
        cmd.add_argument("--skill", choices=SKILLS)
        cmd.add_argument("--output-format", choices=["json"], default="json")
    caps = sub.add_parser("capabilities")
    caps.add_argument("action", choices=["list", "describe"])
    caps.add_argument("operation", nargs="?")
    caps.add_argument("--skill", choices=SKILLS)
    caps.add_argument("--output-format", default="json", choices=["json"])
    run = sub.add_parser("run")
    run.add_argument("operation")
    run.add_argument("--skill", choices=SKILLS)
    run.add_argument("--input-file", default="-")
    run.add_argument("--wait", action="store_true")
    run.add_argument("--request-id")
    run.add_argument("--events-file")
    for command, choices in (
        ("jobs", ["status", "result", "cancel"]),
        ("artifacts", ["import", "read"]),
        ("worker", ["run"]),
    ):
        cmd = sub.add_parser(command)
        cmd.add_argument("action", choices=choices)
        if command != "worker":
            cmd.add_argument("identifier")
    for cmd in (
        run,
        sub.choices["jobs"],
        sub.choices["artifacts"],
        sub.choices["worker"],
    ):
        cmd.add_argument("--workspace", default="./research-work")
        cmd.add_argument("--session", default="default")
        cmd.add_argument("--output-format", choices=["json"], default="json")
    return root


def main(argv=None, fixed_skill=None):
    operation = "cli"
    request_id = ""
    try:
        args = parser().parse_args(argv)
        if args.command == "run":
            operation = args.operation
            request_id = args.request_id or ""
            if fixed_skill and args.skill and args.skill != fixed_skill:
                raise CapabilityError(
                    "ACCESS_DENIED", "Script has a fixed Skill binding"
                )
            content = (
                sys.stdin.read()
                if args.input_file == "-"
                else Path(args.input_file).read_text(encoding="utf-8-sig")
            )
            try:
                payload = json.loads(content)
            except ValueError as exc:
                raise CapabilityError(
                    "INVALID_ARGUMENT", "Input must be valid JSON"
                ) from exc
            context = create_local_context(args.workspace, args.session)
            if args.events_file:

                def sink(event):
                    with Path(args.events_file).open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(event, ensure_ascii=False) + "\n")

                context.event_sink = sink
            with contextlib.redirect_stdout(sys.stderr):
                response = asyncio.run(
                    Runtime().execute(
                        operation,
                        payload,
                        context,
                        fixed_skill or args.skill,
                        args.wait,
                        request_id=args.request_id,
                    )
                )
        elif args.command == "capabilities":
            data = (
                describe(args.operation)
                if args.action == "describe"
                else list_capabilities(args.skill)
            )
            response = result("capabilities", "", data=data)
        elif args.command in ("install", "uninstall"):
            data = (install if args.command == "install" else uninstall)(
                args.target, args.bundle, args.skill
            )
            response = result(args.command, "", data=data)
        elif args.command == "list":
            path = Path(args.target) / ".researchmind-install.json"
            response = result(
                "list", "", data=json.loads(path.read_text()) if path.exists() else {}
            )
        elif args.command == "doctor":
            names = (
                BUNDLES[args.bundle]
                if args.bundle
                else ([args.skill] if args.skill else list(SKILLS))
            )
            diagnostics = {n: Runtime().doctor(n) for n in names}
            installed = Path(args.target)
            response = result(
                "doctor",
                "",
                data={
                    n: {
                        "resource_installed": (installed / n / "SKILL.md").is_file(),
                        "host_enabled": None,
                        "capabilities": v,
                    }
                    for n, v in diagnostics.items()
                },
            )
        else:
            context = create_local_context(args.workspace, args.session)
            runtime = Runtime()
            if args.command == "worker":
                from .worker import serve

                asyncio.run(serve(args.workspace))
                return 0
            if args.command == "jobs":
                method = {
                    "status": runtime.get_job,
                    "result": runtime.get_job_result,
                    "cancel": runtime.cancel_job,
                }[args.action]
                data = method(args.identifier, context)
                response = (
                    data
                    if args.action == "result"
                    else result("jobs." + args.action, "", data=data)
                )
            elif args.action == "import":
                response = result(
                    "artifacts.import",
                    "",
                    artifacts=[Store(context).import_file(args.identifier)],
                )
            else:
                path = Store(context).resolve(args.identifier)
                response = result(
                    "artifacts.read",
                    "",
                    data={"content": path.read_text(encoding="utf-8")},
                )
    except CapabilityError as exc:
        response = failure(operation, request_id, exc)
    except (ValueError, OSError) as exc:
        response = failure(
            operation, request_id, CapabilityError("INVALID_ARGUMENT", str(exc))
        )
    except KeyboardInterrupt:
        response = failure(
            operation, request_id, CapabilityError("CANCELLED", "Interrupted")
        )
        print(json.dumps(response, ensure_ascii=False))
        return 130
    except Exception:
        import logging

        logging.exception("CLI failed")
        response = failure(
            operation,
            request_id,
            CapabilityError("INTERNAL_ERROR", "Unexpected error; inspect stderr"),
        )
    print(json.dumps(response, ensure_ascii=False, default=str))
    if response["status"] == "partial":
        return 3
    if response["status"] == "failed":
        return (
            2
            if response["error"]["code"] == "INVALID_ARGUMENT"
            else (5 if response["error"]["code"] == "INTERNAL_ERROR" else 4)
        )
    return 0
