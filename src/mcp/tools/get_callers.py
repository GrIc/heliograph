"""get_callers — who calls this symbol?"""

from __future__ import annotations

from pathlib import Path

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


class GetCallers(BaseTool):
    name = "get_callers"
    description = (
        "Return the set of modules/functions that call (or depend on) a given "
        "symbol. Backed by the knowledge graph."
    )
    input_schema = {
        "type": "object",
        "required": ["symbol"],
        "properties": {
            "symbol": {"type": "string", "minLength": 1, "maxLength": 200},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["matched_entities", "callers", "sources"],
        "properties": {
            "matched_entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "confidence"],
                    "properties": {
                        "id": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "additionalProperties": True,
                },
            },
            "callers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "type"],
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {"type": "string"},
                        "relation": {"type": "string"},
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
        {"input": {"symbol": "verify_jwt"}, "output": {"matched_entities": [], "callers": [], "sources": [], "notes": "..."}}
    ]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError(
                "internal_error",
                "Knowledge graph unavailable",
                hint="Build it: `python build_graph.py`, ensure graph.enabled=true.",
            )
        symbol = args["symbol"].strip()
        limit = int(args.get("limit", 25))

        matches = graph.find_entities(symbol, threshold=0.7)
        if not matches:
            return {
                "matched_entities": [],
                "callers": [],
                "sources": [],
                "notes": f"No entity matches for symbol '{symbol}'.",
            }

        matched_entities = [
            {"id": m[0], "confidence": round(m[1], 4)} for m in matches[:3]
        ]
        callers: list[dict] = []
        sources: list[dict] = []
        seen_callers: set[str] = set()
        seen_paths: set[str] = set()

        for node_id, _ in matches[:3]:
            for u, _v, data in graph.G.in_edges(node_id, data=True):
                if u in seen_callers:
                    continue
                seen_callers.add(u)
                node_data = graph.G.nodes.get(u, {})
                callers.append({
                    "id": u,
                    "label": node_data.get("label", ""),
                    "type": node_data.get("type", ""),
                    "relation": data.get("relation", ""),
                })
                collect_node_sources(node_data, sources, seen_paths)
                if len(callers) >= limit:
                    break
            if len(callers) >= limit:
                break

        if not callers:
            return {
                "matched_entities": matched_entities,
                "callers": [],
                "sources": [],
                "notes": f"Symbol '{symbol}' matched but no incoming edges (no callers found).",
            }

        return {
            "matched_entities": matched_entities,
            "callers": callers,
            "sources": sources[:20],
        }
