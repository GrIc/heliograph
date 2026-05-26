"""Eval runner — loops over benchmarks × cases × adapters and collects metrics.

Status: SCAFFOLD. The orchestration shell is real (config loading, output
layout, budget enforcement, basic scoring). Adapter and benchmark
implementations are stubs that print TODOs — they're meant to be filled in
incrementally so each addition can be tested end-to-end.

Usage:
    python -m harness.runner --config configs/default.yaml
    python -m harness.runner --config configs/default.yaml --override hub.enabled=false
    python -m harness.runner --config configs/ablation.yaml --mode ablation
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from harness.scorer import score_case
from harness.reporter import write_markdown, write_metrics_json

CONSOLE = Console()
EVAL_ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = EVAL_ROOT / "results"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _apply_override(cfg: dict, dotted: str) -> None:
    """`hub.enabled=false` → cfg['hub']['enabled'] = False (typed)."""
    key, _, raw = dotted.partition("=")
    parts = key.split(".")
    cur = cfg
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    val: Any = raw
    if raw.lower() in {"true", "false"}:
        val = raw.lower() == "true"
    elif raw.isdigit():
        val = int(raw)
    else:
        try:
            val = float(raw)
        except ValueError:
            pass
    cur[parts[-1]] = val


def load_config(path: Path, overrides: list[str]) -> dict:
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    for ovr in overrides:
        _apply_override(cfg, ovr)
    return cfg


# ---------------------------------------------------------------------------
# Adapters & benchmark registries
# ---------------------------------------------------------------------------

def get_adapter(name: str, hub_cfg: dict):
    if name == "raw_mcp":
        from harness.agent_adapters.raw_mcp import RawMCPAdapter
        return RawMCPAdapter(hub_cfg)
    if name == "aider":
        from harness.agent_adapters.aider import AiderAdapter
        return AiderAdapter(hub_cfg)
    if name == "claude_code":
        from harness.agent_adapters.claude_code import ClaudeCodeAdapter
        return ClaudeCodeAdapter(hub_cfg)
    raise ValueError(f"Unknown adapter: {name}")


def get_benchmark(name: str, opts: dict | None = None):
    """Instantiate a benchmark by name, optionally forwarding kwargs from the
    YAML config (e.g. `dataset`, `split`, `task`).

    Soft-routing: if `name` looks like an HF id ('code-rag-bench/…'), it's
    treated as a CodeRAG-Bench dataset and the harness pretends the user
    typed `name: coderagbench` + `dataset: <that id>`. Avoids a common
    config mix-up.
    """
    from benchmarks import internal, repobench_r, coderagbench, swebench_lite
    opts = dict(opts or {})

    # Soft-route HF-style ids into the right benchmark class.
    if name.startswith("code-rag-bench/"):
        opts.setdefault("dataset", name)
        name = "coderagbench"
    elif name.startswith("princeton-nlp/SWE-bench"):
        name = "swebench_lite"
    elif name.startswith("tianyang/repobench"):
        name = "repobench_r"

    if name == "internal":
        return internal.InternalBenchmark()
    if name == "repobench_r":
        return repobench_r.RepoBenchR()
    if name == "coderagbench":
        return coderagbench.CodeRAGBench(
            dataset=opts.get("dataset", coderagbench.DEFAULT_DATASET),
            split=opts.get("split", coderagbench.DEFAULT_SPLIT),
        )
    if name == "swebench_lite":
        return swebench_lite.SWEBenchLite()
    raise KeyError(name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fs_safe(s: str) -> str:
    """Make a string safe to use as a single path segment.

    Replaces path separators and other troublesome chars with '_'. Keeps the
    result readable so reports can still be eyeballed.
    """
    bad = '/\\:*?"<>|\0'
    out = []
    for ch in s:
        out.append("_" if ch in bad else ch)
    return "".join(out).strip(" ._") or "x"


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------

@dataclass
class RunBudget:
    max_cost_usd: float = 1e9
    max_wall_seconds: float = 1e9
    started_at: float = field(default_factory=time.time)
    spent_usd: float = 0.0

    def exhausted(self) -> tuple[bool, str]:
        if self.spent_usd >= self.max_cost_usd:
            return True, f"cost cap reached ({self.spent_usd:.2f} >= {self.max_cost_usd})"
        elapsed = time.time() - self.started_at
        if elapsed >= self.max_wall_seconds:
            return True, f"wall-time cap reached ({elapsed:.0f}s)"
        return False, ""


def run_single(cfg: dict) -> Path:
    """Run one config (not an ablation matrix)."""
    run_name = cfg.get("run_name", "run") + "_" + time.strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS_ROOT / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    CONSOLE.rule(f"[bold cyan]{run_name}")
    CONSOLE.print(f"  → output: {out_dir}")

    adapter = get_adapter(cfg["agent_adapter"], cfg.get("hub", {}))
    budget = RunBudget(
        max_cost_usd=cfg.get("budget", {}).get("max_cost_usd", 1e9),
        max_wall_seconds=cfg.get("budget", {}).get("max_wall_seconds", 1e9),
    )

    all_metrics: dict[str, dict] = {}
    for bench_cfg in cfg.get("benchmarks", []):
        if not bench_cfg.get("enabled", True):
            continue
        name = bench_cfg["name"]
        limit = bench_cfg.get("limit")
        try:
            bench = get_benchmark(name, opts=bench_cfg)
        except KeyError:
            CONSOLE.print(
                f"[red]✗ unknown benchmark '{name}'.[/] "
                f"Valid names: internal, repobench_r, coderagbench, swebench_lite. "
                f"For CodeRAG-Bench tasks pass them as : "
                f"\n    name: coderagbench\n    dataset: code-rag-bench/humaneval"
            )
            raise SystemExit(2)
        CONSOLE.print(f"\n[bold]▶ {name}[/]  limit={limit}")
        cases = list(bench.iter_cases(limit=limit))
        results = []
        # Streamed SWE-bench artifacts (when applicable).
        swe_preds = open(out_dir / "predictions.jsonl", "a") if name.startswith("swebench") else None
        swe_ids = open(out_dir / "instance_ids.txt", "a") if name.startswith("swebench") else None
        # Sanitize bench name + case ids for filesystem use (HF ids contain '/').
        safe_bench = _fs_safe(name)
        cases_dir = out_dir / "cases" / safe_bench
        cases_dir.mkdir(parents=True, exist_ok=True)
        for i, case in enumerate(cases, 1):
            exhausted, why = budget.exhausted()
            if exhausted:
                CONSOLE.print(f"[red]⛔ budget exhausted: {why}[/]")
                break
            out = adapter.run_case(case)
            scored = score_case(case, out)
            budget.spent_usd += out.get("cost_usd", 0.0)
            safe_id = _fs_safe(str(case["id"]))
            with open(cases_dir / f"{safe_id}.json", "w") as fh:
                json.dump({"case": case, "output": out, "scored": scored}, fh, indent=2, default=str)
            if swe_preds is not None:
                swe_preds.write(json.dumps({
                    "instance_id": case["id"],
                    "model_name_or_path": cfg.get("agent_adapter", "raw_mcp"),
                    "model_patch": out.get("patch", ""),
                }) + "\n")
                swe_ids.write(case["id"] + "\n")
            results.append(scored)
            if i % 10 == 0:
                CONSOLE.print(f"  ... {i}/{len(cases)}")
        if swe_preds is not None:
            swe_preds.close()
            swe_ids.close()
            CONSOLE.print(f"  → predictions.jsonl + instance_ids.txt written")
            CONSOLE.print(f"    next: ./scripts/run_swebench.sh {out_dir}")
        all_metrics[name] = _aggregate(results)
        CONSOLE.print(f"  ✓ {name}: {all_metrics[name]}")

    write_metrics_json(out_dir, all_metrics, cfg=cfg, budget=asdict(budget))
    write_markdown(out_dir, all_metrics, cfg=cfg, budget=asdict(budget))
    CONSOLE.print(f"\n[green]✅ done → {out_dir / 'REPORT.md'}[/]")
    return out_dir


def run_ablation(cfg: dict) -> list[Path]:
    """Run each row of cfg['matrix'] as a separate single run.

    Each matrix row may override : hub, agent_adapter, models, benchmarks.
    Produces a combined MATRIX_REPORT.md side-by-side comparing all rows.
    """
    out_dirs = []
    rows_meta = []
    matrix_dir = RESULTS_ROOT / (cfg.get("run_name", "matrix") + "_" + time.strftime("%Y%m%d-%H%M%S"))
    matrix_dir.mkdir(parents=True, exist_ok=True)

    for row in cfg.get("matrix", []):
        sub_cfg = dict(cfg)
        # Apply row overrides — shallow merge per top-level key.
        for k, v in row.items():
            if k == "name":
                continue
            sub_cfg[k] = v
        sub_cfg["run_name"] = f"{cfg.get('run_name', 'matrix')}__{row['name']}"
        out = run_single(sub_cfg)
        out_dirs.append(out)
        rows_meta.append({"name": row["name"], "dir": str(out)})

    # Emit combined matrix report.
    from harness.reporter import write_matrix_report
    write_matrix_report(matrix_dir, rows_meta)
    CONSOLE.print(f"\n[green]✅ matrix → {matrix_dir / 'MATRIX_REPORT.md'}[/]")
    return out_dirs


def _aggregate(scored: list[dict]) -> dict:
    if not scored:
        return {"n": 0}
    n = len(scored)
    keys = {k for s in scored for k in s.keys() if isinstance(s[k], (int, float))}
    agg = {"n": n}
    for k in keys:
        vals = [s[k] for s in scored if isinstance(s.get(k), (int, float))]
        if vals:
            agg[f"{k}_mean"] = sum(vals) / len(vals)
    return agg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--override", action="append", default=[],
                   help="Dotted key=val, repeatable")
    p.add_argument("--mode", choices=["single", "ablation"], default="single")
    args = p.parse_args()

    cfg = load_config(args.config, args.override)
    if args.mode == "ablation":
        run_ablation(cfg)
    else:
        run_single(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
