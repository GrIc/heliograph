"""explain_change — narrative summary of a single commit/changeset."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_temporal,
    make_source,
)


class ExplainChange(BaseTool):
    name = "explain_change"
    description = (
        "Return the enriched summary of a single change identified by SHA "
        "(git) or fs-<timestamp> (filesystem sync)."
    )
    input_schema = {
        "type": "object",
        "required": ["change_id"],
        "properties": {
            "change_id": {"type": "string", "minLength": 4, "maxLength": 200},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["change", "sources"],
        "properties": {
            "change": {
                "type": "object",
                "required": ["sha", "subject"],
                "additionalProperties": True,
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [
        {"input": {"change_id": "abc1234"}, "output": {"change": {"sha": "abc1234", "subject": "..."}, "sources": []}}
    ]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_temporal()
        if store is None:
            raise ToolError("internal_error", "Temporal store unavailable")
        change_id = args["change_id"].strip()

        row = store.get_commit(change_id)
        if row is None:
            raise ToolError(
                "not_found",
                f"No change found for id '{change_id}'",
                hint="Use recent_changes to list known SHAs.",
            )

        change = {
            "sha": row.get("sha", ""),
            "author": row.get("author", ""),
            "date": row.get("date", ""),
            "subject": row.get("subject", ""),
            "body": row.get("body", ""),
            "intent": row.get("intent", ""),
            "summary": row.get("summary", ""),
            "modules_affected": row.get("modules_affected", []) or [],
            "risk_score": float(row.get("risk_score", 0.0) or 0.0),
            "files": row.get("files", []) or [],
        }

        sources: list[dict] = []
        seen_paths: set[str] = set()
        for f in change["files"]:
            p = f.get("path") if isinstance(f, dict) else None
            if not p or p in seen_paths:
                continue
            seen_paths.add(p)
            source = make_source(p)
            if source is not None:
                sources.append(source)

        if not sources:
            return {
                "change": change,
                "sources": [],
                "notes": f"Change {change_id} found but no current workspace files match its file list.",
            }
        return {"change": change, "sources": sources[:30]}
