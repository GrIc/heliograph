"""ping — health check and tool availability status."""

from __future__ import annotations

import time

from src.mcp.base import BaseTool
from src.mcp.tools._common import lazy_graph, lazy_store, lazy_temporal


_BOOT_TIME = time.time()


class Ping(BaseTool):
    name = "ping"
    description = (
        "Health check. Returns server status, uptime, and which subsystems "
        "(vector store, knowledge graph, temporal store) are available."
    )
    input_schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["status", "uptime_seconds", "subsystems"],
        "properties": {
            "status": {"type": "string"},
            "uptime_seconds": {"type": "integer"},
            "subsystems": {
                "type": "object",
                "properties": {
                    "vector_store": {"type": "boolean"},
                    "knowledge_graph": {"type": "boolean"},
                    "temporal_store": {"type": "boolean"},
                },
                "required": ["vector_store", "knowledge_graph", "temporal_store"],
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    }
    examples = [
        {
            "input": {},
            "output": {
                "status": "ok",
                "uptime_seconds": 42,
                "subsystems": {
                    "vector_store": True,
                    "knowledge_graph": False,
                    "temporal_store": True,
                },
            },
        }
    ]
    requires_citations = False
    auth_required = False
    rate_limit_per_minute = 300

    def handle(self, args: dict) -> dict:
        return {
            "status": "ok",
            "uptime_seconds": int(time.time() - _BOOT_TIME),
            "subsystems": {
                "vector_store": lazy_store() is not None,
                "knowledge_graph": lazy_graph() is not None,
                "temporal_store": lazy_temporal() is not None,
            },
        }
