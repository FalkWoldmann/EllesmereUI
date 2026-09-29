#!/usr/bin/env bash
# One-shot local lint: fetch the pinned toolchain (first run only), then run the
# same LuaLS baseline gate as CI (~80s).
#   .tools/lint/check.sh                   # CI-equivalent gate
#   .tools/lint/check.sh --update-baseline # accept current findings
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
.tools/lint/fetch-tools.sh
exec python3 .tools/lint/luals_check.py "$@"
