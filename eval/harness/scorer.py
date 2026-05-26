"""Metrics. Keep small and explicit — extend when needed."""
from __future__ import annotations
from typing import Any


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    top = set(retrieved_ids[:k])
    hits = sum(1 for e in expected_ids if e in top)
    return hits / len(expected_ids)


def mrr(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    if not expected_ids or not retrieved_ids:
        return 0.0
    expected = set(expected_ids)
    for i, r in enumerate(retrieved_ids, 1):
        if r in expected:
            return 1.0 / i
    return 0.0


def exact_match(answer: str, expected: str) -> float:
    return 1.0 if answer.strip().lower() == expected.strip().lower() else 0.0


def contains_all(answer: str, must_contain: list[str]) -> float:
    a = answer.lower()
    if not must_contain:
        return 1.0
    return sum(1 for m in must_contain if m.lower() in a) / len(must_contain)


def score_case(case: dict[str, Any], output: dict[str, Any]) -> dict[str, float]:
    """Dispatch on case['kind']."""
    kind = case.get("kind", "qa")
    out: dict[str, float] = {}

    if kind == "retrieval":
        retrieved = [s.get("id") or s.get("path") for s in output.get("sources", [])]
        expected = [s.get("id") or s.get("path") for s in case.get("expected_sources", [])]
        out["recall_at_5"] = recall_at_k(retrieved, expected, 5)
        out["recall_at_10"] = recall_at_k(retrieved, expected, 10)
        out["mrr"] = mrr(retrieved, expected)

    elif kind == "qa":
        answer = output.get("answer", "")
        if "expected_answer" in case:
            out["exact_match"] = exact_match(answer, case["expected_answer"])
        if "expected_answer_contains" in case:
            out["contains_score"] = contains_all(answer, case["expected_answer_contains"])

    elif kind == "patch":
        # Task-success benchmarks (SWE-bench style): adapter is expected to
        # set output['tests_passed'] (bool) and 'tests_run' (int).
        out["passed"] = float(bool(output.get("tests_passed")))

    out["latency_s"] = float(output.get("latency_s", 0.0))
    out["cost_usd"] = float(output.get("cost_usd", 0.0))
    return out
