# MCP Tools Architecture — v2 (Phase 4 refactor)

> **Status**: Phase 4 in-progress. Framework done; tools migrating from legacy bridge to BaseTool registry.
> **Audience**: contributors implementing or modifying MCP tools.

---

## 1. Layered architecture

```
┌─────────────────────────────────────────────────────────┐
│  MCP clients (Roo Code, Continue.dev, Cursor, Cline…)  │
└────────────────────────────┬────────────────────────────┘
                             │ JSON-RPC over SSE or stdio
                             ▼
┌─────────────────────────────────────────────────────────┐
│  Transports                                              │
│  src/mcp/transports/sse.py   (FastAPI mount /mcp/sse)   │
│  src/mcp/transports/stdio.py (python -m src.mcp.server) │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  Middleware pipeline (executed in this order)            │
│  1. auth.py        → bearer token check                  │
│  2. rate_limit.py  → token bucket, per-tool override     │
│  3. base.py        → JSON Schema validate(input)         │
│  4. BaseTool.handle(args)                                │
│  5. base.py        → JSON Schema validate(output)        │
│  6. citation.py    → enforce sources contract            │
│  7. logging.py     → structured JSON log line            │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  Tool registry (src/mcp/registry.py)                     │
│  Auto-discovers src/mcp/tools/*.py subclasses of BaseTool│
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  Data sources                                            │
│  src/rag/store.py    (ChromaDB)                          │
│  src/rag/graph.py    (KuzuDB knowledge graph)            │
│  src/temporal/store.py (SQLite enriched commits)         │
│  workspace/          (files for citations)               │
└─────────────────────────────────────────────────────────┘
```

---

## 2. BaseTool contract

Every tool inherits from `BaseTool` (src/mcp/base.py):

```python
class MyTool(BaseTool):
    name = "my_tool"                    # unique kebab/snake identifier
    description = "..."                  # 1-3 sentence summary
    input_schema = { ... }               # JSON Schema, validated pre-handle
    output_schema = { ... }              # JSON Schema, validated post-handle
    examples = [ {"input": {...}, "output": {...}} ]
    requires_citations = True            # enforce sources field non-empty
    auth_required = False                # admin tools = True
    rate_limit_per_minute = 60           # override per tool

    def handle(self, args: dict) -> dict:
        # Pure business logic. Framework wraps validation + logging.
        ...
```

**Invariants**:
- `handle()` MUST return a dict matching `output_schema`.
- If `requires_citations`: result MUST include `sources: [{path, line_start, line_end}]` with at least one valid entry (or `notes` field explaining why empty).
- Raise `ToolError(code, message, hint)` for known failure modes. Generic exceptions become `internal_error`.

---

## 3. Tool catalog — Phase 4 status

Legend: ✅ implemented · 🟡 stub (typed, returns `not_implemented`) · 📋 Phase 5+

### A. Meta + admin
| Tool | Status | Notes |
|------|--------|-------|
| `list_tools` | ✅ | Returns registry catalog with schemas |
| `ping` | ✅ | Health check |
| `reindex` | 🟡 | Bridge in workspace_session; will wrap |
| `ingest_files` | 🟡 | |
| `get_coverage_report` | 🟡 | |

### B. Retrieval
| Tool | Status | Notes |
|------|--------|-------|
| `find_code` | ✅ | Vector search + filters |
| `ask_expert` | ✅ | RAG Q&A with grounded LLM, mandatory citations |
| `find_similar` | 🟡 | |

### C. Architecture
| Tool | Status | Notes |
|------|--------|-------|
| `locate_feature` | ✅ | Ranked file paths from synthesis |
| `explain_module` | ✅ | L1/L2 summary retrieval |
| `guided_tour` | 🟡 | |
| `get_architecture_blueprint` | 📋 | Phase 5 — composes other tools |

### D. Graph (depend on Phase 2)
| Tool | Status | Notes |
|------|--------|-------|
| `get_callers` | ✅ | Wraps KnowledgeGraph.get_callers |
| `preview_impact` | ✅ | Topology-weighted impact analysis |
| `get_callees` | 🟡 | |
| `get_module_dependencies` | 🟡 | |
| `shortest_path` | 🟡 | |
| `find_hub_modules` | 🟡 | |

### E. Temporal (depend on Phase 3)
| Tool | Status | Notes |
|------|--------|-------|
| `recent_changes` | ✅ | TemporalStore range query |
| `explain_change` | ✅ | Enriched summary + risk |
| `why_does_this_exist` | 🟡 | |
| `what_changed_here` | 🟡 | |
| `blame_plus` | 🟡 | |

### F. Conventions
| Tool | Status | Notes |
|------|--------|-------|
| `check_conventions` | 🟡 | Stub — rules in Phase 5 |

**Totals**: 10 ✅, 12 🟡, 1 📋 = 23 in spec.

---

## 4. Deviation from spec — rationale

### 4.1 Top-10 ship, stubs for rest
**Spec**: ship 23 in one Phase 4 batch.
**Reality**: stubs let `list_tools` return the full catalog so clients can discover everything immediately. Real impl ships incrementally. Each stub returns a deterministic `{"error": {"code": "not_implemented"}}` per output schema → no surprise behavior.

### 4.2 Bridge → BaseTool migration
Legacy `src/mcp/server.py:_AgentHubBridge` contains tool implementations bypassing the framework. These are migrated to `src/mcp/tools/*.py`. The bridge class is deleted post-migration; `create_mcp_server()` only wires the registry.

### 4.3 `get_architecture_blueprint` deferred
Spec marks it the "flagship" 3-day tool. It composes `find_similar` + `get_callers` + `preview_impact` + pattern discovery (Phase 5). Building it before primitives are stable creates rework. Deferred to Phase 5.

---

## 5. Adding a new tool — checklist

1. Create `src/mcp/tools/my_tool.py` with `class MyTool(BaseTool)`.
2. Define `name`, `description`, `input_schema`, `output_schema`, `examples`.
3. Implement `handle(args)`.
4. Add golden test in `tests/golden/test_mcp_tools.py`.
5. Re-run `python scripts/build_mcp_docs.py` to regenerate `docs/mcp/tools.md`.
6. No registry changes — auto-discovery picks it up at startup.

---

## 6. Error envelope

All errors normalize to:
```json
{"error": {"code": "<code>", "message": "<human>", "hint": "<optional fix>"}}
```

Standard codes:
- `invalid_input` — input schema failed
- `invalid_output` — output schema failed (tool bug)
- `citation_failure` — sources contract violated
- `not_found` — referenced entity doesn't exist
- `insufficient_evidence` — cannot ground answer in source
- `not_implemented` — stub tool
- `rate_limited` — quota exceeded
- `unauthorized` — auth required, token missing/wrong
- `internal_error` — unhandled exception

---

## 7. Citation contract

For any tool with `requires_citations = True`:
- Result MUST include `sources: list[{path, line_start, line_end}]`.
- Each `path` MUST exist under `workspace/`.
- `1 <= line_start <= line_end <= file_lines`.
- `line_end - line_start <= 200` (no "everywhere" citations).
- If result includes `identifiers_mentioned`: every identifier MUST appear in the cited ranges' text.
- Empty `sources` allowed only if result has non-empty `notes` explaining (e.g. "0 results matched filters").

Enforcement: `src/mcp/middleware/citation.py:enforce_citations()`.
