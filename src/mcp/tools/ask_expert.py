"""ask_expert — RAG-powered code Q&A with mandatory citations."""

from __future__ import annotations

import logging

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import (
    SOURCES_LIST_SCHEMA,
    lazy_config,
    lazy_store,
    project_search_result_to_source,
)

logger = logging.getLogger("mcp.tools.ask_expert")


class AskExpert(BaseTool):
    name = "ask_expert"
    description = (
        "Ask a free-form question about the codebase. Returns a grounded answer "
        "with citations to source files. Use for architecture, debugging, and "
        "review questions."
    )
    input_schema = {
        "type": "object",
        "required": ["question"],
        "properties": {
            "question": {"type": "string", "minLength": 1, "maxLength": 2000},
            "scope": {
                "type": "string",
                "description": "Optional scope filter (module path or topic).",
                "maxLength": 200,
            },
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["answer", "sources"],
        "properties": {
            "answer": {"type": "string"},
            "sources": SOURCES_LIST_SCHEMA,
            "notes": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [
        {
            "input": {"question": "How is authentication handled?"},
            "output": {
                "answer": "JWT validation in src/auth/jwt.py:verify_jwt…",
                "sources": [{"path": "src/auth/jwt.py", "line_start": 12, "line_end": 60}],
            },
        }
    ]
    requires_citations = True
    rate_limit_per_minute = 30

    _expert_cache = None

    def _get_expert(self):
        if AskExpert._expert_cache is not None:
            return AskExpert._expert_cache
        try:
            from src.agents.base import BaseAgent
            from src.config import (
                build_custom_dsl_context,
                build_domain_context,
                get_agent_extra_params,
                get_agent_temperature,
                get_model_for_agent,
            )
            from src.mcp.tools._common import _Singletons

            cfg = lazy_config()

            class ExpertMCP(BaseAgent):
                name = "expert"

            AskExpert._expert_cache = ExpertMCP(
                client=_Singletons.client(),
                store=lazy_store(),
                model=get_model_for_agent(cfg, "expert"),
                temperature=get_agent_temperature(cfg, "expert"),
                rag_top_k=cfg.get("rag", {}).get("top_k", 8),
                custom_dsl_info=build_custom_dsl_context(cfg),
                domain_info=build_domain_context(cfg),
                extra_params=get_agent_extra_params(cfg, "expert"),
            )
            return AskExpert._expert_cache
        except Exception as e:
            logger.exception("failed to init expert agent")
            raise ToolError("internal_error", f"expert init failed: {e}")

    def handle(self, args: dict) -> dict:
        question = args["question"].strip()
        scope = args.get("scope", "").strip()
        store = lazy_store()
        if store is None:
            raise ToolError(
                "internal_error",
                "Vector store unavailable",
                hint="Build the index with `python -m src.main scan`.",
            )

        query = f"{scope}: {question}" if scope else question
        try:
            raw = store.search(query=query, top_k=8)
        except Exception as e:
            raise ToolError("internal_error", f"retrieval failed: {e}")

        sources: list[dict] = []
        for r in raw:
            s = project_search_result_to_source(r)
            if s["path"]:
                sources.append(s)
        sources = sources[:8]

        if not sources:
            return {
                "answer": "[INSUFFICIENT_EVIDENCE]",
                "sources": [],
                "notes": "No relevant chunks found in the index. The question may be out of scope.",
            }

        try:
            expert = self._get_expert()
            answer = expert.chat(question)
        except ToolError:
            raise
        except Exception as e:
            logger.exception("expert.chat failed")
            raise ToolError("internal_error", f"expert.chat failed: {e}")

        return {"answer": answer, "sources": sources}
