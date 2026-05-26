#!/usr/bin/env bash
# Run the OFFICIAL swebench harness against predictions produced by our runner.
#
# Workflow:
#   1. Our harness produces eval/results/<run>/predictions.jsonl
#      (one line per SWE-bench instance: {instance_id, model_patch, model_name_or_path})
#   2. This script feeds them to the official `swebench` package, which
#      builds per-repo containers, applies patches, runs hidden tests, and
#      emits a report.jsonl with pass/fail per instance.
#   3. We parse report.jsonl into a markdown summary alongside our run.
#
# Usage:
#   ./scripts/run_swebench.sh results/<run_dir>
#
# Requires Docker (the swebench harness builds per-repo containers).
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run as ./scripts/$(basename "$0") (not 'sh ...')." >&2
  exit 1
fi

set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

RUN_DIR="${1:-}"
if [ -z "$RUN_DIR" ] || [ ! -d "$RUN_DIR" ]; then
  echo "Usage: $0 <run_dir>"; exit 1
fi

PREDS="$RUN_DIR/predictions.jsonl"
if [ ! -f "$PREDS" ]; then
  echo "✗ no predictions.jsonl in $RUN_DIR"
  echo "  produce one with: ./scripts/run_with_hub.sh configs/swebench.yaml"
  exit 1
fi

# Ensure swebench is installed (optional dep).
python -c "import swebench" 2>/dev/null || {
  echo "▶ Installing official swebench harness…"
  pip install "swebench>=2.0"
}

echo "▶ Running official swebench harness on $PREDS"
python -m swebench.harness.run_evaluation \
  --predictions_path "$PREDS" \
  --max_workers 4 \
  --run_id "heliograph-$(basename "$RUN_DIR")" \
  --instance_ids_path "$RUN_DIR/instance_ids.txt" \
  --report_dir "$RUN_DIR/swebench-report"

REPORT="$RUN_DIR/swebench-report"
if [ -f "$REPORT/report.json" ]; then
  python - "$REPORT/report.json" "$RUN_DIR/SWEBENCH_SUMMARY.md" <<'PY'
import json, sys
src, out = sys.argv[1], sys.argv[2]
data = json.load(open(src))
resolved = data.get("resolved", []) if isinstance(data, dict) else []
unresolved = data.get("unresolved", []) if isinstance(data, dict) else []
total = len(resolved) + len(unresolved) or 1
pct = 100 * len(resolved) / total
md = [
  f"# SWE-bench summary",
  "",
  f"- resolved : **{len(resolved)} / {total}**  ({pct:.1f}%)",
  f"- unresolved : {len(unresolved)}",
  "",
  "Resolved instance IDs:",
  *[f"- {iid}" for iid in resolved[:20]],
  ("..." if len(resolved) > 20 else ""),
]
open(out, "w").write("\n".join(md))
print(f"→ {out}")
PY
fi
