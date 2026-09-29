#!/usr/bin/env bash
# Download the pinned static-analysis toolchain into .tools/cache (gitignored).
# Idempotent: a tool is only fetched when its pinned version is not present yet.
# Used by CI (.github/workflows/lint.yml) and locally (.tools/lint/check.sh).
set -euo pipefail

LUALS_VERSION="3.19.1"
# Ketho/vscode-wow-api: community WoW API annotations (LuaCATS) for LuaLS.
WOW_API_COMMIT="d0b5b51fac4c52c493371b9b18e66ce604ea4326"
EMMYLUA_VERSION="0.25.1"
# NumyAddon/FramexmlAnnotations, branch live-mix-into-source (retail 12.1.0 build
# 69933): Blizzard's FrameXML Lua source with generated annotations. Provides the
# FrameXML globals (RAID_CLASS_COLORS, RegisterStateDriver, CharacterFrame, ...).
FRAMEXML_COMMIT="cdb5b000a59967b0ebfea3f6e989cf4f50175013"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CACHE="$ROOT/.tools/cache"
mkdir -p "$CACHE"

case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  luals_os="darwin-arm64"; emmy_os="darwin-arm64" ;;
    Darwin-x86_64) luals_os="darwin-x64";   emmy_os="darwin-x64" ;;
    Linux-x86_64)  luals_os="linux-x64";    emmy_os="linux-x64" ;;
    Linux-aarch64) luals_os="linux-arm64";  emmy_os="linux-aarch64-glibc.2.17" ;;
    *) echo "unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

# lua-language-server (the CI gate)
if [[ "$("$CACHE/luals/bin/lua-language-server" --version 2>/dev/null)" != "$LUALS_VERSION" ]]; then
    echo "Fetching lua-language-server $LUALS_VERSION ($luals_os)"
    rm -rf "$CACHE/luals" && mkdir -p "$CACHE/luals"
    curl -fsSL "https://github.com/LuaLS/lua-language-server/releases/download/$LUALS_VERSION/lua-language-server-$LUALS_VERSION-$luals_os.tar.gz" \
        | tar xz -C "$CACHE/luals"
fi

# WoW API annotations (Core only: C API, widgets, Lua, libraries)
if [[ "$(git -C "$CACHE/wow-api" rev-parse HEAD 2>/dev/null)" != "$WOW_API_COMMIT" ]]; then
    echo "Fetching Ketho/vscode-wow-api @ ${WOW_API_COMMIT:0:7}"
    rm -rf "$CACHE/wow-api"
    git init -q "$CACHE/wow-api"
    git -C "$CACHE/wow-api" fetch -q --depth 1 https://github.com/Ketho/vscode-wow-api "$WOW_API_COMMIT"
    git -C "$CACHE/wow-api" checkout -q FETCH_HEAD
fi

# Blizzard FrameXML source + annotations (~46 MB)
if [[ "$(git -C "$CACHE/framexml-src" rev-parse HEAD 2>/dev/null)" != "$FRAMEXML_COMMIT" ]]; then
    echo "Fetching NumyAddon/FramexmlAnnotations @ ${FRAMEXML_COMMIT:0:7}"
    rm -rf "$CACHE/framexml-src"
    git init -q "$CACHE/framexml-src"
    git -C "$CACHE/framexml-src" fetch -q --depth 1 https://github.com/NumyAddon/FramexmlAnnotations "$FRAMEXML_COMMIT"
    git -C "$CACHE/framexml-src" checkout -q FETCH_HEAD
fi

# emmylua_check (optional, for trying the Rust analyzer by hand): only with --with-emmylua
if [[ "${1:-}" == "--with-emmylua" ]]; then
    if [[ "$("$CACHE/emmylua/emmylua_check" --version 2>/dev/null)" != "emmylua_check $EMMYLUA_VERSION" ]]; then
        echo "Fetching emmylua_check $EMMYLUA_VERSION ($emmy_os)"
        rm -rf "$CACHE/emmylua" && mkdir -p "$CACHE/emmylua"
        curl -fsSL "https://github.com/EmmyLuaLs/emmylua-analyzer-rust/releases/download/$EMMYLUA_VERSION/emmylua_check-$emmy_os.tar.gz" \
            | tar xz -C "$CACHE/emmylua"
    fi
fi
