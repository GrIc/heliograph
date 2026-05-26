#!/usr/bin/env bash
# Runs eval WITH Heliograph enabled. Requires `docker compose up -d` first.
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

HUB_URL="${AGENT_HUB_URL:-http://localhost:8080/mcp/sse}"
if ! curl -sf --max-time 3 "$HUB_URL" -o /dev/null; then
  echo "✗ Heliograph not reachable at $HUB_URL" >&2
  echo "  Start it: (cd .. && docker compose up -d)" >&2
  exit 1
fi

CONFIG="${1:-configs/default.yaml}"
echo "▶ With-hub run, config=$CONFIG"
python -m harness.runner \
  --config "$CONFIG" \
  --override "hub.enabled=true" \
  --override "run_name=hub-$(date +%Y%m%d-%H%M)"
