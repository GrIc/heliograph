#!/usr/bin/env bash
# Runs the ablation matrix : same benchmarks, varying Heliograph config.
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

CONFIG="${1:-configs/ablation.yaml}"
echo "▶ Ablation matrix, config=$CONFIG"
python -m harness.runner --config "$CONFIG" --mode ablation
