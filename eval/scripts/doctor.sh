#!/usr/bin/env bash
# Quick env diagnostics : ports, Python, deps, Heliograph reachability.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run as ./scripts/$(basename "$0") (not 'sh ...')." >&2
  exit 1
fi

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
  # pip pkg name → python import name
  declare -A pkgs=(
    [datasets]=datasets
    [mcp]=mcp
    [pyyaml]=yaml
    [rich]=rich
    [httpx]=httpx
  )
  for pip_name in "${!pkgs[@]}"; do
    import_name="${pkgs[$pip_name]}"
    python -c "import ${import_name}" 2>/dev/null \
      && ok "$pip_name" \
      || fail "missing: $pip_name (pip install -e \".[dev]\")"
  done
fi

echo "▶ Heliograph MCP"
HUB_URL="${HELIOGRAPH_URL:-http://localhost:8080/mcp/sse}"
HEALTH_URL="${HUB_URL%/mcp/sse}/api/stats"
if curl -sf --max-time 2 "$HEALTH_URL" -o /dev/null; then
  ok "Heliograph reachable ($HEALTH_URL)"
else
  warn "Heliograph not reachable at $HEALTH_URL (start with: ../heliograph)"
fi

echo "▶ Disk"
df -h . | tail -1 | awk '{printf "  used %s / %s (%s)\n", $3, $2, $5}'

echo "▶ HF cache"
HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
[ -d "$HF_HOME" ] && ok "$HF_HOME ($(du -sh "$HF_HOME" 2>/dev/null | cut -f1))" || warn "no HF cache yet"
