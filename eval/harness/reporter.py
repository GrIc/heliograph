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


def write_matrix_report(out_dir: Path, rows: list[dict]) -> None:
    """Build a side-by-side table comparing N matrix runs.

    rows: [{"name": "<row name>", "dir": "<absolute path to run dir>"}, ...]
    Reads each run's metrics.json and emits MATRIX_REPORT.md.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {}
    for row in rows:
        try:
            payload = json.loads((Path(row["dir"]) / "metrics.json").read_text())
            data[row["name"]] = payload["metrics"]
        except Exception as exc:
            data[row["name"]] = {"_error": str(exc)}

    # Collect (bench, metric) pairs across all rows.
    pairs: set[tuple[str, str]] = set()
    for metrics in data.values():
        for bench, m in metrics.items():
            if isinstance(m, dict):
                for k in m:
                    if isinstance(m[k], (int, float)):
                        pairs.add((bench, k))

    row_names = [r["name"] for r in rows]
    lines = [f"# Matrix report — {len(rows)} runs", ""]
    for bench in sorted({b for b, _ in pairs}):
        lines.append(f"## {bench}")
        lines.append("")
        hdr = "| metric | " + " | ".join(row_names) + " |"
        sep = "|--------|" + "|".join(["---"] * len(row_names)) + "|"
        lines.append(hdr)
        lines.append(sep)
        for metric in sorted({m for b, m in pairs if b == bench}):
            cells = []
            for name in row_names:
                v = data.get(name, {}).get(bench, {}).get(metric)
                cells.append(f"{v:.4f}" if isinstance(v, float) else (str(v) if v is not None else "—"))
            lines.append(f"| {metric} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("")
    lines.append("Per-row dirs:")
    for r in rows:
        lines.append(f"- **{r['name']}** → `{r['dir']}`")
    (out_dir / "MATRIX_REPORT.md").write_text("\n".join(lines))


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
