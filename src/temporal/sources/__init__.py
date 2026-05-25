"""Pluggable change sources for the changelog pipeline.

The temporal pipeline consumes ``ChangeSet`` objects from a ``ChangeSource``.
Two concrete sources:

* :class:`~src.temporal.sources.git_source.GitSource` — wraps git.
* :class:`~src.temporal.sources.fs_diff_source.FsDiffSource` — workspace snapshot
  diff between two syncs. No git required.

Auto-detection via :func:`resolve_source`: prefer git when ``.git/`` is present,
fall back to ``fs_diff`` otherwise. Override via ``temporal.source`` config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class FileChange:
    """File-level change in a ChangeSet."""

    path: str
    status: str  # A | M | D | R
    insertions: int = 0
    deletions: int = 0


@dataclass
class ChangeSet:
    """Uniform unit consumed by the enricher.

    For git: id = commit SHA, author/subject from git, diff_text from ``git show``.
    For fs_diff: id = ``fs-<iso_timestamp>``, author = "filesystem",
                  subject auto-generated from counts, diff_text optional.
    """

    id: str
    timestamp: str
    author: str
    subject: str
    body: str
    files: List[FileChange] = field(default_factory=list)
    diff_text: str = ""
    source: str = ""  # "git" | "fs_diff"


class ChangeSource(ABC):
    """Abstract change source."""

    name: str = "abstract"

    @abstractmethod
    def detect_changes(self, *, max_items: int = 100) -> List[ChangeSet]:
        """Return new ChangeSets since last seen state, chronologically."""

    @abstractmethod
    def mark_processed(self, last: ChangeSet) -> None:
        """Persist progress up to and including *last*."""


def resolve_source(cfg: dict, workspace: Path) -> ChangeSource:
    """Resolve which ChangeSource to use based on config + workspace state.

    Modes:
      - ``auto`` (default): GitSource if ``.git`` is present, else FsDiffSource.
      - ``git``: force GitSource (raises if no git repo).
      - ``fs_diff``: force FsDiffSource.
    """
    temporal_cfg = cfg.get("temporal", {})
    mode = temporal_cfg.get("source", "auto")

    if mode == "git":
        from src.temporal.sources.git_source import GitSource

        return GitSource(workspace)
    if mode == "fs_diff":
        from src.temporal.sources.fs_diff_source import FsDiffSource

        return FsDiffSource(workspace, cfg=temporal_cfg.get("fs_diff", {}))
    # auto
    if (workspace / ".git").is_dir():
        from src.temporal.sources.git_source import GitSource

        return GitSource(workspace)
    from src.temporal.sources.fs_diff_source import FsDiffSource

    return FsDiffSource(workspace, cfg=temporal_cfg.get("fs_diff", {}))


__all__ = [
    "ChangeSet",
    "ChangeSource",
    "FileChange",
    "resolve_source",
]
