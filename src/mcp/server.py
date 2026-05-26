"""MCP server entry point for Heliograph.

Modular entry point for the Model Context Protocol (MCP) server.  It:

- Loads configuration via :func:`src.config.load_config`.
- Auto‑discovers tools from the ``src.mcp.tools`` package using the
  registry (:func:`src.mcp.registry.discover_tools`).
- Mounts an SSE transport on an existing FastAPI application.
- Supports standalone execution via ``python -m src.mcp.server``.

Structured JSON logging is handled through the ``mcp.server`` logger namespace.

Usage
-----
Standalone (stdio transport)::

    python -m src.mcp.server

Integrated with FastAPI::

    from fastapi import FastAPI
    from src.mcp.server import create_mcp_server, mount_mcp_sse

    cfg = load_config()
    app = FastAPI()
    mount_mcp_sse(app, cfg)

"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from src.config import load_config
from src.mcp.registry import discover_tools

logger = logging.getLogger("mcp.server")

# ---------------------------------------------------------------------------
# Module-level cache to ensure idempotent calls return the same server instance.
# ---------------------------------------------------------------------------
_server_cache: Optional[Any] = None


def _check_mcp_sdk() -> bool:
    """Verify that the ``mcp`` SDK is installed.

    Returns
    -------
    bool
        ``True`` if the SDK is available, ``False`` otherwise.  Logs an
        error message when the SDK is missing.

    """
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        logger.error(
            "MCP SDK not installed. Run: pip install mcp[server] --break-system-packages"
        )
        return False


def create_mcp_server(cfg: dict) -> Any:
    """Create and configure the MCP server instance.

    This function:

    1. Validates that the ``mcp`` SDK is available.
    2. Auto‑discovers all concrete :class:`~src.mcp.base.BaseTool` subclasses
       from the ``src.mcp.tools`` package via
       :func:`src.mcp.registry.discover_tools`.
    3. Registers each discovered tool with the MCP ``Server`` instance,
       mapping tool names to their handler implementations.
    4. Exposes a ``workspace://tree`` resource that returns the workspace
       directory tree.

    Parameters
    ----------
    cfg : dict
        Configuration dictionary produced by :func:`src.config.load_config`.

    Returns
    -------
    mcp.server.Server or None
        The configured MCP ``Server`` instance, or ``None`` if the SDK is
        not available.

    Raises
    ------
    KeyError
        If required configuration keys are missing.

    Examples
    --------
    >>> cfg = load_config()  # doctest: +SKIP
    >>> server = create_mcp_server(cfg)  # doctest: +SKIP
    >>> type(server).__name__  # doctest: +SKIP
    'Server'

    """
    global _server_cache

    if _server_cache is not None:
        logger.debug("Returning cached MCP server instance")
        return _server_cache

    if not _check_mcp_sdk():
        return None

    # Lazy imports to keep this module lightweight when only the registry
    # or other transports are needed.
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool, Resource
        from pydantic import AnyUrl
    except ImportError as exc:
        raise ImportError(
            "MCP server requires the mcp SDK. "
            "Install it with: pip install mcp[server]"
        ) from exc

    # ------------------------------------------------------------------
    # Auto‑discover tools from the registry.
    # ------------------------------------------------------------------
    tool_registry = discover_tools()
    logger.info(
        "Discovered %d tool(s) from registry.", len(tool_registry)
    )

    # ------------------------------------------------------------------
    # Create the MCP Server instance.
    # ------------------------------------------------------------------
    server = Server("heliograph")

    # -- Tool definitions ------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available MCP tools."""
        return [
            Tool(
                name=tool_name,
                description=getattr(tool_instance, "description", ""),
                inputSchema=getattr(tool_instance, "input_schema", {}),
            )
            for tool_name, tool_instance in tool_registry.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Route tool calls through the registry."""
        try:
            if name not in tool_registry:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            tool_instance = tool_registry[name]
            result = await asyncio.to_thread(tool_instance, arguments, context={})
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            logger.exception("Tool '%s' failed", name)
            return [TextContent(type="text", text=f"Error: {e}")]

    # -- Resources -------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available MCP resources."""
        return [
            Resource(
                uri=AnyUrl("workspace://tree"),
                name="Workspace file tree",
                mimeType="text/plain",
                description="Directory tree of the indexed codebase",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: Any) -> str:
        """Read a resource by URI."""
        if str(uri) == "workspace://tree":
            tree_tool = tool_registry.get("workspace_tree")
            if tree_tool is None:
                return "workspace_tree tool not registered"
            result = await asyncio.to_thread(tree_tool, {}, context={})
            return result.get("tree", "") if isinstance(result, dict) else str(result)
        return f"Unknown resource: {uri}"

    _server_cache = server
    logger.info("MCP server created with %d tool(s).", len(tool_registry))
    return _server_cache


def mount_mcp_sse(app: Any, cfg: dict) -> None:
    """Mount the MCP server as an SSE endpoint on an existing FastAPI app.

    This function configures the MCP server and mounts two routes on the
    provided FastAPI application:

    - ``GET /mcp/sse`` — SSE connection endpoint for event streaming.
    - ``POST /mcp/messages`` — JSON‑RPC message endpoint for client requests.

    Parameters
    ----------
    app : fastapi.FastAPI
        The FastAPI application to mount the MCP SSE endpoint on.
    cfg : dict
        Configuration dictionary produced by :func:`src.config.load_config`.

    Raises
    ------
    ImportError
        If FastAPI or the MCP SDK are not installed.

    Examples
    --------
    >>> from fastapi import FastAPI  # doctest: +SKIP
    >>> from src.mcp.server import mount_mcp_sse, load_config  # doctest: +SKIP
    >>> app = FastAPI()  # doctest: +SKIP
    >>> mount_mcp_sse(app, load_config())  # doctest: +SKIP

    """
    if not _check_mcp_sdk():
        logger.warning("MCP SDK not available — IDE integration disabled")
        return

    try:
        from mcp.server.sse import SseServerTransport
        from starlette.routing import Route, Mount
    except ImportError as exc:
        raise ImportError(
            "SSE transport requires starlette. "
            "Install it with: pip install starlette"
        ) from exc

    server = create_mcp_server(cfg)
    if server is None:
        return

    sse_transport = SseServerTransport("/mcp/messages")

    async def handle_sse(request: Any) -> Any:
        """Handle SSE connection from IDE client."""
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )

    async def handle_messages(request: Any) -> Any:
        """Handle JSON-RPC messages from IDE client."""
        return await sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )

    # Mount as sub-application under /mcp.
    app.mount(
        "/mcp",
        Mount(
            "/mcp",
            routes=[
                Route(
                    "/sse",
                    endpoint=handle_sse,
                    methods=["GET"],
                    media_type="text/event-stream",
                ),
                Route(
                    "/messages",
                    endpoint=handle_messages,
                    methods=["POST"],
                ),
            ],
        ),
    )
    logger.info("MCP SSE endpoint mounted at /mcp/sse")


def main() -> None:
    """Run the MCP server standalone with stdio transport.

    This function is useful for development and local IDE testing.  It
    loads configuration, creates the MCP server, and runs it over stdio
    so that any MCP‑compatible client can connect directly.

    Returns
    -------
    None

    Raises
    ------
    SystemExit
        If the MCP SDK is not installed.

    Examples
    --------
    Run the server::

        python -m src.mcp.server

    """
    if not _check_mcp_sdk():
        sys.exit(1)

    from mcp.server.stdio import stdio_server

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )

    cfg = load_config()
    server = create_mcp_server(cfg)
    if server is None:
        sys.exit(1)

    print("Heliograph MCP server starting (stdio transport)...", file=sys.stderr)

    async def run() -> None:
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run())
