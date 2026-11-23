#!/usr/bin/env bash
# Build `osd` for a local release archive.
#
#   scripts/dev/build-osd-sidecar.sh <rust-target>
#
# Unlike the other three sidecars this one is not fetched — it is OURS, and it
# compiles the web client into itself (crates/osd-cli/build.rs), so the frontend
# has to exist BEFORE it is built, hence the explicit build here: an `osd` staged
# against a stale `dist/` would serve a stale UI to every browser that reaches
# it. Cargo and Vite both no-op when nothing changed, so the double build costs
# almost nothing.
#
# The release archive places `osd` next to its runtime binaries.
set -euo pipefail

target="${1:?usage: build-osd-sidecar.sh <rust-target>}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ext=""
case "$target" in *windows*) ext=".exe" ;; esac

echo "Building the frontend so osd embeds the current web client..."
(cd "$root" && pnpm --filter @ai4s/web build)

echo "Building osd for ${target}..."
cargo build --release --target "$target" --package osd-cli --manifest-path "$root/Cargo.toml"

dest_dir="$root/dist-sidecars"
mkdir -p "$dest_dir"
cp "$root/target/$target/release/osd$ext" "$dest_dir/osd-$target$ext"
chmod +x "$dest_dir/osd-$target$ext"
ls -la "$dest_dir/osd-$target$ext"
