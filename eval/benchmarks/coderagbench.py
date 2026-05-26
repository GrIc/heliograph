"""CodeRAG-Bench adapter.

CodeRAG-Bench is published as a *family* of HF datasets, one per task:
  code-rag-bench/humaneval, code-rag-bench/mbpp, code-rag-bench/ds1000,
  code-rag-bench/odex, code-rag-bench/programming-solutions, …

There is NO umbrella dataset called 'code-rag-bench/coderagbench' on the
Hub. Pick a task by its HF id when configuring the benchmark :

  benchmarks:
    - name: coderagbench
      dataset: code-rag-bench/humaneval   # smallest, fastest sanity baseline
      split: test
      limit: 50

Default = humaneval (164 cases, free, takes a couple minutes).

Reference : https://huggingface.co/code-rag-bench
"""
from __future__ import annotations

from typing import Any, Iterable

DEFAULT_DATASET = "code-rag-bench/humaneval"
# Most code-rag-bench tasks ship as a single 'train' split (no train/test
# separation — the dataset itself IS the eval set). Override per-task in
# YAML if you hit a dataset that uses 'test'.
DEFAULT_SPLIT = "train"


class CodeRAGBench:
    name = "coderagbench"

    def __init__(self, dataset: str = DEFAULT_DATASET, split: str = DEFAULT_SPLIT):
        self.dataset = dataset
        self.split = split

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]:
        try:
            from datasets import load_dataset
        except ImportError:
            print(f"[{self.name}] datasets package not installed; pip install datasets")
            return
        try:
            ds = load_dataset(self.dataset, split=self.split, streaming=True)
        except Exception as exc:
            print(f"[{self.name}] cannot load {self.dataset} ({self.split}): {exc}")
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
        refs = ex.get("references") or ex.get("docs") or []
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
