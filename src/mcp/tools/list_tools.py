"""list_tools — return the catalog of registered MCP tools."""

from __future__ import annotations

from src.mcp.base import BaseTool


class ListTools(BaseTool):
    name = "list_tools"
    description = (
        "Return the catalog of all registered MCP tools, including their "
        "names, descriptions, and input schemas. Use this to discover what "
        "Heliograph can do."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "include_schema": {
                "type": "boolean",
                "description": "If true, embed each tool's full JSON Schema.",
                "default": False,
            }
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["tools", "count"],
        "properties": {
            "count": {"type": "integer"},
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "requires_citations": {"type": "boolean"},
                        "auth_required": {"type": "boolean"},
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": False,
    }
    examples = [
        {"input": {}, "output": {"count": 1, "tools": [{"name": "ping", "description": "..."}]}}
    ]
    requires_citations = False
    auth_required = False
    rate_limit_per_minute = 120

    def handle(self, args: dict) -> dict:
        from src.mcp.registry import discover_tools

        include_schema = bool(args.get("include_schema", False))
        registry = discover_tools()
        tools_out: list[dict] = []
        for name in sorted(registry.keys()):
            t = registry[name]
            entry = {
                "name": name,
                "description": getattr(t, "description", ""),
                "requires_citations": bool(getattr(t, "requires_citations", False)),
                "auth_required": bool(getattr(t, "auth_required", False)),
            }
            if include_schema:
                entry["input_schema"] = getattr(t, "input_schema", {})
                entry["output_schema"] = getattr(t, "output_schema", {})
            tools_out.append(entry)
        return {"count": len(tools_out), "tools": tools_out}
