"""GitSource — adapter over ``src.temporal.git_client``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.temporal import git_client
from src.temporal.sources import ChangeSet, ChangeSource, FileChange

logger = logging.getLogger(__name__)


class GitSource(ChangeSource):
    """Yields ChangeSets from new git commits since the last indexed SHA."""

    name = "git"

    def __init__(self, repo: Path) -> None:
        self.repo = Path(repo).resolve()

    def detect_changes(self, *, max_items: int = 100) -> List[ChangeSet]:
        sha = git_client.last_indexed_sha()
        commits = git_client.new_commits_since(sha, max_commits=max_items)
        out: List[ChangeSet] = []
        for c in commits:
            files = git_client.files_changed(c.sha)
            diff = git_client.diff_for_commit(c.sha, max_lines=2000)
            out.append(
                ChangeSet(
                    id=c.sha,
                    timestamp=c.date,
                    author=c.author,
                    subject=c.subject,
                    body=c.body or "",
                    files=[
                        FileChange(
                            path=f.path,
                            status=f.status,
                            insertions=f.insertions,
                            deletions=f.deletions,
                        )
                        for f in files
                    ],
                    diff_text=diff,
                    source="git",
                )
            )
        return out

    def mark_processed(self, last: ChangeSet) -> None:
        git_client.set_last_indexed_sha(last.id)
