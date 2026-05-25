"""explain_module — return a synthesized summary of a module."""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_store,
    project_search_result_to_source,
)


class ExplainModule(BaseTool):
    name = "explain_module"
    description = (
        "Return a concise summary of a module pulled from the L1/L2 synthesis "
        "documents, with citations to the source files."
    )
    input_schema = {
        "type": "object",
        "required": ["module_id"],
        "properties": {
            "module_id": {"type": "string", "minLength": 1, "maxLength": 200},
            "max_chars": {"type": "integer", "minimum": 100, "maximum": 4000, "default": 1500},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["summary", "sources"],
        "properties": {
            "summary": {"type": "string"},
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [
        {
            "input": {"module_id": "src/auth"},
            "output": {"summary": "Handles JWT…", "sources": [{"path": "src/auth/__init__.py", "line_start": 1, "line_end": 40}]},
        }
    ]
    requires_citations = True
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        store = lazy_store()
        if store is None:
            raise ToolError("internal_error", "Vector store unavailable")
        module_id = args["module_id"].strip()
        max_chars = int(args.get("max_chars", 1500))

        try:
            raw = store.search(
                query=f"summary of {module_id}",
                top_k=6,
                doc_levels=["L1", "L2"],
                module=module_id,
            )
            if not raw:
                raw = store.search(query=module_id, top_k=6, doc_levels=["L1", "L2"])
            if not raw:
                raw = store.search(query=module_id, top_k=6)
        except Exception as e:
            raise ToolError("internal_error", f"search failed: {e}")

        if not raw:
            return {
                "summary": "[INSUFFICIENT_EVIDENCE]",
                "sources": [],
                "notes": f"No synthesis chunks found for module '{module_id}'.",
            }

        parts: list[str] = []
        sources: list[dict] = []
        used = 0
        for r in raw:
            text = r.get("text", "").strip()
            if not text:
                continue
            slice_len = min(len(text), max_chars - used)
            if slice_len <= 0:
                break
            parts.append(text[:slice_len])
            used += slice_len
            s = project_search_result_to_source(r)
            if s["path"]:
                sources.append(s)
            if used >= max_chars:
                break
        summary = "\n\n".join(parts)[:max_chars]
        return {"summary": summary, "sources": sources[:6]}
