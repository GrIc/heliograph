"""RepoBench-R adapter.

Dataset: tianyang/repobench-r (Hugging Face). Cross-file retrieval task.
For each case, agent must retrieve the right code chunks given context lines.

Status: SCAFFOLD. Dataset path + case mapping noted but not wired.
"""
from __future__ import annotations
from typing import Any, Iterable

HF_DATASET = "tianyang/repobench-r"


class RepoBenchR:
    name = "repobench_r"

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]:
        try:
            from datasets import load_dataset
        except ImportError:
            print(f"[{self.name}] datasets package not installed, skipping")
            return
        try:
            ds = load_dataset(HF_DATASET, split="train", streaming=True)
        except Exception as e:
            print(f"[{self.name}] cannot load {HF_DATASET}: {e}")
            return
        for i, ex in enumerate(ds):
            if limit and i >= limit:
                return
            # TODO: map RepoBench-R fields → our case schema.
            # Typical fields include 'context', 'next_line', 'candidates', etc.
            yield {
                "id": f"repobench_r-{i:06d}",
                "kind": "retrieval",
                "query": ex.get("context", "")[:2000],
                "expected_sources": [],   # TODO: derive from ex['gold'] equivalent
                "_raw": ex,
            }
