"""Talk to Heliograph directly via MCP. No LLM agent in the loop.

This adapter is the cheapest, fastest, and most deterministic way to measure
Heliograph's intrinsic tool quality, independent of any agent's behavior.

Status: SCAFFOLD. Wires up MCP SSE endpoint, list_tools, and dispatches based
on case['kind']. Most heavy logic (tool selection per case) is TODO.
"""
from __future__ import annotations
import time
from typing import Any


class RawMCPAdapter:
    def __init__(self, hub_cfg: dict):
        self.cfg = hub_cfg
        self.endpoint = hub_cfg.get("endpoint", "http://localhost:8080/mcp/sse")
        self.enabled = hub_cfg.get("enabled", True)
        self._client = None   # lazy

    def _client_or_none(self):
        if not self.enabled:
            return None
        if self._client is not None:
            return self._client
        try:
            # Lazy import — keeps the rest of the harness usable even if mcp
            # package isn't installed yet.
            from mcp import ClientSession  # noqa: F401
            # TODO: open SSE connection, return wrapper exposing call_tool().
            # For now we return a stub that records calls without performing them.
            self._client = _StubMCPClient(self.endpoint)
        except Exception as e:
            print(f"[raw_mcp] cannot init MCP client: {e}")
            self._client = _StubMCPClient(self.endpoint, error=str(e))
        return self._client

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        kind = case.get("kind", "qa")
        client = self._client_or_none()

        if client is None:
            # Hub disabled => baseline = nothing retrieved, no answer.
            return {
                "answer": "",
                "sources": [],
                "latency_s": 0.0,
                "cost_usd": 0.0,
                "raw": {"adapter": "raw_mcp", "hub_enabled": False},
            }

        # Dispatch — minimal mapping. TODO: refine per benchmark.
        if kind == "qa":
            result = client.call_tool("ask_expert", {"question": case["question"]})
        elif kind == "retrieval":
            result = client.call_tool("find_code", {"query": case["query"]})
        else:
            result = {"answer": "", "sources": [], "_unhandled_kind": kind}

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "latency_s": time.time() - started,
            "cost_usd": 0.0,        # raw MCP doesn't bill direct LLM calls beyond hub-internal
            "raw": {"adapter": "raw_mcp", "tool_result": result},
        }


class _StubMCPClient:
    """Records intent without performing real calls — used while the real
    MCP client wrapper is being implemented. Returns empty results so the
    harness pipeline can run end-to-end."""

    def __init__(self, endpoint: str, error: str | None = None):
        self.endpoint = endpoint
        self.error = error

    def call_tool(self, name: str, args: dict) -> dict:
        return {
            "answer": "",
            "sources": [],
            "_stub": True,
            "_tool": name,
            "_args": args,
            "_error": self.error,
        }
