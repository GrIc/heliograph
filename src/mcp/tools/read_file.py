"""read_file — read a file from the workspace, safely."""

from __future__ import annotations

from pathlib import Path

from src.mcp.base import BaseTool, ToolError
from src.mcp.tools._common import WORKSPACE_PATH


class ReadFile(BaseTool):
    name = "read_file"
    description = (
        "Read a file from the workspace directory. Refuses path traversal and "
        "returns size + content. Useful for agents that need raw source."
    )
    input_schema = {
        "type": "object",
        "required": ["filepath"],
        "properties": {
            "filepath": {"type": "string", "minLength": 1, "maxLength": 500},
            "max_bytes": {"type": "integer", "minimum": 1, "maximum": 2_000_000, "default": 500_000},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["filepath", "content", "size"],
        "properties": {
            "filepath": {"type": "string"},
            "content": {"type": "string"},
            "size": {"type": "integer"},
            "truncated": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
    examples = [
        {"input": {"filepath": "src/main.py"},
         "output": {"filepath": "src/main.py", "content": "...", "size": 1234, "truncated": False}}
    ]
    requires_citations = False
    rate_limit_per_minute = 120

    def handle(self, args: dict) -> dict:
        filepath = args["filepath"]
        max_bytes = int(args.get("max_bytes", 500_000))
        full = (WORKSPACE_PATH / filepath).resolve()
        ws = WORKSPACE_PATH.resolve()
        if not str(full).startswith(str(ws)):
            raise ToolError("invalid_input", "Path traversal blocked", hint="Use relative paths.")
        if not full.exists():
            raise ToolError("not_found", f"File not found: {filepath}")
        if not full.is_file():
            raise ToolError("invalid_input", f"Not a file: {filepath}")
        raw = full.read_bytes()
        truncated = len(raw) > max_bytes
        content = raw[:max_bytes].decode("utf-8", errors="replace")
        return {
            "filepath": filepath,
            "content": content,
            "size": len(raw),
            "truncated": truncated,
        }
