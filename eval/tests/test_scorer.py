"""Sanity tests for the scoring functions."""
from harness.scorer import recall_at_k, mrr, exact_match, contains_all, score_case


def test_recall_at_k_basic():
    assert recall_at_k(["a", "b", "c"], ["a"], 1) == 1.0
    assert recall_at_k(["a", "b", "c"], ["b"], 1) == 0.0
    assert recall_at_k(["a", "b", "c"], ["b"], 2) == 1.0
    assert recall_at_k(["a", "b", "c"], ["a", "x"], 5) == 0.5


def test_mrr_basic():
    assert mrr(["a", "b", "c"], ["a"]) == 1.0
    assert mrr(["a", "b", "c"], ["b"]) == 0.5
    assert mrr(["a", "b", "c"], ["c"]) == 1 / 3
    assert mrr(["a", "b", "c"], ["z"]) == 0.0


def test_exact_match():
    assert exact_match("Yes", "yes") == 1.0
    assert exact_match("no", "yes") == 0.0


def test_contains_all():
    assert contains_all("foo bar baz", ["foo", "baz"]) == 1.0
    assert contains_all("foo bar", ["foo", "qux"]) == 0.5
    assert contains_all("anything", []) == 1.0


def test_score_case_qa_contains():
    case = {"kind": "qa", "expected_answer_contains": ["alpha", "beta"]}
    out = {"answer": "alpha and beta found here", "latency_s": 0.1}
    s = score_case(case, out)
    assert s["contains_score"] == 1.0
    assert s["latency_s"] == 0.1


def test_score_case_retrieval():
    case = {"kind": "retrieval",
            "expected_sources": [{"path": "src/a.py"}, {"path": "src/b.py"}]}
    out = {"sources": [{"path": "src/a.py"}, {"path": "src/x.py"}, {"path": "src/b.py"}]}
    s = score_case(case, out)
    assert s["recall_at_5"] == 1.0
    assert 0 < s["mrr"] <= 1.0
