"""Reporting: markdown human-readable + JSON machine-readable + diffing."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def write_metrics_json(out_dir: Path, metrics: dict, cfg: dict, budget: dict) -> None:
    payload = {"metrics": metrics, "cfg": cfg, "budget": budget}
    (out_dir / "metrics.json").write_text(json.dumps(payload, indent=2, default=str))


def write_markdown(out_dir: Path, metrics: dict, cfg: dict, budget: dict) -> None:
    lines: list[str] = []
    lines.append(f"# Eval report — {cfg.get('run_name', '')}")
    lines.append("")
    lines.append(f"- adapter: `{cfg.get('agent_adapter')}`")
    lines.append(f"- hub enabled: `{cfg.get('hub', {}).get('enabled')}`")
    lines.append(f"- spent: ${budget.get('spent_usd', 0):.3f}")
    lines.append("")
    for bench, m in metrics.items():
        lines.append(f"## {bench}")
        lines.append("")
        lines.append("| metric | value |")
        lines.append("|--------|-------|")
        for k, v in sorted(m.items()):
            vs = f"{v:.4f}" if isinstance(v, float) else str(v)
            lines.append(f"| {k} | {vs} |")
        lines.append("")
    (out_dir / "REPORT.md").write_text("\n".join(lines))


def compare_runs(a: Path, b: Path) -> str:
    ma = json.loads((a / "metrics.json").read_text())["metrics"]
    mb = json.loads((b / "metrics.json").read_text())["metrics"]
    out = [f"# Comparison — {a.name}  →  {b.name}", ""]
    for bench in sorted(set(ma) | set(mb)):
        out.append(f"## {bench}")
        out.append("| metric | A | B | Δ |")
        out.append("|--------|---|---|---|")
        keys = sorted(set(ma.get(bench, {})) | set(mb.get(bench, {})))
        for k in keys:
            va = ma.get(bench, {}).get(k)
            vb = mb.get(bench, {}).get(k)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                d = vb - va
                arrow = "🟢" if d > 0 else ("🔴" if d < 0 else "·")
                out.append(f"| {k} | {va:.4f} | {vb:.4f} | {d:+.4f} {arrow} |")
            else:
                out.append(f"| {k} | {va} | {vb} | — |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    args = p.parse_args()
    if args.compare:
        md = compare_runs(Path(args.compare[0]), Path(args.compare[1]))
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
