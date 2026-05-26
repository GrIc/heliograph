"""Make sure fixtures parse and have required fields."""
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "agent-hub-internal"


def test_questions_parse():
    f = FIXTURES / "questions.jsonl"
    assert f.exists()
    n = 0
    for line in f.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        case = json.loads(line)
        assert "id" in case
        assert "kind" in case
        assert case["kind"] in {"qa", "retrieval", "patch"}
        n += 1
    assert n >= 5


def test_tasks_parse():
    f = FIXTURES / "tasks.jsonl"
    assert f.exists()
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        assert case["kind"] == "patch"
        assert "problem_statement" in case
