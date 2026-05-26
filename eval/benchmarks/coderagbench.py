"""CodeRAG-Bench adapter.

Public HF dataset for RAG-specific code Q&A. Used here to compare MCP
context providers head-to-head (same agent stub, different MCP server).

Reference: https://huggingface.co/datasets/code-rag-bench/coderagbench

Each example becomes a 'qa' case. The canonical answer (if present) is
distilled into a small keyword set for cheap contains-scoring; the listed
reference documents (if any) seed retrieval-quality scoring.
"""
from __future__ import annotations

from typing import Any, Iterable

HF_DATASET = "code-rag-bench/coderagbench"
DEFAULT_TASK = "humaneval"   # smallest, fastest sanity baseline
DEFAULT_SPLIT = "test"


class CodeRAGBench:
    name = "coderagbench"

    def __init__(self, task: str = DEFAULT_TASK, split: str = DEFAULT_SPLIT):
        self.task = task
        self.split = split

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]:
        try:
            from datasets import load_dataset
        except ImportError:
            print(f"[{self.name}] datasets package not installed; pip install datasets")
            return
        try:
            ds = load_dataset(HF_DATASET, self.task, split=self.split, streaming=True)
        except Exception as exc:
            try:
                ds = load_dataset(HF_DATASET, split=self.split, streaming=True)
            except Exception as exc2:
                print(f"[{self.name}] cannot load {HF_DATASET}: {exc} ; {exc2}")
                return

        for i, ex in enumerate(ds):
            if limit and i >= limit:
                return
            yield self._to_case(i, ex)

    @staticmethod
    def _to_case(i: int, ex: dict) -> dict[str, Any]:
        question = (
            ex.get("prompt")
            or ex.get("question")
            or ex.get("intent")
            or ex.get("text", "")
        )
        gold = ex.get("canonical_solution") or ex.get("answer") or ex.get("solution") or ""
        refs = ex.get("references") or ex.get("context") or ex.get("docs") or []
        expected_sources = []
        if isinstance(refs, list):
            for r in refs:
                if isinstance(r, str):
                    expected_sources.append({"path": r})
                elif isinstance(r, dict):
                    p = r.get("path") or r.get("url") or r.get("id")
                    if p:
                        expected_sources.append({"path": str(p)})
        return {
            "id": ex.get("task_id") or f"coderagbench-{i:06d}",
            "kind": "qa",
            "question": question,
            "expected_answer_contains": _keywords(gold),
            "expected_sources": expected_sources,
            "_raw": ex,
        }


def _keywords(text: str) -> list[str]:
    """Pick a few distinctive identifiers from a gold answer for cheap
    contains-scoring. Free-form prose remains unconstrained."""
    if not text:
        return []
    import re
    stopwords = {
        "return", "import", "from", "self", "None", "True", "False",
        "class", "if", "else", "elif", "def", "with", "while", "for",
        "this", "that", "then", "than", "into", "have", "will", "been",
    }
    toks = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", text)
    out, seen = [], set()
    for t in toks:
        if t in stopwords or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= 5:
            break
    return out
