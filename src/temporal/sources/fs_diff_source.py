"""FsDiffSource — detect changes by snapshotting workspace state.

Algorithm
---------
1. Read the previous snapshot (or ``{}`` on first run).
2. Walk the workspace, honoring skip patterns.
3. For each file, compute ``mtime + size``; reuse the previous SHA-256 if
   both are unchanged, else re-hash.
4. Compare current vs previous to derive ``added`` / ``modified`` / ``deleted``.
5. If anything changed, emit ONE :class:`ChangeSet` summarizing the sync diff.
6. Persist the new snapshot.

Notes
-----
* This source produces at most one ChangeSet per detection call (per sync).
* File content is not retained between snapshots: line-level diff text is
  best-effort (only adds full content for new files; for modifications, includes
  per-file size+line-count delta but no patch).
* ID format: ``fs-<isoformat>``. Author: ``"filesystem"``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.temporal.sources import ChangeSet, ChangeSource, FileChange

logger = logging.getLogger(__name__)

DEFAULT_SKIP_PATTERNS = [
    "**/.git/**",
    "**/node_modules/**",
    "**/.vectordb/**",
    "**/.graphdb/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.log",
    "**/.idea/**",
    "**/.vscode/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
    "**/target/**",
]


@dataclass
class _FileMeta:
    mtime: float
    size: int
    sha256: str

    def to_json(self) -> dict:
        return {"mtime": self.mtime, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_json(cls, d: dict) -> "_FileMeta":
        return cls(
            mtime=float(d.get("mtime", 0.0)),
            size=int(d.get("size", 0)),
            sha256=str(d.get("sha256", "")),
        )


class FsDiffSource(ChangeSource):
    """Snapshot-diff based change source."""

    name = "fs_diff"

    def __init__(
        self,
        workspace: Path,
        *,
        cfg: Optional[Dict[str, Any]] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        cfg = cfg or {}
        self.skip_patterns = list(cfg.get("skip_patterns") or DEFAULT_SKIP_PATTERNS)
        self.max_file_size = int(cfg.get("max_file_size", 5_000_000))  # 5 MB default
        self.state_path = (
            Path(state_path)
            if state_path
            else Path("context/temporal/fs_snapshot.json")
        )

    # ── Public API ──────────────────────────────────────────────────────

    def detect_changes(self, *, max_items: int = 1) -> List[ChangeSet]:
        previous = self._load_snapshot()
        current = self._build_snapshot()
        diff = self._diff(previous, current)
        if not any(diff.values()):
            return []

        changeset = self._build_changeset(diff, current)
        self._pending_snapshot = current  # save on mark_processed
        return [changeset]

    def mark_processed(self, last: ChangeSet) -> None:
        if hasattr(self, "_pending_snapshot"):
            self._save_snapshot(self._pending_snapshot)
            del self._pending_snapshot

    # ── Snapshot I/O ────────────────────────────────────────────────────

    def _load_snapshot(self) -> Dict[str, _FileMeta]:
        if not self.state_path.exists():
            return {}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            files = raw.get("files", {})
            return {p: _FileMeta.from_json(v) for p, v in files.items()}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cannot read fs snapshot %s: %s", self.state_path, e)
            return {}

    def _save_snapshot(self, snapshot: Dict[str, _FileMeta]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "last_snapshot_at": _iso_now(),
            "files": {p: m.to_json() for p, m in snapshot.items()},
        }
        self.state_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Walk + hash ─────────────────────────────────────────────────────

    def _is_skipped(self, rel_path: str) -> bool:
        # Match against the full relative path and against any path segment,
        # so patterns like ``**/node_modules/**`` and ``**/*.pyc`` work
        # whether the match is at root or in a subdirectory.
        parts = rel_path.split("/")
        candidates = [rel_path] + [
            "/".join(parts[i:]) for i in range(1, len(parts))
        ]
        for pat in self.skip_patterns:
            stripped = pat[3:] if pat.startswith("**/") else pat
            for cand in candidates:
                if fnmatch(cand, pat) or fnmatch(cand, stripped):
                    return True
                # Match a directory segment anywhere in the path
                if "/" not in stripped and any(
                    fnmatch(seg, stripped) for seg in parts
                ):
                    return True
        return False

    def _build_snapshot(self) -> Dict[str, _FileMeta]:
        previous = self._load_snapshot()
        snapshot: Dict[str, _FileMeta] = {}
        for root, dirs, files in os.walk(self.workspace):
            # prune skipped dirs in-place
            dirs[:] = [
                d for d in dirs
                if not self._is_skipped(self._rel(Path(root) / d) + "/")
            ]
            for fname in files:
                full = Path(root) / fname
                rel = self._rel(full)
                if self._is_skipped(rel):
                    continue
                try:
                    st = full.stat()
                except OSError:
                    continue
                if st.st_size > self.max_file_size:
                    continue
                prev = previous.get(rel)
                if prev and prev.mtime == st.st_mtime and prev.size == st.st_size:
                    snapshot[rel] = prev
                else:
                    snapshot[rel] = _FileMeta(
                        mtime=st.st_mtime,
                        size=st.st_size,
                        sha256=self._hash_file(full),
                    )
        return snapshot

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.workspace)).replace(os.sep, "/")
        except ValueError:
            return str(path)

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        try:
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        except OSError:
            return ""
        return h.hexdigest()

    # ── Diff ────────────────────────────────────────────────────────────

    def _diff(
        self,
        previous: Dict[str, _FileMeta],
        current: Dict[str, _FileMeta],
    ) -> Dict[str, List[str]]:
        prev_keys = set(previous.keys())
        cur_keys = set(current.keys())
        added = sorted(cur_keys - prev_keys)
        deleted = sorted(prev_keys - cur_keys)
        modified = sorted(
            p for p in cur_keys & prev_keys
            if current[p].sha256 != previous[p].sha256
        )
        return {"added": added, "modified": modified, "deleted": deleted}

    def _build_changeset(
        self,
        diff: Dict[str, List[str]],
        current: Dict[str, _FileMeta],
    ) -> ChangeSet:
        ts = _iso_now()
        cid = f"fs-{ts.replace(':', '').replace('-', '')[:15]}"
        n_a = len(diff["added"])
        n_m = len(diff["modified"])
        n_d = len(diff["deleted"])
        subject = f"FS sync: {n_a}A {n_m}M {n_d}D"
        files: List[FileChange] = []
        for p in diff["added"]:
            files.append(FileChange(path=p, status="A"))
        for p in diff["modified"]:
            files.append(FileChange(path=p, status="M"))
        for p in diff["deleted"]:
            files.append(FileChange(path=p, status="D"))
        return ChangeSet(
            id=cid,
            timestamp=ts,
            author="filesystem",
            subject=subject,
            body="",
            files=files,
            diff_text="",  # no per-line diff; enricher works on file list
            source="fs_diff",
        )


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
