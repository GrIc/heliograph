#!/usr/bin/env bash
# Runs the ablation matrix : same benchmarks, varying Heliograph config.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run as ./scripts/$(basename "$0") (not 'sh ...')." >&2
  exit 1
fi

set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

CONFIG="${1:-configs/ablation.yaml}"
echo "▶ Ablation matrix, config=$CONFIG"
python -m harness.runner --config "$CONFIG" --mode ablation
