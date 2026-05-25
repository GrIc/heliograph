"""what_changed_here — commit timeline for a given file."""

from __future__ import annotations

import json

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_temporal,
    make_source,
)


class WhatChangedHere(BaseTool):
    name = "what_changed_here"
    description = (
        "Return the timeline of enriched commits that touched a specific file, "
        "newest first."
    )
    input_schema = {
        "type": "object",
        "required": ["filepath"],
        "properties": {
            "filepath": {"type": "string", "minLength": 1, "maxLength": 500},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["filepath", "history", "sources"],
        "properties": {
            "filepath": {"type": "string"},
            "history": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["sha", "subject"],
                    "properties": {
                        "sha": {"type": "string"},
                        "author": {"type": "string"},
                        "date": {"type": "string"},
                        "subject": {"type": "string"},
                        "intent": {"type": "string"},
                        "summary": {"type": "string"},
                        "risk_score": {"type": "number"},
                    },
                    "additionalProperties": True,
                },
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"filepath": "src/main.py"},
                  "output": {"filepath": "src/main.py", "history": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_temporal()
        if store is None:
            raise ToolError("internal_error", "Temporal store unavailable")
        filepath = args["filepath"].strip()
        limit = int(args.get("limit", 25))

        # filter via files_json containing the path
        cursor = store.connection.execute(
            """
            SELECT * FROM commits
            WHERE files_json LIKE ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (f'%"{filepath}"%', limit),
        )
        rows = [store._row_to_dict(r) for r in cursor.fetchall()]
        if not rows:
            return {
                "filepath": filepath,
                "history": [],
                "sources": [],
                "notes": f"No commits in store touched '{filepath}'.",
            }

        history = [{
            "sha": r.get("sha", ""),
            "author": r.get("author", ""),
            "date": r.get("date", ""),
            "subject": r.get("subject", ""),
            "intent": r.get("intent", ""),
            "summary": r.get("summary", ""),
            "risk_score": float(r.get("risk_score", 0.0) or 0.0),
        } for r in rows]

        source = make_source(filepath)
        if source is not None:
            return {"filepath": filepath, "history": history, "sources": [source]}
        return {
            "filepath": filepath,
            "history": history,
            "sources": [],
            "notes": f"History found but '{filepath}' does not exist in current workspace.",
        }
