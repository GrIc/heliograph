"""Shared schema fragments and helpers for MCP tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Single source of truth for the workspace root, shared with the citation
# middleware. Override at runtime by exporting MCP_WORKSPACE_PATH.
WORKSPACE_PATH = Path(os.getenv("MCP_WORKSPACE_PATH", "workspace"))


SOURCE_SCHEMA = {
    "type": "object",
    "required": ["path", "line_start", "line_end"],
    "properties": {
        "path": {"type": "string"},
        "line_start": {"type": "integer", "minimum": 1},
        "line_end": {"type": "integer", "minimum": 1},
        "score": {"type": "number"},
    },
    "additionalProperties": True,
}

SOURCES_LIST_SCHEMA = {
    "type": "array",
    "items": SOURCE_SCHEMA,
}


def clamp_line_range(line_start: int, line_end: int, path: Path) -> tuple[int, int]:
    """Clamp a line range to a file's actual length.

    Returns the original range if the file is unreadable.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            n_lines = sum(1 for _ in f)
    except OSError:
        return line_start, line_end
    n_lines = max(1, n_lines)
    ls = max(1, min(line_start, n_lines))
    le = max(ls, min(line_end, n_lines))
    return ls, le


def collect_node_sources(
    node_data: dict,
    sources: list[dict],
    seen_paths: set[str],
    *,
    score: float = 1.0,
    line_window: int = 200,
) -> None:
    """Append citations derived from a graph node's ``source_docs`` list.

    Mutates ``sources`` and ``seen_paths`` in place. Used by every graph-
    backed tool (get_callers, get_callees, preview_impact, search_graph,
    find_hub_modules, get_module_dependencies) to keep the logic DRY.
    """
    for sd in node_data.get("source_docs", []):
        if not sd or sd in seen_paths:
            continue
        seen_paths.add(sd)
        full = WORKSPACE_PATH / sd
        if not full.exists():
            continue
        ls, le = clamp_line_range(1, line_window, full)
        sources.append({
            "path": sd,
            "line_start": ls,
            "line_end": le,
            "score": score,
        })


def make_source(path: str, *, score: float = 1.0, line_window: int = 200) -> dict | None:
    """Build a validated citation source dict for a workspace path.

    Returns ``None`` if the path does not exist in the workspace.
    """
    if not path:
        return None
    full = WORKSPACE_PATH / path
    if not full.exists():
        return None
    ls, le = clamp_line_range(1, line_window, full)
    return {"path": path, "line_start": ls, "line_end": le, "score": score}


def project_search_result_to_source(result: dict) -> dict:
    """Map a VectorStore search result to a citation source.

    Each result dict carries ``source`` (path), ``line_start``, ``line_end``.
    """
    path = result.get("source", "")
    ls = int(result.get("line_start") or 1)
    le = int(result.get("line_end") or ls)
    full = WORKSPACE_PATH / path if path else None
    if full and full.exists():
        ls, le = clamp_line_range(ls, le, full)
    return {
        "path": path,
        "line_start": ls,
        "line_end": le,
        "score": round(float(result.get("score", 0.0)), 4),
    }


def lazy_store() -> Any:
    """Return a cached VectorStore instance or None if init fails."""
    return _Singletons.store()


def lazy_graph() -> Any:
    """Return a cached KnowledgeGraph instance or None if disabled/empty."""
    return _Singletons.graph()


def lazy_temporal() -> Any:
    """Return a cached TemporalStore instance or None if unavailable."""
    return _Singletons.temporal()


def lazy_config() -> dict:
    """Cached config."""
    return _Singletons.config()


class _Singletons:
    _store: Any = None
    _graph: Any = None
    _temporal: Any = None
    _client: Any = None
    _config: dict | None = None

    @classmethod
    def config(cls) -> dict:
        if cls._config is None:
            from src.config import load_config

            cls._config = load_config()
        return cls._config

    @classmethod
    def client(cls) -> Any:
        if cls._client is None:
            from src.client import ResilientClient

            cfg = cls.config()
            defaults = cfg.get("_defaults", {})
            cls._client = ResilientClient(
                api_key=defaults.get("api_key", ""),
                base_url=defaults.get("api_base_url", ""),
                max_retries=cfg["retry"]["max_attempts"],
                base_delay=cfg["retry"]["base_delay_s"],
                max_delay=cfg["retry"]["max_delay_s"],
            )
        return cls._client

    @classmethod
    def store(cls) -> Any:
        if cls._store is None:
            try:
                from src.rag.store import VectorStore

                cfg = cls.config()
                embed_model = cfg["models"].get("embed", "")
                rerank_model = cfg["models"].get("rerank", "")
                cls._store = VectorStore(
                    client=cls.client(),
                    embed_model=embed_model,
                    rerank_model=rerank_model,
                )
            except Exception:
                cls._store = None
        return cls._store

    @classmethod
    def graph(cls) -> Any:
        if cls._graph is None:
            try:
                cfg = cls.config()
                graph_cfg = cfg.get("graph", {})
                if not graph_cfg.get("enabled", False):
                    return None
                from src.rag.graph import KnowledgeGraph

                persist_dir = graph_cfg.get("persist_dir", ".graphdb")
                kg = KnowledgeGraph(persist_dir=persist_dir)
                if kg.node_count == 0:
                    return None
                cls._graph = kg
            except Exception:
                cls._graph = None
        return cls._graph

    @classmethod
    def temporal(cls) -> Any:
        if cls._temporal is None:
            try:
                from src.temporal.store import TemporalStore

                cfg = cls.config()
                db_path = cfg.get("temporal", {}).get(
                    "db_path", "context/temporal/store.sqlite"
                )
                if not Path(db_path).exists():
                    return None
                cls._temporal = TemporalStore(db_path)
            except Exception:
                cls._temporal = None
        return cls._temporal
