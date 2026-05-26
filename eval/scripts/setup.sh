#!/usr/bin/env bash
# eval/scripts/setup.sh — one-time setup for the eval harness
# Pulls benchmark datasets, prepares Python env, checks Heliograph reachable.
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EVAL_DIR"

echo "▶ Heliograph eval harness — setup"
echo "  EVAL_DIR=$EVAL_DIR"

# --- 1. Python venv -----------------------------------------------------------
if [ ! -d ".venv" ]; then
  echo "▶ Creating Python venv (.venv)…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel >/dev/null

echo "▶ Installing eval deps (pyproject.toml)…"
pip install -e . >/dev/null

# --- 2. Fixtures dir ----------------------------------------------------------
mkdir -p fixtures/repos
mkdir -p results

# --- 3. Download HF datasets (lazy, cached) ----------------------------------
echo "▶ Pre-fetching benchmark datasets (cached in ~/.cache/huggingface)…"
python - <<'PY'
from datasets import load_dataset
TARGETS = [
    ("princeton-nlp/SWE-bench_Lite", "test"),
    # ("tianyang/repobench-r", "train"),        # uncomment when adapter ready
    # ("code-rag-bench/coderagbench", "test"),  # uncomment when adapter ready
]
for name, split in TARGETS:
    try:
        ds = load_dataset(name, split=split, streaming=True)
        next(iter(ds))   # touch one sample to validate
        print(f"  ✓ {name} ({split}) reachable")
    except Exception as e:
        print(f"  ⚠ {name}: {e}")
PY

# --- 4. Heliograph reachability check ------------------------------------------
echo "▶ Checking Heliograph MCP endpoint…"
HUB_URL="${AGENT_HUB_URL:-http://localhost:8080/mcp/sse}"
if curl -sf --max-time 3 "$HUB_URL" -o /dev/null; then
  echo "  ✓ $HUB_URL reachable"
else
  echo "  ⚠ $HUB_URL not reachable (start with: docker compose up -d)"
fi

echo "✅ Setup done. Next : ./scripts/run_baseline.sh"
