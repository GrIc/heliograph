#!/usr/bin/env bash
# Runs eval WITH Heliograph enabled. Requires `docker compose up -d` first.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run as ./scripts/$(basename "$0") (not 'sh ...')." >&2
  exit 1
fi

set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

HUB_URL="${HELIOGRAPH_URL:-http://localhost:8080/mcp/sse}"
# Reach the same host:port via REST stats (200 OK is decisive; SSE endpoint
# is a stream and would hang curl). Wait up to 30s for container healthcheck.
HEALTH_URL="${HUB_URL%/mcp/sse}/api/stats"
for i in $(seq 1 30); do
  if curl -sf --max-time 2 "$HEALTH_URL" -o /dev/null; then
    break
  fi
  if [ "$i" = 1 ]; then
    echo "▶ Waiting for Heliograph at $HEALTH_URL …"
  fi
  sleep 1
done
if ! curl -sf --max-time 2 "$HEALTH_URL" -o /dev/null; then
  echo "✗ Heliograph not reachable at $HEALTH_URL (after 30s)" >&2
  echo "  Start it: (cd .. && ./heliograph)" >&2
  exit 1
fi

CONFIG="${1:-configs/default.yaml}"
echo "▶ With-hub run, config=$CONFIG"
python -m harness.runner \
  --config "$CONFIG" \
  --override "hub.enabled=true" \
  --override "run_name=hub-$(date +%Y%m%d-%H%M)"
