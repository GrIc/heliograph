"""find_similar — vector neighbors for a given reference (file or text)."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    WORKSPACE_PATH,
    lazy_store,
    project_search_result_to_source,
)


class FindSimilar(BaseTool):
    name = "find_similar"
    description = (
        "Find code chunks similar to a given reference. The reference may be a "
        "workspace file path, a class name, or a free-form description."
    )
    input_schema = {
        "type": "object",
        "required": ["reference"],
        "properties": {
            "reference": {"type": "string", "minLength": 1, "maxLength": 1000},
            "kind": {"type": "string", "enum": ["auto", "file", "description"], "default": "auto"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["results", "sources"],
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["snippet", "score", "source"],
                    "properties": {
                        "snippet": {"type": "string"},
                        "score": {"type": "number"},
                        "source": {"type": "object", "additionalProperties": True},
                    },
                    "additionalProperties": True,
                },
            },
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
            "resolved_kind": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"reference": "src/auth/jwt.py"}, "output": {"results": [], "sources": []}}]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_store()
        if store is None:
            raise ToolError("internal_error", "Vector store unavailable")
        reference = args["reference"].strip()
        kind = args.get("kind", "auto")
        top_k = int(args.get("top_k", 8))

        resolved = kind
        query = reference
        if kind == "auto":
            candidate = WORKSPACE_PATH / reference
            if candidate.exists() and candidate.is_file():
                resolved = "file"
                query = candidate.read_text(encoding="utf-8", errors="replace")[:2000]
            else:
                resolved = "description"
        elif kind == "file":
            full = WORKSPACE_PATH / reference
            if not full.exists():
                raise ToolError("not_found", f"File not found: {reference}")
            query = full.read_text(encoding="utf-8", errors="replace")[:2000]

        try:
            raw = store.search(query=query, top_k=top_k + 2)
        except Exception as e:
            raise ToolError("internal_error", f"search failed: {e}")

        results: list[dict] = []
        sources: list[dict] = []
        for r in raw:
            src = project_search_result_to_source(r)
            if not src["path"] or (resolved == "file" and src["path"] == reference):
                continue
            results.append({
                "snippet": r.get("text", "")[:1000],
                "score": src["score"],
                "source": src,
            })
            sources.append(src)
            if len(results) >= top_k:
                break

        if not results:
            return {
                "results": [], "sources": [],
                "resolved_kind": resolved,
                "notes": f"No similar chunks for reference '{reference}'.",
            }
        return {"results": results, "sources": sources, "resolved_kind": resolved}
