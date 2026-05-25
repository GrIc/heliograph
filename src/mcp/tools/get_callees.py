"""get_callees — what does this symbol call?"""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


class GetCallees(BaseTool):
    name = "get_callees"
    description = (
        "Return the set of modules/functions that the given symbol calls "
        "(outgoing edges in the knowledge graph)."
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
        "required": ["matched_entities", "callees", "sources"],
        "properties": {
            "matched_entities": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "callees": {
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
    examples = [{"input": {"symbol": "main"}, "output": {"matched_entities": [], "callees": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError("internal_error", "Knowledge graph unavailable")
        symbol = args["symbol"].strip()
        limit = int(args.get("limit", 25))

        matches = graph.find_entities(symbol, threshold=0.7)
        if not matches:
            return {
                "matched_entities": [],
                "callees": [],
                "sources": [],
                "notes": f"No entity matches for symbol '{symbol}'.",
            }

        matched = [{"id": m[0], "confidence": round(m[1], 4)} for m in matches[:3]]
        callees: list[dict] = []
        sources: list[dict] = []
        seen_nodes: set[str] = set()
        seen_paths: set[str] = set()

        for node_id, _ in matches[:3]:
            for _u, v, data in graph.G.out_edges(node_id, data=True):
                if v in seen_nodes:
                    continue
                seen_nodes.add(v)
                nd = graph.G.nodes.get(v, {})
                callees.append({
                    "id": v,
                    "label": nd.get("label", ""),
                    "type": nd.get("type", ""),
                    "relation": data.get("relation", ""),
                })
                collect_node_sources(nd, sources, seen_paths)
                if len(callees) >= limit:
                    break
            if len(callees) >= limit:
                break

        if not callees:
            return {
                "matched_entities": matched,
                "callees": [],
                "sources": [],
                "notes": f"Symbol '{symbol}' matched but no outgoing edges.",
            }
        return {"matched_entities": matched, "callees": callees, "sources": sources[:20]}
