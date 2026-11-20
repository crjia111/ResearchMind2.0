"""Start the local AgentScope backend and UI; manage only our child processes."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def load_local_config(env_file=None):
    env_file = Path(env_file).resolve() if env_file else ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print("Created .env. Configure MODEL_USE, OPENAI_API_KEY and OPENAI_BASE_URL for AI requests.", flush=True)
    env = os.environ.copy()
    env.update({key: value for key, value in dotenv_values(env_file).items() if value is not None})
    defaults = {
        "RESEARCHMIND_HTTP_HOST": "127.0.0.1", "RESEARCHMIND_HTTP_PORT": "50002",
        "RESEARCHMIND_WS_HOST": "127.0.0.1", "RESEARCHMIND_WS_PORT": "50003",
        "PAPER_SEARCH_MCP_HOST": "127.0.0.1", "PAPER_SEARCH_MCP_PORT": "50004",
        "SIMULATION_MCP_HOST": "127.0.0.1", "SIMULATION_MCP_PORT": "50005",
        "DATABASE_MCP_HOST": "127.0.0.1", "DATABASE_MCP_PORT": "50006",
        "VITE_FRONTEND_HOST": "127.0.0.1", "VITE_FRONTEND_PORT": "50010",
        "VITE_API_URL": "/api", "VITE_WS_URL": "/ws",
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value
    for prefix in ("PAPER_SEARCH", "SIMULATION", "DATABASE"):
        env.setdefault(f"{prefix}_MCP_URL", f"http://{env[f'{prefix}_MCP_HOST']}:{env[f'{prefix}_MCP_PORT']}/sse")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def endpoints(env):
    return [(name, env[f"{prefix}_HOST"], int(env[f"{prefix}_PORT"])) for name, prefix in (
        ("HTTP API", "RESEARCHMIND_HTTP"), ("WebSocket", "RESEARCHMIND_WS"),
        ("UI", "VITE_FRONTEND"),
    )]


def check_ports(env):
    configured = endpoints(env)
    seen = set()
    for name, host, port in configured:
        if port in seen:
            raise RuntimeError(f"Duplicate port {port} for {name}; configure separate ports in .env.")
        seen.add(port)
    for name, host, port in configured:
        try:
            with socket.socket() as sock:
                sock.bind((host, port))
        except OSError as error:
            raise RuntimeError(f"{name} cannot bind {host}:{port}: {error}. Stop that service or change .env.") from error


def stop_children(children):
    for child in reversed(children):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 10
    for child in children:
        try:
            child.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
    if os.name != "nt":
        # npm can exit before Vite; wait for the entire process group to stop.
        for child in children:
            while True:
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= deadline:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description="Run ResearchMind locally without login.")
    parser.add_argument("--check", action="store_true", help="Check local configuration and available ports without starting services")
    parser.add_argument("--env-file", help="Use an alternative local environment file")
    parser.add_argument("--stop-file", help="Gracefully stop all managed children when this file appears")
    args = parser.parse_args()
    children, logs = [], []
    try:
        env = load_local_config(args.env_file)
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise RuntimeError("Node.js/npm is required. Install Node.js 18 or newer.")
        check_ports(env)
        if args.check:
            for name, host, port in endpoints(env):
                print(f"{name}: {host}:{port}")
            return 0
        if not (ROOT / "ui/node_modules").exists():
            subprocess.run([npm, "ci"], cwd=ROOT / "ui", env=env, check=True)
        log_dir = Path(env.get("RESEARCHMIND_LOG_DIR") or ROOT / "data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        services = [
            ("backend", [sys.executable, "main.py"], ROOT),
            ("frontend", [npm, "run", "dev", "--", "--host", env["VITE_FRONTEND_HOST"],
                          "--port", env["VITE_FRONTEND_PORT"]], ROOT / "ui"),
        ]
        def interrupted(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, interrupted)
        for name, command, cwd in services:
            log = open(log_dir / f"{name}.log", "w", encoding="utf-8")
            logs.append(log)
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            children.append(subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, **options))
            print(f"Starting {name}; log: {log_dir / f'{name}.log'}", flush=True)
        pending = endpoints(env)
        deadline = time.monotonic() + 180
        while True:
            if args.stop_file and Path(args.stop_file).exists():
                return 0
            for (name, _, _), child in zip(services, children):
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited with code {child.returncode}; see {log_dir / f'{name}.log'}")
            if pending:
                for endpoint in list(pending):
                    name, host, port = endpoint
                    connect_host = "127.0.0.1" if host == "0.0.0.0" else host
                    try:
                        with socket.create_connection((connect_host, port), timeout=0.2):
                            pending.remove(endpoint)
                            print(f"Ready: {name}", flush=True)
                    except OSError:
                        pass
                if not pending:
                    print(f"ResearchMind: http://localhost:{env['VITE_FRONTEND_PORT']}\n"
                          f"API docs: http://localhost:{env['RESEARCHMIND_HTTP_PORT']}/docs\n"
                          "No login required. Press Ctrl+C to stop all services.", flush=True)
                elif time.monotonic() > deadline:
                    raise RuntimeError(f"Startup timed out: {', '.join(item[0] for item in pending)}; see {log_dir}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping local services...", flush=True)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"Startup failed: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop_children(children)
        for log in logs:
            log.close()


if __name__ == "__main__":
    sys.exit(main())
