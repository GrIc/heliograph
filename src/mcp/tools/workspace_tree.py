"""workspace_tree — directory tree of the indexed workspace."""

from __future__ import annotations

from pathlib import Path

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import WORKSPACE_PATH


_DEFAULT_SKIP = {
    "node_modules", "__pycache__", ".git", ".svn", "dist", "build",
    ".venv", "venv", ".vectordb", ".graphdb", ".idea", ".vscode", "target",
}


class WorkspaceTree(BaseTool):
    name = "workspace_tree"
    description = (
        "Return a text rendering of the workspace directory tree up to a "
        "given depth, with common build/vendor directories skipped."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "max_depth": {"type": "integer", "minimum": 1, "maximum": 8, "default": 3},
            "subdir": {"type": "string", "default": ""},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["root", "tree"],
        "properties": {
            "root": {"type": "string"},
            "tree": {"type": "string"},
        },
        "additionalProperties": False,
    }
    examples = [{"input": {"max_depth": 2}, "output": {"root": "workspace", "tree": "..."}}]
    requires_citations = False
    rate_limit_per_minute = 60

    def handle(self, args: dict) -> dict:
        max_depth = int(args.get("max_depth", 3))
        subdir = args.get("subdir", "").strip().lstrip("/")
        root = (WORKSPACE_PATH / subdir).resolve()
        ws = WORKSPACE_PATH.resolve()
        if not str(root).startswith(str(ws)):
            raise ToolError("invalid_input", "Path traversal blocked")
        if not root.exists():
            raise ToolError("not_found", f"Path not found: {subdir or '.'}")
        lines: list[str] = [f"Root: {root.relative_to(ws) if root != ws else '.'}", ""]
        _render(root, lines, "", max_depth, 0)
        return {"root": str(root.relative_to(ws) if root != ws else "."), "tree": "\n".join(lines)}


def _render(path: Path, lines: list[str], prefix: str, max_depth: int, depth: int) -> None:
    if depth >= max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        return
    entries = [e for e in entries if not e.name.startswith(".") and e.name not in _DEFAULT_SKIP]
    for i, entry in enumerate(entries):
        last = i == len(entries) - 1
        connector = "└── " if last else "├── "
        marker = "/" if entry.is_dir() else ""
        lines.append(f"{prefix}{connector}{entry.name}{marker}")
        if entry.is_dir():
            ext = "    " if last else "│   "
            _render(entry, lines, prefix + ext, max_depth, depth + 1)
