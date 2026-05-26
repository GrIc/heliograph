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


def get_benchmark(name: str):
    from benchmarks import internal, repobench_r, coderagbench, swebench_lite
    return {
        "internal": internal.InternalBenchmark(),
        "repobench_r": repobench_r.RepoBenchR(),
        "coderagbench": coderagbench.CodeRAGBench(),
        "swebench_lite": swebench_lite.SWEBenchLite(),
    }[name]


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
            bench = get_benchmark(name)
        except KeyError:
            CONSOLE.print(f"[yellow]⚠ unknown benchmark {name}, skipping[/]")
            continue
        CONSOLE.print(f"\n[bold]▶ {name}[/]  limit={limit}")
        cases = list(bench.iter_cases(limit=limit))
        results = []
        for i, case in enumerate(cases, 1):
            exhausted, why = budget.exhausted()
            if exhausted:
                CONSOLE.print(f"[red]⛔ budget exhausted: {why}[/]")
                break
            out = adapter.run_case(case)
            scored = score_case(case, out)
            budget.spent_usd += out.get("cost_usd", 0.0)
            (out_dir / "cases" / name).mkdir(parents=True, exist_ok=True)
            with open(out_dir / "cases" / name / f"{case['id']}.json", "w") as fh:
                json.dump({"case": case, "output": out, "scored": scored}, fh, indent=2, default=str)
            results.append(scored)
            if i % 10 == 0:
                CONSOLE.print(f"  ... {i}/{len(cases)}")
        all_metrics[name] = _aggregate(results)
        CONSOLE.print(f"  ✓ {name}: {all_metrics[name]}")

    write_metrics_json(out_dir, all_metrics, cfg=cfg, budget=asdict(budget))
    write_markdown(out_dir, all_metrics, cfg=cfg, budget=asdict(budget))
    CONSOLE.print(f"\n[green]✅ done → {out_dir / 'REPORT.md'}[/]")
    return out_dir


def run_ablation(cfg: dict) -> list[Path]:
    """Run each row of cfg['matrix'] as a separate single run."""
    out_dirs = []
    for row in cfg.get("matrix", []):
        sub_cfg = dict(cfg)
        sub_cfg["hub"] = row.get("hub", {})
        sub_cfg["run_name"] = f"{cfg['run_name']}__{row['name']}"
        out_dirs.append(run_single(sub_cfg))
    # TODO : emit combined matrix report
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
