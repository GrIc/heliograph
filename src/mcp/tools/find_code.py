"""find_code — semantic code search with filters and mandatory citations."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_store,
    project_search_result_to_source,
)


_ALLOWED_LEVELS = ["L0", "L1", "L2", "L3", "code", "context"]
_ALLOWED_CONTENT = ["code", "codex_doc", "synthesis", "config", "test"]


class FindCode(BaseTool):
    name = "find_code"
    description = (
        "Semantic search over the indexed codebase with optional filters. "
        "Returns ranked snippets with verifiable line-level citations."
    )
    input_schema = {
        "type": "object",
        "required": ["intent"],
        "properties": {
            "intent": {"type": "string", "minLength": 1, "maxLength": 500},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
            "filters": {
                "type": "object",
                "properties": {
                    "module": {"type": "string"},
                    "doc_level": {"type": "string", "enum": _ALLOWED_LEVELS},
                    "content_type": {"type": "string", "enum": _ALLOWED_CONTENT},
                },
                "additionalProperties": False,
            },
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
                        "doc_level": {"type": "string"},
                        "module": {"type": "string"},
                        "source": {
                            "type": "object",
                            "required": ["path", "line_start", "line_end"],
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
            "input": {"intent": "JWT token validation", "top_k": 5},
            "output": {
                "results": [{"snippet": "def verify_jwt(token):...", "score": 0.84,
                              "source": {"path": "src/auth/jwt.py", "line_start": 12, "line_end": 30}}],
                "sources": [{"path": "src/auth/jwt.py", "line_start": 12, "line_end": 30}],
            },
        }
    ]
    requires_citations = True
    rate_limit_per_minute = 120

    def handle(self, args: dict) -> dict:
        store = lazy_store()
        if store is None:
            raise ToolError(
                "internal_error",
                "Vector store unavailable",
                hint="Run `python -m src.main scan` to build the index.",
            )
        intent = args["intent"].strip()
        top_k = int(args.get("top_k", 8))
        filters = args.get("filters") or {}
        doc_levels = [filters["doc_level"]] if filters.get("doc_level") else None
        module = filters.get("module")
        content_type = filters.get("content_type")

        try:
            raw = store.search(
                query=intent,
                top_k=top_k,
                doc_levels=doc_levels,
                module=module,
                content_type=content_type,
            )
        except Exception as e:
            raise ToolError("internal_error", f"search failed: {e}")

        results = []
        sources = []
        for r in raw:
            source = project_search_result_to_source(r)
            if not source["path"]:
                continue
            results.append({
                "snippet": r.get("text", "")[:1000],
                "score": source["score"],
                "doc_level": r.get("doc_level", ""),
                "module": r.get("module", ""),
                "source": source,
            })
            sources.append(source)

        if not results:
            return {
                "results": [],
                "sources": [],
                "notes": f"0 results for intent='{intent}' with filters={filters}",
            }
        return {"results": results, "sources": sources}
