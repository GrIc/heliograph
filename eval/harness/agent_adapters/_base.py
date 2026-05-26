"""Adapter base class."""
from __future__ import annotations
from typing import Any, Protocol


class AgentAdapter(Protocol):
    """Run a single benchmark case and return a structured output.

    Output schema (all fields optional unless noted by score_case):
      {
        "answer":       str,           # for qa cases
        "sources":      [{path, line_start, line_end, id?}, ...],
        "patch":        str,           # for patch cases (unified diff)
        "tests_passed": bool,
        "tests_run":    int,
        "latency_s":    float,
        "cost_usd":     float,
        "tokens_in":    int,
        "tokens_out":   int,
        "raw":          dict,          # adapter-specific debug
      }
    """

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]: ...
