"""SWE-bench Lite adapter.

Dataset: princeton-nlp/SWE-bench_Lite (300 real GitHub issues with hidden
tests). Each case = (repo, base_commit, problem_statement, test_patch).

Status: SCAFFOLD. The full eval requires building per-repo containers; this
adapter just maps cases. The `aider` or `claude_code` adapter is responsible
for actually proposing a patch; running the hidden tests requires the
official `swebench` harness (optional dep).
"""
from __future__ import annotations
from typing import Any, Iterable

HF_DATASET = "princeton-nlp/SWE-bench_Lite"


class SWEBenchLite:
    name = "swebench_lite"

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
                "id": ex.get("instance_id", f"swebench-{i:06d}"),
                "kind": "patch",
                "repo": ex.get("repo"),
                "base_commit": ex.get("base_commit"),
                "problem_statement": ex.get("problem_statement"),
                "test_patch": ex.get("test_patch"),
                "_raw": ex,
            }
