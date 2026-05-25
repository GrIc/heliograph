"""Tests for the ChangeSource abstraction.

Covers:
  * FsDiffSource snapshot / diff semantics
  * Skip patterns
  * Idempotency of empty diffs
  * resolve_source auto-detection
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.temporal.sources import ChangeSet, FileChange, resolve_source
from src.temporal.sources.fs_diff_source import FsDiffSource


# ── FsDiffSource basics ─────────────────────────────────────────────────


def _make_source(tmp_path: Path) -> FsDiffSource:
    ws = tmp_path / "ws"
    ws.mkdir()
    state = tmp_path / "state.json"
    return FsDiffSource(ws, state_path=state)


def test_first_run_is_empty(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    assert src.detect_changes() == []


def test_detect_added_file(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    src.detect_changes()  # establish baseline (still empty)
    (src.workspace / "a.py").write_text("hello")
    cs_list = src.detect_changes()
    assert len(cs_list) == 1
    cs = cs_list[0]
    assert cs.source == "fs_diff"
    assert cs.author == "filesystem"
    assert any(f.status == "A" for f in cs.files)
    assert "1A" in cs.subject


def test_no_change_after_mark_processed(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    (src.workspace / "a.py").write_text("hello")
    cs_list = src.detect_changes()
    src.mark_processed(cs_list[-1])
    # Same state → no further changes
    assert src.detect_changes() == []


def test_detect_modified(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    (src.workspace / "a.py").write_text("hello")
    cs_list = src.detect_changes()
    src.mark_processed(cs_list[-1])

    (src.workspace / "a.py").write_text("hello world")
    cs = src.detect_changes()[0]
    assert any(f.status == "M" and f.path == "a.py" for f in cs.files)


def test_detect_deleted(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    f = src.workspace / "a.py"
    f.write_text("hello")
    src.mark_processed(src.detect_changes()[-1])

    f.unlink()
    cs = src.detect_changes()[0]
    assert any(c.status == "D" and c.path == "a.py" for c in cs.files)


def test_mtime_touch_without_content_change_is_ignored(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    f = src.workspace / "a.py"
    f.write_text("hello")
    src.mark_processed(src.detect_changes()[-1])

    # Touch mtime via os.utime; size + sha256 unchanged
    import os
    import time

    t = time.time() + 100
    os.utime(f, (t, t))
    cs_list = src.detect_changes()
    assert cs_list == []


def test_skip_patterns_exclude_dirs(tmp_path: Path) -> None:
    src = _make_source(tmp_path)
    (src.workspace / "node_modules").mkdir()
    (src.workspace / "node_modules" / "garbage.js").write_text("noise")
    (src.workspace / "real.py").write_text("hi")
    cs = src.detect_changes()[0]
    paths = [f.path for f in cs.files]
    assert "real.py" in paths
    assert not any("node_modules" in p for p in paths)


# ── resolve_source auto-detect ─────────────────────────────────────────


def test_resolve_source_picks_fs_diff_when_no_git(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    src = resolve_source({}, ws)
    assert src.name == "fs_diff"


def test_resolve_source_picks_git_when_git_present(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    (ws / ".git").mkdir(parents=True)
    src = resolve_source({}, ws)
    assert src.name == "git"


def test_resolve_source_forced_fs_diff(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    (ws / ".git").mkdir(parents=True)
    src = resolve_source({"temporal": {"source": "fs_diff"}}, ws)
    assert src.name == "fs_diff"


# ── Adapter ─────────────────────────────────────────────────────────────


def test_changeset_to_commit_tuple_round_trip() -> None:
    from src.temporal.sources._adapter import changeset_to_commit_tuple

    cs = ChangeSet(
        id="fs-20260525T100000Z",
        timestamp="2026-05-25T10:00:00Z",
        author="filesystem",
        subject="FS sync: 1A 0M 0D",
        body="",
        files=[FileChange(path="a.py", status="A")],
        diff_text="",
        source="fs_diff",
    )
    commit, files, diff = changeset_to_commit_tuple(cs)
    assert commit.sha == cs.id
    assert commit.author == "filesystem"
    assert len(files) == 1
    assert files[0].status == "A"
    assert diff == ""
