"""Claude Code headless adapter.

Uses `claude -p "<prompt>" --output-format json` with an MCP config pointing
at Agent Hub. Captures the JSON output, extracts the proposed patch and the
tool calls made.

Status: SCAFFOLD.
"""
from __future__ import annotations
import time
from typing import Any


class ClaudeCodeAdapter:
    def __init__(self, hub_cfg: dict):
        self.hub_cfg = hub_cfg
        # TODO: detect `claude` binary, set up an mcp config file pointing at
        # self.hub_cfg['endpoint'] when enabled.

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        # TODO:
        # 1. spawn claude -p "<prompt>" --output-format json (--mcp-config ...)
        # 2. parse the streamed JSON for final assistant message + tool uses
        # 3. for patch-cases, apply and run tests
        return {
            "answer": "",
            "patch": "",
            "tests_passed": False,
            "tests_run": 0,
            "latency_s": time.time() - started,
            "cost_usd": 0.0,
            "raw": {"adapter": "claude_code", "status": "TODO"},
        }
