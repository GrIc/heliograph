"""search_graph — entity-relationship search in the knowledge graph."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


class SearchGraph(BaseTool):
    name = "search_graph"
    description = (
        "Search the knowledge graph for an entity by name. Returns the matched "
        "entities, their neighbors within max_hops, and a textual subgraph summary."
    )
    input_schema = {
        "type": "object",
        "required": ["entity"],
        "properties": {
            "entity": {"type": "string", "minLength": 1, "maxLength": 200},
            "max_hops": {"type": "integer", "minimum": 1, "maximum": 4, "default": 2},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["entity", "matches", "sources"],
        "properties": {
            "entity": {"type": "string"},
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["id", "confidence"],
                    "additionalProperties": True,
                },
            },
            "neighbor_count": {"type": "integer"},
            "summary": {"type": "string"},
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"entity": "UserService"}, "output": {"entity": "UserService", "matches": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError("internal_error", "Knowledge graph unavailable",
                            hint="Build with `python build_graph.py` and set graph.enabled.")
        entity = args["entity"].strip()
        max_hops = int(args.get("max_hops", 2))

        matches = graph.find_entities(entity, threshold=0.6)
        if not matches:
            return {
                "entity": entity,
                "matches": [],
                "neighbor_count": 0,
                "summary": "",
                "sources": [],
                "notes": f"No graph entities matched '{entity}'.",
            }

        all_neighbors: dict[str, int] = {}
        for node_id, _ in matches[:3]:
            for nid, hop in graph.get_neighbors(node_id, max_hops=max_hops).items():
                if nid not in all_neighbors or hop < all_neighbors[nid]:
                    all_neighbors[nid] = hop
        summary = graph.get_subgraph_summary(all_neighbors)

        sources: list[dict] = []
        seen: set[str] = set()
        for node_id, _ in matches[:3]:
            collect_node_sources(graph.G.nodes.get(node_id, {}), sources, seen)

        return {
            "entity": entity,
            "matches": [{"id": m[0], "confidence": round(m[1], 4)} for m in matches[:5]],
            "neighbor_count": len(all_neighbors),
            "summary": summary,
            "sources": sources[:20] if sources else [],
            **({"notes": "Matches found but no cited paths exist in workspace."} if not sources else {}),
        }
