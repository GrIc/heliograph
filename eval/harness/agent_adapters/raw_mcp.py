"""Talk to Heliograph directly via its REST IDE routes (which wrap the MCP tools).

This is the cheapest, fastest, most deterministic way to measure Heliograph's
intrinsic tool quality, independent of any agent's behavior.

REST endpoints used :
  POST /api/ide/ask          → ask_expert
  POST /api/ide/search       → find_code
  POST /api/ide/read-file    → read_file
  GET  /api/ide/workspace-tree

For full MCP (SSE) interop, use the GenericMCPAdapter (see _mcp_sse.py — TODO).
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class RawMCPAdapter:
    """Heliograph-specific adapter using the REST IDE shortcuts."""

    def __init__(self, hub_cfg: dict):
        self.cfg = hub_cfg
        # The "endpoint" field historically pointed at /mcp/sse. Derive the
        # REST base from it for convenience.
        sse = hub_cfg.get("endpoint", "http://localhost:8080/mcp/sse")
        self.base_url = sse.replace("/mcp/sse", "").rstrip("/")
        self.enabled = hub_cfg.get("enabled", True)
        self.timeout = float(hub_cfg.get("timeout_s", 60.0))
        self._client: httpx.Client | None = None

    def _http(self) -> httpx.Client | None:
        if not self.enabled:
            return None
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=False,  # internal endpoints may use self-signed certs
            )
        return self._client

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        kind = case.get("kind", "qa")
        http = self._http()

        if http is None:
            # Baseline mode : hub disabled. Empty result = lower bound.
            return {
                "answer": "",
                "sources": [],
                "latency_s": 0.0,
                "cost_usd": 0.0,
                "raw": {"adapter": "raw_mcp", "hub_enabled": False},
            }

        try:
            if kind == "qa":
                question = case.get("question") or case.get("query") or ""
                r = http.post("/api/ide/ask", json={"question": question})
                r.raise_for_status()
                data = r.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
            elif kind == "retrieval":
                query = case.get("query") or case.get("question") or ""
                top_k = int(case.get("top_k", 10))
                r = http.post("/api/ide/search", json={"query": query, "top_k": top_k})
                r.raise_for_status()
                data = r.json()
                # find_code returns 'results' or 'matches' depending on impl; normalize.
                raw_sources = (
                    data.get("sources")
                    or data.get("results")
                    or data.get("matches")
                    or []
                )
                sources = [_normalize_source(s) for s in raw_sources]
                answer = ""
            else:
                return {
                    "answer": "",
                    "sources": [],
                    "latency_s": time.time() - started,
                    "raw": {"adapter": "raw_mcp", "skipped_kind": kind},
                }
            return {
                "answer": answer,
                "sources": sources,
                "latency_s": time.time() - started,
                "cost_usd": 0.0,
                "raw": {"adapter": "raw_mcp", "kind": kind},
            }
        except httpx.HTTPError as e:
            return {
                "answer": "",
                "sources": [],
                "latency_s": time.time() - started,
                "cost_usd": 0.0,
                "raw": {"adapter": "raw_mcp", "error": str(e)},
            }


def _normalize_source(s: Any) -> dict:
    """Best-effort flatten of a source record to {path, line_start, line_end}."""
    if isinstance(s, str):
        return {"path": s}
    if not isinstance(s, dict):
        return {"path": str(s)}
    path = s.get("path") or s.get("source") or s.get("file") or s.get("filepath") or ""
    line_start = s.get("line_start") or s.get("start_line") or s.get("line") or None
    line_end = s.get("line_end") or s.get("end_line") or None
    out = {"path": path}
    if line_start is not None:
        out["line_start"] = line_start
    if line_end is not None:
        out["line_end"] = line_end
    return out
