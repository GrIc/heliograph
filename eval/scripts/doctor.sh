#!/usr/bin/env bash
# Quick env diagnostics : ports, Python, deps, Heliograph reachability.
set -uo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m⚠\033[0m %s\n" "$*"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$*"; }

echo "▶ Python"
command -v python3 >/dev/null && ok "python3 = $(python3 --version 2>&1)" || fail "python3 missing"

echo "▶ Venv"
[ -d .venv ] && ok ".venv exists" || warn ".venv missing — run ./scripts/setup.sh"

echo "▶ Deps"
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  for pkg in datasets mcp pyyaml rich httpx; do
    python -c "import ${pkg}" 2>/dev/null && ok "import $pkg" || fail "missing: $pkg"
  done
fi

echo "▶ Heliograph MCP"
HUB_URL="${HELIOGRAPH_URL:-http://localhost:8080/mcp/sse}"
if curl -sf --max-time 3 "$HUB_URL" -o /dev/null; then
  ok "$HUB_URL reachable"
else
  warn "$HUB_URL not reachable (docker compose up -d ?)"
fi

echo "▶ Disk"
df -h . | tail -1 | awk '{printf "  used %s / %s (%s)\n", $3, $2, $5}'

echo "▶ HF cache"
HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
[ -d "$HF_HOME" ] && ok "$HF_HOME ($(du -sh "$HF_HOME" 2>/dev/null | cut -f1))" || warn "no HF cache yet"
