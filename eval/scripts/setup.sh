#!/usr/bin/env bash
# eval/scripts/setup.sh — one-time setup for the eval harness
# Pulls benchmark datasets, prepares Python env, checks Heliograph reachable.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "This script requires bash. Run as ./scripts/$(basename "$0") (not 'sh ...')." >&2
  exit 1
fi

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
# Disable multiprocess to dodge the Python 3.12 + multiprocess RLock shutdown
# warning. Sequential is fine here, we only fetch a single sample per dataset.
export HF_DATASETS_DISABLE_MULTIPROCESSING=1
python - <<'PY'
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from datasets import load_dataset
TARGETS = [
    ("princeton-nlp/SWE-bench_Lite", "test"),
    # Uncomment when the adapter is exercised in CI :
    # ("tianyang/repobench-r", "train"),
    # ("code-rag-bench/coderagbench", "test"),
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
HUB_URL="${HELIOGRAPH_URL:-http://localhost:8080/mcp/sse}"
HEALTH_URL="${HUB_URL%/mcp/sse}/api/stats"
if curl -sf --max-time 2 "$HEALTH_URL" -o /dev/null; then
  echo "  ✓ Heliograph reachable (${HEALTH_URL})"
else
  echo "  ⚠ Heliograph not reachable at $HEALTH_URL (run: ../heliograph)"
fi

echo "✅ Setup done. Next : ./scripts/run_baseline.sh"
