"""CodeRAG-Bench adapter. SCAFFOLD."""
from __future__ import annotations
from typing import Any, Iterable

HF_DATASET = "code-rag-bench/coderagbench"


class CodeRAGBench:
    name = "coderagbench"

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]:
        try:
            from datasets import load_dataset
        except ImportError:
            print(f"[{self.name}] datasets package not installed")
            return
        try:
            ds = load_dataset(HF_DATASET, split="test", streaming=True)
        except Exception as e:
            print(f"[{self.name}] cannot load {HF_DATASET}: {e}")
            return
        for i, ex in enumerate(ds):
            if limit and i >= limit:
                return
            yield {
                "id": f"coderagbench-{i:06d}",
                "kind": "qa",
                "question": ex.get("question", ""),
                "expected_answer_contains": ex.get("answer_keywords", []),
                "_raw": ex,
            }
