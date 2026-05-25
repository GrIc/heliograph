"""IDE REST routes — thin proxy over the MCP tool registry.

These endpoints expose a small subset of MCP tools as plain JSON HTTP routes,
useful for IDE extensions (VS Code, IntelliJ) that don't speak MCP directly.

Endpoint format: each route accepts the MCP tool's input schema as JSON body
and returns the tool's response verbatim (with the same error envelope).

The MCP server at ``/mcp/sse`` remains the preferred path; this is a fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.mcp.registry import discover_tools

logger = logging.getLogger(__name__)


def register_ide_routes(app: Any, cfg: dict) -> None:
    """Register ``/api/ide/*`` routes on the FastAPI app.

    Each route invokes a registered MCP tool. Configuration is unused here
    (kept for backwards compatibility with the legacy bridge signature).
    """
    del cfg  # not needed; registry is config-driven
    registry = discover_tools()

    async def _call(tool_name: str, payload: dict) -> Any:
        tool = registry.get(tool_name)
        if tool is None:
            return JSONResponse(
                {"error": {"code": "not_found", "message": f"tool '{tool_name}' not registered"}},
                status_code=404,
            )
        result = tool(payload, context={})
        if isinstance(result, dict) and "error" in result:
            return JSONResponse(result, status_code=400)
        return result

    @app.post("/api/ide/ask")
    async def ide_ask(request: Request):
        body = await request.json()
        question = (body.get("question") or "").strip()
        if not question:
            return JSONResponse({"error": "question required"}, status_code=400)
        return await _call("ask_expert", {"question": question})

    @app.post("/api/ide/search")
    async def ide_search(request: Request):
        body = await request.json()
        query = (body.get("query") or "").strip()
        top_k = int(body.get("top_k", 8))
        if not query:
            return JSONResponse({"error": "query required"}, status_code=400)
        return await _call("find_code", {"intent": query, "top_k": top_k})

    @app.post("/api/ide/read-file")
    async def ide_read_file(request: Request):
        body = await request.json()
        filepath = (body.get("filepath") or "").strip()
        if not filepath:
            return JSONResponse({"error": "filepath required"}, status_code=400)
        return await _call("read_file", {"filepath": filepath})

    @app.get("/api/ide/workspace-tree")
    async def ide_workspace_tree(max_depth: int = 3):
        return await _call("workspace_tree", {"max_depth": max_depth})

    logger.info("IDE REST routes registered at /api/ide/* (%d tools wired)", len(registry))
