"""Golden tests for MCP tools.

Each tool is asserted on:
  - schema validity (input_schema, output_schema parse as JSON Schema)
  - registry discovery (auto-found by ``discover_tools``)
  - empty-input behavior where applicable (returns ``error`` or stub envelope)
  - citation contract for tools with ``requires_citations`` (when not erroring)

Heavy data-dependent tools (find_code, ask_expert, recent_changes...) are tested
in degraded-mode: with no index / no temporal store, they must emit a clean
``internal_error`` envelope rather than a stack trace.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest

from src.mcp.base import BaseTool
from src.mcp.registry import discover_tools


# ── Common fixtures ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def registry() -> dict[str, BaseTool]:
    return discover_tools()


# ── Discovery + schema sanity ───────────────────────────────────────────


def test_registry_non_empty(registry: dict[str, BaseTool]) -> None:
    assert len(registry) >= 10, "Expected at least 10 tools registered"


def test_all_tools_have_metadata(registry: dict[str, BaseTool]) -> None:
    for name, tool in registry.items():
        assert isinstance(getattr(tool, "name", None), str) and tool.name == name
        assert isinstance(getattr(tool, "description", ""), str)
        assert isinstance(getattr(tool, "input_schema", None), dict), name
        assert isinstance(getattr(tool, "output_schema", None), dict), name


def test_all_schemas_are_valid_jsonschema(registry: dict[str, BaseTool]) -> None:
    for name, tool in registry.items():
        try:
            jsonschema.Draft7Validator.check_schema(tool.input_schema)
            jsonschema.Draft7Validator.check_schema(tool.output_schema)
        except jsonschema.SchemaError as e:
            pytest.fail(f"{name}: invalid schema — {e}")


# ── Per-tool smoke tests ────────────────────────────────────────────────


def _call(tool: BaseTool, args: dict) -> dict:
    return tool(args, context={})


def test_list_tools_runs(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["list_tools"], {})
    assert "tools" in out
    assert out["count"] == len(out["tools"])
    names = {t["name"] for t in out["tools"]}
    assert "ping" in names
    assert "list_tools" in names


def test_ping_runs(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["ping"], {})
    assert out["status"] == "ok"
    assert "uptime_seconds" in out
    assert "subsystems" in out


def test_invalid_input_returns_error(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["find_code"], {"top_k": "not-an-int"})
    assert "error" in out, out
    assert out["error"]["code"] in {"invalid_input"}


def test_invalid_input_required_field(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["explain_module"], {})
    assert "error" in out
    assert out["error"]["code"] == "invalid_input"


def test_stub_tool_returns_not_implemented(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["check_conventions"], {})
    assert "error" in out
    assert out["error"]["code"] == "not_implemented"


# ── Citation contract for tools requiring sources ───────────────────────


def test_tools_requiring_citations_carry_flag(registry: dict[str, BaseTool]) -> None:
    expected = {
        "ask_expert",
        "find_code",
        "locate_feature",
        "explain_module",
        "get_callers",
        "preview_impact",
        "recent_changes",
        "explain_change",
    }
    actual = {n for n, t in registry.items() if getattr(t, "requires_citations", False)}
    assert expected.issubset(actual), expected - actual


def test_find_code_degrades_cleanly(registry: dict[str, BaseTool]) -> None:
    # No index in the test environment — tool must return an error envelope,
    # never raise. Schema or internal_error are both acceptable failure modes.
    out = _call(registry["find_code"], {"intent": "auth", "top_k": 3})
    if "error" in out:
        assert out["error"]["code"] in {"internal_error", "citation_failure"}
    else:
        # If an index happens to exist, ensure the contract holds.
        assert "results" in out
        assert "sources" in out


def test_get_callers_without_graph(registry: dict[str, BaseTool]) -> None:
    out = _call(registry["get_callers"], {"symbol": "nonexistent_symbol_xyz"})
    # Either no graph (internal_error) or graph present but symbol not found
    # (returns matched_entities=[] + sources=[] + notes).
    if "error" in out:
        assert out["error"]["code"] in {"internal_error"}
    else:
        assert "matched_entities" in out
        if out["matched_entities"] == []:
            assert out.get("notes")


# ── Citation middleware: empty sources allowed only with notes ──────────


def test_citation_middleware_allows_empty_with_notes() -> None:
    from src.mcp.middleware.citation import enforce_citations

    assert enforce_citations({"sources": []}) is not None
    assert enforce_citations({"sources": [], "notes": "0 results"}) is None
    assert enforce_citations({"sources": None}) is None
    assert enforce_citations({}) is None


def test_citation_middleware_rejects_fake_path(tmp_path) -> None:
    from src.mcp.middleware.citation import enforce_citations

    os.environ["MCP_WORKSPACE_PATH"] = str(tmp_path)
    try:
        err = enforce_citations({
            "sources": [{"path": "totally/fake.py", "line_start": 1, "line_end": 5}]
        })
        assert err and "does not exist" in err
    finally:
        os.environ.pop("MCP_WORKSPACE_PATH", None)


def test_citation_middleware_validates_range(tmp_path) -> None:
    from src.mcp.middleware.citation import enforce_citations

    f = tmp_path / "real.py"
    f.write_text("\n".join(f"line {i}" for i in range(10)))
    os.environ["MCP_WORKSPACE_PATH"] = str(tmp_path)
    try:
        # invalid range
        err = enforce_citations({
            "sources": [{"path": "real.py", "line_start": 1, "line_end": 50}]
        })
        assert err and "invalid" in err.lower()
        # valid range
        err = enforce_citations({
            "sources": [{"path": "real.py", "line_start": 1, "line_end": 5}]
        })
        assert err is None
    finally:
        os.environ.pop("MCP_WORKSPACE_PATH", None)
