"""Stub implementations for tools whose real implementation is deferred.

Each stub:
- Validates schema (so clients see consistent contracts).
- Returns ``{"error": {"code": "not_implemented", ...}}`` via ToolError.
- Auto-discovered like real tools so ``list_tools`` shows the full catalog.

When a stub is replaced by a real impl, just delete its class from this module
and add the new file under ``src/mcp/tools/``.
"""

from __future__ import annotations

from src.mcp.base import BaseTool, ToolError


_GENERIC_INPUT = {
    "type": "object",
    "additionalProperties": True,
}
_GENERIC_OUTPUT = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "notes": {"type": "string"},
    },
    "additionalProperties": True,
}


class _StubTool(BaseTool):
    """Common base; subclasses set ``name`` + ``description``."""

    input_schema = _GENERIC_INPUT
    output_schema = _GENERIC_OUTPUT
    examples: list[dict] = []
    requires_citations = False

    def handle(self, args: dict) -> dict:
        raise ToolError(
            "not_implemented",
            f"Tool '{self.name}' is a stub. Real implementation deferred.",
            hint="See docs/architecture/mcp_tools_v2.md for status.",
        )


# ── Admin ────────────────────────────────────────────────────────────────


class Reindex(_StubTool):
    name = "reindex"
    description = "Trigger a full reindex of the workspace (stub — not yet implemented)."
    auth_required = True
    rate_limit_per_minute = 5


class IngestFiles(_StubTool):
    name = "ingest_files"
    description = "Index ad-hoc files into the RAG store (stub — not yet implemented)."
    auth_required = True
    rate_limit_per_minute = 10


class GetCoverageReport(_StubTool):
    name = "get_coverage_report"
    description = "Return the indexing quality / coverage report (stub — not yet implemented)."
    auth_required = True
    rate_limit_per_minute = 10


# ── Architecture ─────────────────────────────────────────────────────────


class GuidedTour(_StubTool):
    name = "guided_tour"
    description = "Produce a recommended reading order for understanding a topic (stub)."


class GetArchitectureBlueprint(_StubTool):
    name = "get_architecture_blueprint"
    description = (
        "Compose a structured implementation plan for a feature "
        "(similar features, modules, insertion points, risks). Not yet implemented."
    )


# ── Graph ────────────────────────────────────────────


class ShortestPath(_StubTool):
    name = "shortest_path"
    description = "Shortest path in the call graph between two symbols (stub — not yet implemented)."


# ── Conventions ──────────────────────────────────────────────────────────


class CheckConventions(_StubTool):
    name = "check_conventions"
    description = "Check proposed code against inferred conventions (stub — not yet implemented)."
