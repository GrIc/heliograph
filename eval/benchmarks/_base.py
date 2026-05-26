"""Benchmark interface.

A benchmark yields `case` dicts. A `case` has at minimum:
  - id (str)              unique
  - kind (str)            one of: qa | retrieval | patch
  - everything else is kind-specific (question, expected_*, base_commit, ...)
"""
from __future__ import annotations
from typing import Any, Iterable, Protocol


class Benchmark(Protocol):
    name: str

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]: ...
