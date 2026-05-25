"""get_module_dependencies — inbound / outbound dependencies of a module."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    collect_node_sources,
    lazy_graph,
)


_DIRECTIONS = ["in", "out", "both"]


class GetModuleDependencies(BaseTool):
    name = "get_module_dependencies"
    description = (
        "Return the inbound, outbound, or both sets of dependencies for a "
        "module-level entity in the knowledge graph."
    )
    input_schema = {
        "type": "object",
        "required": ["module"],
        "properties": {
            "module": {"type": "string", "minLength": 1, "maxLength": 200},
            "direction": {"type": "string", "enum": _DIRECTIONS, "default": "both"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["module", "matches", "inbound", "outbound", "sources"],
        "properties": {
            "module": {"type": "string"},
            "matches": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "inbound": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "outbound": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"module": "src/auth"}, "output": {"module": "src/auth", "matches": [], "inbound": [], "outbound": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        graph = lazy_graph()
        if graph is None:
            raise ToolError("internal_error", "Knowledge graph unavailable")
        module = args["module"].strip()
        direction = args.get("direction", "both")
        limit = int(args.get("limit", 50))

        matches = graph.find_entities(module, threshold=0.6)
        if not matches:
            return {
                "module": module,
                "matches": [],
                "inbound": [],
                "outbound": [],
                "sources": [],
                "notes": f"No graph entities matched module '{module}'.",
            }

        inbound: list[dict] = []
        outbound: list[dict] = []
        sources: list[dict] = []
        seen_paths: set[str] = set()
        seen_in: set[str] = set()
        seen_out: set[str] = set()

        for node_id, _ in matches[:3]:
            if direction in {"in", "both"}:
                for u, _v, data in graph.G.in_edges(node_id, data=True):
                    if u in seen_in:
                        continue
                    seen_in.add(u)
                    nd = graph.G.nodes.get(u, {})
                    inbound.append({
                        "id": u, "label": nd.get("label", ""),
                        "type": nd.get("type", ""), "relation": data.get("relation", ""),
                    })
                    collect_node_sources(nd, sources, seen_paths)
                    if len(inbound) >= limit:
                        break
            if direction in {"out", "both"}:
                for _u, v, data in graph.G.out_edges(node_id, data=True):
                    if v in seen_out:
                        continue
                    seen_out.add(v)
                    nd = graph.G.nodes.get(v, {})
                    outbound.append({
                        "id": v, "label": nd.get("label", ""),
                        "type": nd.get("type", ""), "relation": data.get("relation", ""),
                    })
                    collect_node_sources(nd, sources, seen_paths)
                    if len(outbound) >= limit:
                        break

        if not inbound and not outbound:
            return {
                "module": module,
                "matches": [{"id": m[0], "confidence": round(m[1], 4)} for m in matches[:3]],
                "inbound": [], "outbound": [], "sources": [],
                "notes": f"Module '{module}' matched but no edges in direction '{direction}'.",
            }

        return {
            "module": module,
            "matches": [{"id": m[0], "confidence": round(m[1], 4)} for m in matches[:3]],
            "inbound": inbound,
            "outbound": outbound,
            "sources": sources[:30],
        }


