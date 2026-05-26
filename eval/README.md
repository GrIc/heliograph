# Heliograph — Eval Harness

Measure **what Heliograph actually does** for a coding agent, with public
benchmarks and reproducible commands.

---

## What you can measure

| Question | Benchmark | Adapter | Time | Cost |
|---|---|---|---|---|
| « Does Heliograph retrieve the right code for *my* repo ? » | `internal` (your fixtures) | `raw_mcp` | seconds | $0 |
| « Does Heliograph compete on standard RAG tasks ? » | `coderagbench` | `raw_mcp` | 5–30 min | $0–$1 |
| « Does Heliograph improve real GitHub-issue resolution ? » | `swebench_lite` | `raw_mcp` → swebench official harness | 1–6 h | $5–$50 |
| « Does swap of MCP server / model / embedder move the needle ? » | matrix mode | any | depends | depends |

All benchmarks are **public Hugging Face datasets** ; nothing private,
nothing proprietary, results comparable to other tools.

---

## Step 0 — prerequisites (once)

```bash
# Heliograph itself must be running with an indexed codebase :
cd ..
./heliograph status         # check it's up
curl -s http://localhost:${WEB_PORT:-8080}/api/stats | python -m json.tool
# Expect "chunks" > 0. If not : docker exec heliograph-web python -m src.main --ingest
```

If you haven't built the index, **stop here** and follow
[`docs/install.md`](../docs/install.md) §6 first. The eval is meaningless
on an empty index.

```bash
cd eval
./scripts/setup.sh          # creates .venv, installs deps, prefetches HF datasets
./scripts/doctor.sh         # python OK, deps OK, MCP reachable
```

---

## Step 1 — first signal in 60 seconds (`internal` benchmark)

Hand-curated Q/A on the Heliograph repo itself (or your own — see
"Custom fixtures" below). No network, no LLM judge, just retrieval
scoring.

```bash
# Baseline : Heliograph OFF (empty results = lower bound)
./scripts/run_baseline.sh configs/default.yaml

# With Heliograph
./scripts/run_with_hub.sh configs/default.yaml

# Side-by-side delta
./scripts/compare.sh
```

Output : `results/<run>/REPORT.md` and a diff table on stdout, e.g.

```
## internal
| metric             | baseline | hub    | Δ        |
| recall_at_5_mean   | 0.000    | 0.620  | +0.620 🟢|
| mrr_mean           | 0.000    | 0.481  | +0.481 🟢|
| contains_score_mean| 0.144    | 0.733  | +0.589 🟢|
```

If `hub` is not strictly above `baseline` on `recall_at_5_mean`, your
Heliograph install is wrong (index empty, wrong workspace, etc.).

---

## Step 2 — public benchmark : CodeRAG-Bench

Standard RAG-for-code benchmark, ~1000 examples, comparable across MCP
servers.

```bash
cat > configs/coderag.yaml <<'EOF'
run_name: coderag
agent_adapter: raw_mcp
hub: { enabled: true, endpoint: "http://localhost:8080/mcp/sse" }
benchmarks:
  - name: coderagbench
    enabled: true
    limit: 100         # bump to 1000+ for full run
budget: { max_cost_usd: 2, max_wall_seconds: 1800 }
EOF

./scripts/run_with_hub.sh configs/coderag.yaml
```

Same with `hub.enabled: false` for the baseline. `compare.sh` to diff.

---

## Step 3 — head-to-head matrix (multiple providers / models)

Run N configurations against the same benchmarks, get one combined
`MATRIX_REPORT.md`.

```bash
./scripts/run_ablation.sh configs/compare.yaml
```

Edit `configs/compare.yaml` to add rows. Examples :

```yaml
matrix:
  - name: baseline-no-hub
    hub: { enabled: false }

  - name: heliograph
    hub: { enabled: true, endpoint: "http://localhost:8080/mcp/sse" }

  - name: continue-dev          # another MCP server running on :8090
    hub: { enabled: true, endpoint: "http://localhost:8090/mcp/sse" }

  - name: heliograph-other-embed
    hub: { enabled: true, endpoint: "http://localhost:8080/mcp/sse" }
    # (you must restart Heliograph with the alternative embed model — this
    #  field is advisory, the harness doesn't reconfigure Heliograph for you)
```

Output : `results/compare_<ts>/MATRIX_REPORT.md` with all rows side-by-side.

---

## Step 4 — SWE-bench Lite (the gold standard)

300 real GitHub issues with hidden tests. Uses the **official `swebench`
package** for evaluation, so your numbers are directly comparable to the
public leaderboard.

> ⚠️ Requires Docker (swebench builds one container per repo to apply +
> test patches). Plan for hours and a non-trivial LLM bill.

### 4a. Produce predictions

```bash
cat > configs/swebench.yaml <<'EOF'
run_name: swebench
agent_adapter: raw_mcp          # swap to 'aider' or 'claude_code' to actually produce patches
hub: { enabled: true, endpoint: "http://localhost:8080/mcp/sse" }
benchmarks:
  - name: swebench_lite
    enabled: true
    limit: 10                    # start small ; remove for full 300
budget: { max_cost_usd: 5, max_wall_seconds: 3600 }
EOF

./scripts/run_with_hub.sh configs/swebench.yaml
# → results/swebench-<ts>/predictions.jsonl + instance_ids.txt
```

