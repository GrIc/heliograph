"""find_hub_modules — list highly-connected modules in the knowledge graph."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


class FindHubModules(BaseTool):
    name = "find_hub_modules"
    description = (
        "Return modules with the highest combined in/out degree in the "
        "knowledge graph. These are the 'hub' nodes — useful for impact "
        "analysis and high-blast-radius changes."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 15},
            "min_degree": {"type": "integer", "minimum": 1, "default": 3},
            "type_filter": {"type": "string", "description": "Optional node type to filter (e.g. 'Module')."},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["hubs", "sources"],
        "properties": {
            "hubs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "degree"],
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {"type": "string"},
                        "in_degree": {"type": "integer"},
                        "out_degree": {"type": "integer"},
                        "degree": {"type": "integer"},
                    },
                    "additionalProperties": True,
                },
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"limit": 5}, "output": {"hubs": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 30

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError("internal_error", "Knowledge graph unavailable")
        limit = int(args.get("limit", 15))
        min_degree = int(args.get("min_degree", 3))
        type_filter = args.get("type_filter")

        scored: list[tuple[str, int, int]] = []
        for node_id in graph.G.nodes:
            if type_filter and graph.G.nodes[node_id].get("type") != type_filter:
                continue
            in_d = graph.G.in_degree(node_id)
            out_d = graph.G.out_degree(node_id)
            total = in_d + out_d
            if total >= min_degree:
                scored.append((node_id, in_d, out_d))

        scored.sort(key=lambda x: -(x[1] + x[2]))
        scored = scored[:limit]

        hubs: list[dict] = []
        sources: list[dict] = []
        seen_paths: set[str] = set()
        for node_id, in_d, out_d in scored:
            nd = graph.G.nodes.get(node_id, {})
            hubs.append({
                "id": node_id,
                "label": nd.get("label", ""),
                "type": nd.get("type", ""),
                "in_degree": in_d,
                "out_degree": out_d,
                "degree": in_d + out_d,
            })
            collect_node_sources(nd, sources, seen_paths)

        if not hubs:
            return {
                "hubs": [],
                "sources": [],
                "notes": f"No nodes with degree >= {min_degree}.",
            }
        return {"hubs": hubs, "sources": sources[:30]}
