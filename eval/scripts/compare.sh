#!/usr/bin/env bash
# Compare two result dirs and emit a markdown delta report.
# Usage: compare.sh [run_a] [run_b]   (defaults: last two runs in results/)
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

if [ $# -ge 2 ]; then
  A="$1"; B="$2"
else
  # last two runs by mtime
  mapfile -t LATEST < <(ls -1dt results/*/ 2>/dev/null | head -n 2)
  if [ "${#LATEST[@]}" -lt 2 ]; then
    echo "Need at least 2 runs in results/ (got ${#LATEST[@]})" >&2
    exit 1
  fi
  B="${LATEST[0]%/}"
  A="${LATEST[1]%/}"
fi

echo "▶ Diff $A  →  $B"
python -m harness.reporter --compare "$A" "$B"
