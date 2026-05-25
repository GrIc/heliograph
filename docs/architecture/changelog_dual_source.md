# Changelog — dual-source architecture

> **Goal**: capture code changes whether the workspace is a git repo OR a plain filesystem synced between two states.
> **Phase**: 3 (extension to existing T-302..T-308).

---

## 1. Why dual source

Phase 3 originally assumed every workspace is a git repo. Real deployments include:

- **Mounted code dumps** synced from external systems (no .git).
- **Workspaces refreshed via rsync/scp** between snapshots.
- **Generated codebases** where commits are batched outside the watched directory.

Solution: abstract the change detector. Same downstream pipeline (enricher, store, digest, channels) for both.

---

## 2. Abstraction

```
src/temporal/sources/
  __init__.py          → ChangeSource ABC, registry
  git_source.py        → wraps existing src/temporal/git_client.py
  fs_diff_source.py    → new: workspace snapshot diff
```

### ChangeSource interface

```python
class ChangeSource(ABC):
    name: str  # "git" | "fs_diff"

    @abstractmethod
    def detect_changes(self, *, max_items: int = 100) -> list[ChangeSet]:
        """Return ChangeSets since last seen state, in chronological order."""

    @abstractmethod
    def mark_processed(self, last: ChangeSet) -> None:
        """Persist 'we've consumed up to this point'."""
```

### ChangeSet (uniform unit)

```python
class ChangeSet(NamedTuple):
    id: str                       # commit SHA, or fs snapshot id
    timestamp: str                # ISO 8601
    author: str                   # git author, or "filesystem"
    subject: str                  # commit subject, or auto-generated
    body: str                     # commit body, or "" for fs
    files: list[FileChange]       # path + status + insertions + deletions
    diff_text: str                # unified diff (may be empty for fs adds/deletes)
    source: str                   # "git" | "fs_diff"
```

This is the only object the enricher needs.

---

## 3. GitSource

Thin adapter over existing `git_client.py`. No new functionality.

```python
class GitSource(ChangeSource):
    name = "git"

    def __init__(self, repo: Path, state_path: Path): ...

    def detect_changes(self, *, max_items: int = 100) -> list[ChangeSet]:
        sha = last_indexed_sha(self.state_path)
        commits = new_commits_since(sha, self.repo, max_commits=max_items)
        return [self._commit_to_changeset(c) for c in commits]

    def mark_processed(self, last: ChangeSet) -> None:
        set_last_indexed_sha(self.state_path, last.id)
```

---

## 4. FsDiffSource (new)

### State model

```json
// context/temporal/fs_snapshot.json
{
  "version": 1,
  "last_snapshot_at": "2026-05-25T10:32:00Z",
  "files": {
    "src/auth/login.py": {"mtime": 1716628320.0, "sha256": "abc123…", "size": 1432},
    "src/auth/__init__.py": {"mtime": 1716628100.0, "sha256": "def456…", "size": 42}
  }
}
```

`sha256` is the safety net: mtime alone misses touches without content change AND content changes that preserve mtime (rare but possible with archived restores).

### Detect algorithm

```
1. Read previous snapshot (or {} if first run).
2. Walk workspace honoring skip patterns (.git, node_modules, .vectordb, __pycache__, *.pyc, …).
3. For each file:
   - Compute mtime, size.
   - If size+mtime unchanged → reuse previous sha256 (no re-hash).
   - Else → hash sha256.
4. Build diff:
   - Added: in current, not in previous.
   - Deleted: in previous, not in current.
   - Modified: sha256 differs.
   - Unchanged: skipped.
5. If no changes → return [].
6. Build a single ChangeSet (one snapshot diff = one logical change):
   id        = "fs-<iso_timestamp>"
   timestamp = now()
   author    = "filesystem"
   subject   = f"FS sync: {n_added}A {n_modified}M {n_deleted}D"
   body      = ""
   files     = [FileChange(path, status, insertions, deletions)]
   diff_text = unified diff per file, capped at max_diff_lines
   source    = "fs_diff"
7. Persist new snapshot.
```