> Note : `raw_mcp` only gathers context — it does **not** synthesize a
> real patch. For meaningful SWE-bench numbers, use the `aider` or
> `claude_code` adapter (stubs today, see `harness/agent_adapters/`).
> The pipeline still works end-to-end with `raw_mcp`, you just get 0%
> solved as expected.

### 4b. Run the official harness

```bash
./scripts/run_swebench.sh results/swebench-<ts>
# → results/swebench-<ts>/SWEBENCH_SUMMARY.md
# → results/swebench-<ts>/swebench-report/report.json
```

Output : `% resolved` over the run, plus the list of resolved instance
IDs. Comparable to <https://swebench.com> leaderboard.

---

## Configs cheat sheet

| File | Purpose |
|---|---|
| `configs/default.yaml` | Moderate single-run config (internal + light repobench) |
| `configs/ci-quick.yaml` | ~5 min, used by CI on every PR |
| `configs/nightly.yaml` | All benchmarks, longer budget |
| `configs/ablation.yaml` | Model / embed / rerank ablation matrix |
| `configs/compare.yaml` | Head-to-head matrix (drop-in for swapping MCP servers) |
| `configs/coderag.yaml` (you create) | CodeRAG-Bench focused |
| `configs/swebench.yaml` (you create) | SWE-bench Lite focused |

---

## Custom fixtures (your own repo)

Default `internal` benchmark targets the Heliograph repo itself. To
evaluate on **your** codebase, write 10–30 ground-truth Q/A :

```bash
mkdir -p fixtures/my-pilot
cat > fixtures/my-pilot/questions.jsonl <<'EOF'
{"id": "p-001", "kind": "qa", "question": "Where is authentication handled?", "expected_answer_contains": ["auth", "login"]}
{"id": "p-002", "kind": "retrieval", "query": "user session creation", "expected_sources": [{"path": "src/auth/session.py"}]}
EOF

# Register it (add to harness/runner.py → get_benchmark()) :
#   "my-pilot": MyPilot(),
# Then create benchmarks/my_pilot.py mirroring benchmarks/internal.py.
```

Then point a config at it :

```yaml
benchmarks:
  - { name: my-pilot, enabled: true }
```

---

## What each adapter does

| Adapter | Calls MCP ? | Calls LLM ? | Produces patches ? | Cost | Use for |
|---|---|---|---|---|---|
| `raw_mcp` | yes (REST `/api/ide/*`) | no | no | $0 | retrieval quality, response grounding |
| `aider` (stub) | yes | yes (via aider) | yes (real diff) | $$ | SWE-bench, real-world tasks |
| `claude_code` (stub) | yes | yes (via claude headless) | yes | $$$ | SOTA reference |

To switch : set `agent_adapter:` in the config.

---

## Reading the reports

Each run creates :

```
results/<run-name>_<timestamp>/
├── REPORT.md              ← human summary (open this first)
├── metrics.json           ← aggregated metrics + cfg + budget
├── cases/<bench>/<id>.json ← per-case raw : case, output, score
├── predictions.jsonl      ← SWE-bench style predictions (if applicable)
└── instance_ids.txt       ← (idem)
```

Matrix runs add `MATRIX_REPORT.md` at the top.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `recall_at_5_mean = 0` even with hub | empty index | `docker exec heliograph-web python -m src.main --ingest` |
| `cannot load HF dataset` | offline / proxy | `huggingface-cli login` ; check `HF_HUB_OFFLINE` |
| SWE-bench harness crashes | Docker not available | `docker info` must succeed |
| `swebench package not installed` | optional dep | `pip install "swebench>=2.0"` (auto on first `run_swebench.sh`) |
| Heliograph returns empty sources | endpoint mismatch | `curl http://localhost:8080/api/stats` ; check `WEB_PORT` in `.env` |
| All metrics zero | adapter not wired | check `agent_adapter:` in your config matches a real adapter |

---

## Cost / time table

| Run | Wall time | LLM cost (OpenAI) | Local GPU |
|---|---|---|---|
| `internal` x 13 | < 1 min | $0 | $0 |
| `coderagbench` x 100 | 5–15 min | $0.05–$0.50 | optional |
| `coderagbench` x 1000 | 1–3 h | $1–$5 | optional |
| `swebench_lite` x 10 | 10–30 min | $1–$3 | $0 |
| `swebench_lite` x 300 (full) | 4–8 h | $20–$100 | $0 |
| `compare.yaml` (default 2 rows) | 5–15 min | $0.10–$1 | optional |

Cap with `budget.max_cost_usd` in any config to avoid surprises.

---

## See also

- [`../docs/install.md`](../docs/install.md) — install + index preheat
- [`../docs/usage.md`](../docs/usage.md) — daily commands + MCP tool list
- [`../docs/architecture.md`](../docs/architecture.md) — how Heliograph works
