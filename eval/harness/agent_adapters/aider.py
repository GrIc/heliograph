"""Aider headless adapter.

Aider is open-source, scriptable, MCP-compatible. Drives it in a temporary
git worktree per case, captures the proposed patch, applies it, runs tests.

Status: SCAFFOLD. Subprocess plumbing + worktree management is sketched but
not yet wired. Fill in when SWE-bench-style runs are needed.
"""
from __future__ import annotations
import time
from typing import Any


class AiderAdapter:
    def __init__(self, hub_cfg: dict):
        self.hub_cfg = hub_cfg
        # TODO: detect `aider` binary on PATH, fail loud if missing.

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        # TODO:
        # 1. git worktree add for the repo at case['base_commit']
        # 2. write task prompt to a temp file
        # 3. subprocess.run(["aider", "--yes", "--message-file", prompt,
        #                    "--mcp-server", self.hub_cfg['endpoint'], ...])
        # 4. capture diff via `git diff`
        # 5. apply diff in a fresh checkout, run case['test_command']
        return {
            "answer": "",
            "patch": "",
            "tests_passed": False,
            "tests_run": 0,
            "latency_s": time.time() - started,
            "cost_usd": 0.0,
            "raw": {"adapter": "aider", "status": "TODO"},
        }
