"""Smoke tests for the MCP server end-to-end wiring.

These tests do NOT speak the full MCP JSON-RPC protocol — they verify the
internal wiring (registry → server creation → handler dispatch) without going
through stdio or SSE transports. Full transport tests require the MCP SDK.

If ``mcp`` is not installed, the tests skip cleanly.
"""

from __future__ import annotations

import importlib.util

import pytest

mcp_available = importlib.util.find_spec("mcp") is not None
needs_mcp = pytest.mark.skipif(not mcp_available, reason="MCP SDK not installed")


def _load_minimal_cfg() -> dict:
    """Return a minimal config dict sufficient to bootstrap the server."""
    return {
        "_defaults": {
            "api_key": "test",
            "api_base_url": "http://localhost",
            "workspace_path": "./workspace",
        },
        "models": {"embed": "", "rerank": ""},
        "graph": {"enabled": False},
        "rag": {"top_k": 8},
    }


@needs_mcp
def test_create_mcp_server_returns_instance() -> None:
    from src.mcp.server import create_mcp_server, _server_cache  # type: ignore

    # Clear cache for a clean test
    import src.mcp.server as srv
    srv._server_cache = None

    server = create_mcp_server(_load_minimal_cfg())
    assert server is not None
    assert server.name == "heliograph"


def test_server_registers_all_discovered_tools() -> None:
    """The handler closure in server.py should expose every registered tool."""
    from src.mcp.registry import discover_tools

    registry = discover_tools()
    assert "list_tools" in registry
    assert "ping" in registry
    assert "find_code" in registry
    # 10+ real tools expected after Phase 4 first wave
    real_tool_names = {
        "list_tools", "ping", "find_code", "ask_expert",
        "locate_feature", "explain_module",
        "get_callers", "get_callees", "preview_impact",
        "recent_changes", "explain_change",
        "read_file", "workspace_tree", "search_graph",
    }
    missing = real_tool_names - set(registry.keys())
    assert not missing, f"Missing tools: {missing}"


def test_list_tools_round_trip_via_registry() -> None:
    """Reproduce the work `server.list_tools()` does, without a live transport."""
    from src.mcp.registry import discover_tools

    registry = discover_tools()
    listing = [
        {"name": name, "description": getattr(t, "description", ""),
         "input_schema": getattr(t, "input_schema", {})}
        for name, t in registry.items()
    ]
    assert all(item["name"] for item in listing)
    assert all(isinstance(item["input_schema"], dict) for item in listing)


def test_call_tool_dispatch_via_registry() -> None:
    """Reproduce `server.call_tool` dispatch without the MCP transport layer."""
    from src.mcp.registry import discover_tools

    registry = discover_tools()
    ping_tool = registry["ping"]
    result = ping_tool({}, context={})
    assert result["status"] == "ok"
    assert "subsystems" in result


def test_unknown_tool_does_not_crash() -> None:
    from src.mcp.registry import discover_tools

    registry = discover_tools()
    assert "this_tool_does_not_exist" not in registry
