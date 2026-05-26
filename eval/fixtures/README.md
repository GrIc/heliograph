# Fixtures

## `agent-hub-internal/`

Hand-curated Q/A on **this repo**. Used by the `internal` benchmark.
Cheap to run, deterministic, dogfood.

Two files:

- `questions.jsonl` — one Q/A per line, kind=`qa` or `retrieval`.
- `tasks.jsonl` — multi-step coding tasks, kind=`patch`.

Add new entries freely. Schema is documented at the top of each file.

## `repos/`

Cloned lazily by `scripts/setup.sh`. Gitignored. Used by benchmarks that
need a checked-out repo (SWE-bench cases, RepoBench).
