"""why_does_this_exist — walk back to the commit introducing a symbol."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_temporal,
    make_source,
)


class WhyDoesThisExist(BaseTool):
    name = "why_does_this_exist"
    description = (
        "Return the oldest enriched commit that touched a file matching the "
        "given path, with its summary — typically the commit that introduced it."
    )
    input_schema = {
        "type": "object",
        "required": ["filepath"],
        "properties": {
            "filepath": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["filepath", "sources"],
        "properties": {
            "filepath": {"type": "string"},
            "introducing_commit": {
                "type": "object",
                "additionalProperties": True,
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"filepath": "src/main.py"}, "output": {"filepath": "src/main.py", "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_temporal()
        if store is None:
            raise ToolError("internal_error", "Temporal store unavailable")
        filepath = args["filepath"].strip()

        cursor = store.connection.execute(
            """
            SELECT * FROM commits
            WHERE files_json LIKE ?
            ORDER BY date ASC
            LIMIT 1
            """,
            (f'%"{filepath}"%',),
        )
        row = cursor.fetchone()
        if not row:
            return {
                "filepath": filepath,
                "sources": [],
                "notes": f"No commits in store touched '{filepath}'.",
            }
        r = store._row_to_dict(row)
        commit = {
            "sha": r.get("sha", ""),
            "author": r.get("author", ""),
            "date": r.get("date", ""),
            "subject": r.get("subject", ""),
            "intent": r.get("intent", ""),
            "summary": r.get("summary", ""),
            "risk_score": float(r.get("risk_score", 0.0) or 0.0),
        }

        source = make_source(filepath)
        if source is not None:
            return {"filepath": filepath, "introducing_commit": commit, "sources": [source]}
        return {
            "filepath": filepath,
            "introducing_commit": commit,
            "sources": [],
            "notes": f"Commit found but '{filepath}' missing from current workspace.",
        }
