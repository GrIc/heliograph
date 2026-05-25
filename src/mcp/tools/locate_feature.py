"""locate_feature — find ranked file paths where a feature lives."""

from __future__ import annotations

from collections import defaultdict

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_store,
    project_search_result_to_source,
)


class LocateFeature(BaseTool):
    name = "locate_feature"
    description = (
        "Given a feature description in natural language, return ranked file "
        "paths where the feature is implemented, with confidence scores."
    )
    input_schema = {
        "type": "object",
        "required": ["description"],
        "properties": {
            "description": {"type": "string", "minLength": 1, "maxLength": 500},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 15, "default": 5},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["locations", "sources"],
        "properties": {
            "locations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["path", "confidence", "hits"],
                    "properties": {
                        "path": {"type": "string"},
                        "confidence": {"type": "number"},
                        "hits": {"type": "integer"},
                        "best_range": {
                            "type": "object",
                            "additionalProperties": True,
                        },
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
        {
            "input": {"description": "user login flow"},
            "output": {
                "locations": [
                    {"path": "src/auth/login.py", "confidence": 0.92, "hits": 3,
                      "best_range": {"line_start": 10, "line_end": 80}}
                ],
                "sources": [{"path": "src/auth/login.py", "line_start": 10, "line_end": 80}],
            },
        }
    ]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_store()
        if store is None:
            raise ToolError("internal_error", "Vector store unavailable")
        description = args["description"].strip()
        top_k = int(args.get("top_k", 5))

        try:
            raw = store.search(query=description, top_k=top_k * 3)
        except Exception as e:
            raise ToolError("internal_error", f"search failed: {e}")

        per_path: dict[str, dict] = defaultdict(lambda: {"hits": 0, "score_sum": 0.0,
                                                            "best": None, "best_score": -1.0})
        for r in raw:
            path = r.get("source", "")
            if not path:
                continue
            score = float(r.get("score", 0.0))
            entry = per_path[path]
            entry["hits"] += 1
            entry["score_sum"] += score
            if score > entry["best_score"]:
                entry["best_score"] = score
                entry["best"] = project_search_result_to_source(r)

        locations = []
        sources = []
        for path, e in per_path.items():
            confidence = round(min(1.0, e["score_sum"] / max(1, e["hits"])), 4)
            best = e["best"] or {"path": path, "line_start": 1, "line_end": 1}
            locations.append({
                "path": path,
                "confidence": confidence,
                "hits": e["hits"],
                "best_range": best,
            })
            sources.append(best)
        locations.sort(key=lambda x: (-x["confidence"], -x["hits"]))
        locations = locations[:top_k]
        sources = [loc["best_range"] for loc in locations]

        if not locations:
            return {
                "locations": [],
                "sources": [],
                "notes": f"No matches for '{description}'.",
            }
        return {"locations": locations, "sources": sources}
