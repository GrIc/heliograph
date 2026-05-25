"""blame_plus — git blame enriched with the commit's semantic summary."""

from __future__ import annotations

import subprocess

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    WORKSPACE_PATH,
    clamp_line_range,
    lazy_temporal,
)


class BlamePlus(BaseTool):
    name = "blame_plus"
    description = (
        "Run git blame on a specific line and enrich the result with the "
        "corresponding commit's enriched summary (intent, risk, modules)."
    )
    input_schema = {
        "type": "object",
        "required": ["filepath", "line"],
        "properties": {
            "filepath": {"type": "string", "minLength": 1, "maxLength": 500},
            "line": {"type": "integer", "minimum": 1},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["filepath", "line", "sources"],
        "properties": {
            "filepath": {"type": "string"},
            "line": {"type": "integer"},
            "blame": {
                "type": "object",
                "additionalProperties": True,
            },
            "enriched": {
                "type": "object",
                "additionalProperties": True,
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"filepath": "src/main.py", "line": 1},
                  "output": {"filepath": "src/main.py", "line": 1, "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        filepath = args["filepath"].strip()
        line = int(args["line"])
        full = WORKSPACE_PATH / filepath
        if not full.exists():
            raise ToolError("not_found", f"File not found: {filepath}")

        try:
            output = subprocess.check_output(
                ["git", "blame", "-L", f"{line},{line}", "--porcelain", filepath],
                cwd=WORKSPACE_PATH,
                stderr=subprocess.STDOUT,
                timeout=10,
            ).decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise ToolError("internal_error", f"git blame failed: {e}",
                            hint="Workspace must be a git repo for blame_plus.")

        blame = _parse_porcelain_blame(output)
        if not blame.get("sha"):
            return {
                "filepath": filepath, "line": line,
                "sources": [],
                "notes": "git blame returned no SHA.",
            }

        enriched: dict = {}
        store = lazy_temporal()
        if store is not None:
            row = store.get_commit(blame["sha"])
            if row:
                enriched = {
                    "intent": row.get("intent", ""),
                    "summary": row.get("summary", ""),
                    "modules_affected": row.get("modules_affected", []) or [],
                    "risk_score": float(row.get("risk_score", 0.0) or 0.0),
                }

        ls, le = clamp_line_range(max(1, line - 5), line + 5, full)
        sources = [{"path": filepath, "line_start": ls, "line_end": le, "score": 1.0}]
        result = {"filepath": filepath, "line": line, "blame": blame, "sources": sources}
        if enriched:
            result["enriched"] = enriched
        else:
            result["notes"] = "Blame SHA not in temporal store (run watch.py --changelog-only)."
        return result


def _parse_porcelain_blame(text: str) -> dict:
    out: dict = {}
    for raw in text.splitlines():
        if not raw:
            continue
        parts = raw.split(" ", 1)
        head = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if not out and len(head) == 40:
            out["sha"] = head
            continue
        if head == "author":
            out["author"] = rest
        elif head == "author-time":
            out["author_time"] = rest
        elif head == "summary":
            out["summary"] = rest
    return out
