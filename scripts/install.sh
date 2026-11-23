#!/bin/sh
# Install the local ResearchMind server and Web client on Linux for the current
# user — no root, no package manager, nothing outside $HOME.
#
#   curl -fsSL https://raw.githubusercontent.com/crjia111/ResearchMind2.0/main/scripts/install.sh | sh
#   curl -fsSL …/install.sh | sh -s -- --uninstall
#
# The installer provides `osd`, the local server and CLI. The Web client is
# served over HTTP by `osd server` and opens in the user's browser.
#
# Layout:
#   ~/.local/share/researchmind/osd/        the osd archive, unpacked
#   ~/.local/share/researchmind/osd/        the server archive, unpacked
#   ~/.local/bin/osd                        a wrapper (not a symlink: osd finds
#                                           its sidecars next to its real path)
#
# Environment: OSD_VERSION=0.6.1 pins a release (default: latest).
#              OSD_DOWNLOAD_BASE overrides the release download URL (a mirror).
set -eu

REPO="crjia111/ResearchMind2.0"
# Shared with the CLI wrapper, so an existing install can be replaced safely.
SIGNATURE="ResearchMind CLI wrapper"

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA/researchmind"
BIN="$HOME/.local/bin"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

case "${1:-}" in
  "") mode=install ;;
  --uninstall) mode=uninstall ;;
  -h|--help) say "usage: install.sh [--uninstall]"; exit 0 ;;
  *) die "unknown option: $1 (use --uninstall)" ;;
esac

# Remove a file only when this project wrote it.
remove_ours() {
  if [ -f "$1" ] && grep -q "$SIGNATURE" "$1" 2>/dev/null; then
    rm -f "$1"
  fi
}

if [ "$mode" = uninstall ]; then
  rm -rf "$PREFIX"
  remove_ours "$BIN/osd"
  say "Removed ResearchMind from $PREFIX."
  say "Your workspace (~/Documents/ResearchMind) and settings were left in place."
  exit 0
fi

[ "$(uname -s)" = Linux ] || die "this installer is for Linux; get the macOS/Windows installer from https://github.com/$REPO/releases/latest"
command -v curl > /dev/null 2>&1 || die "curl is required"
command -v tar > /dev/null 2>&1 || die "tar is required"

case "$(uname -m)" in
  x86_64|amd64) target=x86_64-unknown-linux-gnu ;;
  aarch64|arm64) target=aarch64-unknown-linux-gnu ;;
  *) die "unsupported architecture: $(uname -m) (x86_64 and aarch64 only)" ;;
esac

# The latest version from the redirect of /releases/latest — no API call, so
# no rate limit.
version="${OSD_VERSION:-}"
if [ -z "$version" ]; then
  location=$(curl -fsSI "https://github.com/$REPO/releases/latest" | tr -d '\r' | sed -n 's/^[Ll]ocation: .*\/tag\/v\{0,1\}//p')
  version="$location"
  [ -n "$version" ] || die "could not determine the latest version (set OSD_VERSION=x.y.z)"
fi
version="${version#v}"
base="${OSD_DOWNLOAD_BASE:-https://github.com/$REPO/releases/download/v$version}"

archive="osd-$version-$target.tar.gz"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM

say "Downloading $archive…"
if ! curl -fL --progress-bar -o "$tmp/$archive" "$base/$archive"; then
  die "download failed: $base/$archive"
fi
mkdir "$tmp/unpacked"
tar -xzf "$tmp/$archive" -C "$tmp/unpacked"

# Swap the new copy in only after it unpacked completely.
mkdir -p "$PREFIX"
dest="$PREFIX/osd"
osd_bin="$dest/osd"
rm -rf "$dest"
mv "$tmp/unpacked/"* "$dest"
[ -x "$osd_bin" ] || die "the archive did not contain $osd_bin"

# Write a wrapper unless something that is not ours already has the name.
write_wrapper() {
  path="$1"
  binary="$2"
  if [ -e "$path" ] && ! grep -q "$SIGNATURE" "$path" 2>/dev/null; then
    say "warning: $path exists and is not ours; left it alone"
    return 0
  fi
  cat > "$path" <<EOF
#!/bin/sh
# $SIGNATURE. A wrapper, not a symlink: osd finds its sidecars and
# bundled resources next to the real executable.
if [ ! -x "$binary" ]; then
	echo "ResearchMind is no longer installed; removing this leftover command." >&2
	rm -f -- "\$0"
	exit 127
fi
exec "$binary" "\$@"
EOF
  chmod 755 "$path"
}

mkdir -p "$BIN"
write_wrapper "$BIN/osd" "$osd_bin"

say ""
say "Installed ResearchMind $version in $dest"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) say "Add $BIN to your PATH:  export PATH=\"$BIN:\$PATH\"" ;;
esac
say "Start it with:  osd server        (osd --help for everything else)"
