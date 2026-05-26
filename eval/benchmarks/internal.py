"""Hand-curated Q/A on the agent-hub repo itself. Cheap, fast, dogfood.

Reads JSONL files from eval/fixtures/agent-hub-internal/.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Iterable

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "agent-hub-internal"


class InternalBenchmark:
    name = "internal"

    def iter_cases(self, limit: int | None = None) -> Iterable[dict[str, Any]]:
        sources = [FIXTURES_DIR / "questions.jsonl", FIXTURES_DIR / "tasks.jsonl"]
        n = 0
        for src in sources:
            if not src.exists():
                continue
            for line in src.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                case = json.loads(line)
                case.setdefault("kind", "qa")
                yield case
                n += 1
                if limit and n >= limit:
                    return
