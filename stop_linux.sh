#!/usr/bin/env bash
# Stop only this checkout's local launcher; it shuts down its own children.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
project_root="$(pwd -P)"
found=false
for proc_dir in /proc/[0-9]*; do
    [[ -r "$proc_dir/cmdline" ]] || continue
    cmdline="$(tr '\0' ' ' < "$proc_dir/cmdline" 2>/dev/null || true)"
    [[ "$cmdline" == *"-m services.launcher"* ]] || continue
    [[ "$(readlink "$proc_dir/cwd" 2>/dev/null || true)" == "$project_root" ]] || continue
    kill -TERM "${proc_dir##*/}"
    found=true
done
if [[ "$found" == false ]]; then
    echo "No local launcher is running. If started manually, use Ctrl+C in its terminal."
fi
