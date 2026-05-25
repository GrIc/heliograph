"""Adapter that lets the existing enricher consume ChangeSet objects.

The enricher API ``enrich_commit(commit, files, diff_text, ...)`` predates the
``ChangeSource`` abstraction. This module bridges them without modifying the
enricher signature.
"""

from __future__ import annotations

from typing import Any, Dict

from src.temporal.git_client import Commit as GitCommit
from src.temporal.git_client import FileChange as GitFileChange
from src.temporal.sources import ChangeSet


def changeset_to_commit_tuple(cs: ChangeSet) -> tuple[GitCommit, list[GitFileChange], str]:
    """Project a ChangeSet onto the (Commit, list[FileChange], diff_text) shape."""
    commit = GitCommit(
        sha=cs.id,
        author=cs.author,
        date=cs.timestamp,
        subject=cs.subject,
        body=cs.body or "",
    )
    files = [
        GitFileChange(
            path=f.path,
            status=f.status,
            insertions=f.insertions,
            deletions=f.deletions,
        )
        for f in cs.files
    ]
    return commit, files, cs.diff_text


def upsert_changeset(store: Any, cs: ChangeSet) -> None:
    """Upsert a ChangeSet into the TemporalStore via the legacy commit API."""
    commit, files, _ = changeset_to_commit_tuple(cs)
    store.upsert_commit(commit, files)
