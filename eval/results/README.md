# Results layout

One directory per run, named `<run_name>_YYYYMMDD-HHMMSS/`:

```
<run_dir>/
├── REPORT.md         # human-readable summary
├── metrics.json      # aggregated metrics + config + budget
└── cases/
    └── <bench>/
        └── <case_id>.json   # per-case input/output/score
```

Diff two runs:

```
./scripts/compare.sh results/runA results/runB
```

Run dirs are gitignored by default. To version a meaningful baseline, copy
or symlink it to `results/_baseline` and commit it explicitly.
