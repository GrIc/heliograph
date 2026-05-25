"""preview_impact — estimate downstream modules impacted by changes."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


class PreviewImpact(BaseTool):
    name = "preview_impact"
    description = (
        "Given a list of changed files or symbols, return weighted estimates "
        "of downstream impact via the knowledge graph."
    )
    input_schema = {
        "type": "object",
        "required": ["changed"],
        "properties": {
            "changed": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
                "maxItems": 50,
            },
            "max_hops": {"type": "integer", "minimum": 1, "maximum": 4, "default": 2},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["impacted", "sources"],
        "properties": {
            "impacted": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "weight", "hops"],
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {"type": "string"},
                        "weight": {"type": "number"},
                        "hops": {"type": "integer"},
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
        {"input": {"changed": ["src/auth/jwt.py"], "max_hops": 2},
         "output": {"impacted": [], "sources": [], "notes": "..."}}
    ]
    requires_citations = True
    rate_limit_per_minute = 30

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError("internal_error", "Knowledge graph unavailable")
        changed = args["changed"]
        max_hops = int(args.get("max_hops", 2))
        limit = int(args.get("limit", 30))

        seed_nodes: list[str] = []
        for item in changed:
            matches = graph.find_entities(item, threshold=0.6)
            for nid, _ in matches[:2]:
                if nid not in seed_nodes:
                    seed_nodes.append(nid)

        if not seed_nodes:
            return {
                "impacted": [],
                "sources": [],
                "notes": f"No graph entities matched any of {len(changed)} changed inputs.",
            }

        impact_map: dict[str, int] = {}
        for seed in seed_nodes:
            neighbors = graph.get_neighbors(seed, max_hops=max_hops)
            for nid, hop in neighbors.items():
                if nid == seed:
                    continue
                impact_map[nid] = min(impact_map.get(nid, hop), hop)

        impacted: list[dict] = []
        sources: list[dict] = []
        seen_paths: set[str] = set()
        ranked = sorted(impact_map.items(), key=lambda x: (x[1], x[0]))[:limit]
        for nid, hop in ranked:
            data = graph.G.nodes.get(nid, {})
            weight = round(1.0 / (1.0 + hop), 4)
            impacted.append({
                "id": nid,
                "label": data.get("label", ""),
                "type": data.get("type", ""),
                "weight": weight,
                "hops": hop,
            })
            collect_node_sources(data, sources, seen_paths, score=weight)

        if not impacted:
            return {
                "impacted": [],
                "sources": [],
                "notes": "Seeds matched but no downstream neighbors within max_hops.",
            }
        return {"impacted": impacted, "sources": sources[:30]}
