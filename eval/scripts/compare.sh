#!/usr/bin/env bash
# Compare two result dirs and emit a markdown delta report.
# Usage:
#   ./scripts/compare.sh                # last two runs in results/
#   ./scripts/compare.sh runA runB      # explicit pair
#
# IMPORTANT: run with bash (./scripts/compare.sh), not 'sh'. We use bash
# features (process substitution, mapfile).
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run it as: ./scripts/compare.sh (or bash ./scripts/compare.sh)" >&2
  exit 1
fi
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

if [ $# -ge 2 ]; then
  A="$1"; B="$2"
else
  # last two runs by mtime, portable (no mapfile)
  RUNS=$(ls -1dt results/*/ 2>/dev/null | head -n 2)
  count=$(printf '%s\n' "$RUNS" | sed '/^$/d' | wc -l)
  if [ "$count" -lt 2 ]; then
    echo "Need at least 2 runs in results/ (got $count)" >&2
    exit 1
  fi
  B=$(printf '%s\n' "$RUNS" | sed -n '1p')
  A=$(printf '%s\n' "$RUNS" | sed -n '2p')
  B="${B%/}"
  A="${A%/}"
fi

echo "▶ Diff $A  →  $B"
python -m harness.reporter --compare "$A" "$B"
