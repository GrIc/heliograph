"""recent_changes — list recent enriched commits/changesets."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_temporal,
    make_source,
)


class RecentChanges(BaseTool):
    name = "recent_changes"
    description = (
        "Return recent enriched changes with intent classification, summaries, "
        "and affected modules. Sourced from the temporal store (git commits or "
        "filesystem sync snapshots)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 25},
            "intent": {
                "type": "string",
                "enum": ["feature", "fix", "refactor", "chore", "docs", "test", "unknown"],
            },
            "module": {"type": "string", "maxLength": 200},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["changes", "sources"],
        "properties": {
            "changes": {
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
                        "modules_affected": {"type": "array", "items": {"type": "string"}},
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
    examples = [
        {"input": {"limit": 5},
         "output": {"changes": [], "sources": [], "notes": "..."}}
    ]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_temporal()
        if store is None:
            raise ToolError(
                "internal_error",
                "Temporal store unavailable",
                hint="Run watch.py --changelog-only to populate the store.",
            )
        limit = int(args.get("limit", 25))
        intent = args.get("intent")
        module = args.get("module")

        if intent:
            rows = store.commits_by_intent(intent, limit=limit)
        elif module:
            rows = store.commits_for_module(module, limit=limit)
        else:
            rows = store.enriched_commits(limit=limit)

        if not rows:
            return {
                "changes": [],
                "sources": [],
                "notes": "No enriched changes in temporal store.",
            }

        changes = []
        sources: list[dict] = []
        seen_paths: set[str] = set()
        for row in rows:
            entry = {
                "sha": row.get("sha", ""),
                "author": row.get("author", ""),
                "date": row.get("date", ""),
                "subject": row.get("subject", ""),
                "intent": row.get("intent", ""),
                "summary": row.get("summary", ""),
                "modules_affected": row.get("modules_affected", []) or [],
                "risk_score": float(row.get("risk_score", 0.0) or 0.0),
            }
            changes.append(entry)
            files = row.get("files", []) or []
            for f in files[:3]:
                p = f.get("path") if isinstance(f, dict) else None
                if not p or p in seen_paths:
                    continue
                seen_paths.add(p)
                source = make_source(p)
                if source is not None:
                    sources.append(source)

        if not sources:
            return {
                "changes": changes,
                "sources": [],
                "notes": "Changes returned but no cited paths exist in current workspace.",
            }
        return {"changes": changes, "sources": sources[:30]}