### Per-file insertions/deletions

For modified files: compute `difflib.unified_diff(prev_content, curr_content)`. `prev_content` requires storing content OR re-reading from a snapshot directory. **Design choice**: store sha256 only, on-modify regenerate diff by reading current + falling back to "added" semantics if previous content not available. Optional `snapshot_keep_content: true` config keeps last-N file contents for richer diffs (trade-off: disk space).

Default: NO content kept. Diff text contains file list + line counts, not full unified diff. Enricher still works (knows what changed, how many lines).

### Skip patterns (config)

```yaml
temporal:
  source: auto                    # auto | git | fs_diff
  fs_diff:
    skip_patterns:
      - "**/.git/**"
      - "**/node_modules/**"
      - "**/.vectordb/**"
      - "**/__pycache__/**"
      - "**/*.pyc"
      - "**/*.log"
      - "**/.idea/**"
      - "**/.vscode/**"
    max_diff_lines: 2000
    keep_content_snapshots: false
```

---

## 5. Auto-detection

`src/temporal/sources/__init__.py:resolve_source(cfg)`:

```python
def resolve_source(cfg: dict, workspace: Path) -> ChangeSource:
    mode = cfg.get("temporal", {}).get("source", "auto")
    if mode == "git":
        return GitSource(workspace, state_path=...)
    if mode == "fs_diff":
        return FsDiffSource(workspace, state_path=...)
    # auto
    if (workspace / ".git").is_dir():
        return GitSource(workspace, state_path=...)
    return FsDiffSource(workspace, state_path=...)
```

---

## 6. Enricher compatibility

Existing `src/temporal/enricher.py:enrich_commit(commit, files, diff_text, …)` already takes a triplet that maps cleanly to ChangeSet. Adapter:

```python
def enrich_changeset(cs: ChangeSet, *, llm_client, config, graph_store=None) -> dict:
    commit = Commit(sha=cs.id, author=cs.author, date=cs.timestamp,
                    subject=cs.subject, body=cs.body)
    return enrich_commit(commit, cs.files, cs.diff_text,
                          llm_client=llm_client, config=config, graph_store=graph_store)
```

For fs_diff ChangeSets: enricher receives subject like "FS sync: 3A 2M 1D" — intent classification still works (refactor/feature inferred from file paths + diff). `modules_affected` grounded against `cs.files` paths, same as git.

---

## 7. watch.py routing

```python
# watch.py --changelog-only
source = resolve_source(cfg, workspace)
changesets = source.detect_changes(max_items=cfg["temporal"]["bootstrap_commits"])
for cs in changesets:
    store.upsert_changeset(cs)   # store.py grows upsert_changeset alongside upsert_commit
enrich_pending(store, ...)
render_and_deliver(store, ...)
if changesets:
    source.mark_processed(changesets[-1])
```

`store.py` already keyed by SHA; `cs.id` can be either a git SHA or `fs-<timestamp>`. No schema change required.

---

## 8. Testing

- `tests/test_temporal_fs_diff_source.py` — unit tests:
  - First run with empty state → snapshot taken, 0 changes.
  - Add file → 1 change with status=A.
  - Modify file (content) → status=M.
  - Modify mtime only, same content → no change.
  - Delete file → status=D.
  - Skip pattern excludes node_modules → confirmed.
- `tests/test_temporal_source_resolver.py` — auto-detect picks git when .git present, fs_diff otherwise.
- `tests/test_temporal_enricher.py` already covers enrich_commit; add 1 case feeding a fs_diff-style ChangeSet.

---

## 9. Migration

Existing deployments with git keep working — `source: auto` defaults to git when `.git` exists. No config change required. FsDiffSource activates only when no git OR when explicitly forced.
