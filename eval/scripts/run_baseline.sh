#!/usr/bin/env bash
# Runs eval WITHOUT Heliograph — gives the baseline to compare against.
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

CONFIG="${1:-configs/default.yaml}"
echo "▶ Baseline run (hub disabled), config=$CONFIG"
python -m harness.runner \
  --config "$CONFIG" \
  --override "hub.enabled=false" \
  --override "run_name=baseline-$(date +%Y%m%d-%H%M)"
