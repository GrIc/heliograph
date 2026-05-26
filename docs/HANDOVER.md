# Heliograph — Handover / Onboarding

> Read this first. Then `docs/index.md`. Then jump into code.

This document gives you everything to run, debug, extend, and maintain Heliograph without needing the original author. Target audience: a senior engineer who has never seen the codebase.

---

## 1. What this is in 60 seconds

Heliograph is a self-hosted **MCP server** that indexes a codebase into three complementary stores (vector / graph / temporal) and exposes that knowledge as **typed tools with mandatory source-line citations** to AI coding agents (Roo Code, Cursor, Claude Code, Continue, Cline).

It is **not** an editor, not a code reviewer, not a SaaS. It is a context provider.

---

## 2. Setup from scratch — first run in 15 minutes

### 2.1 Prerequisites

- Docker + Docker Compose
- Git
- Access to an OpenAI-compatible LLM endpoint (OpenAI, Mistral, vLLM, Ollama, Azure, LiteLLM…)
- A codebase to index (10k – 10M LOC)

### 2.2 Clone and configure

```bash
git clone https://github.com/GrIc/heliograph.git
cd heliograph
cp .env.example .env
$EDITOR .env        # set API_BASE_URL + API_KEY
```

Key environment variables (`.env`):

| Var | Meaning |
|---|---|
| `API_BASE_URL` | LLM endpoint, e.g. `https://api.openai.com/v1` |
| `API_KEY` | LLM key |
| `MODEL_HEAVY` | reasoning model (e.g. `gpt-4o`, `claude-opus-4-7`) |
| `MODEL_CODE` | code-specialized model |
| `MODEL_LIGHT` | fast model for light tasks |
| `MODEL_EMBED` | embedding model (e.g. `text-embedding-3-small`) |
| `MCP_BEARER_TOKEN` | optional; required if `mcp.auth.enabled: true` |

### 2.3 Link the codebase

```bash
ln -s /absolute/path/to/your/codebase workspace
```

Symlink is preferred — keeps Heliograph repo separate from the indexed code.

### 2.4 First indexing pass

```bash
docker compose up -d                      # bring up the web + indexer
docker compose exec web python -m src.main scan       # codex L3 docs
docker compose exec web python synthesize.py          # L0/L1/L2 pyramid
docker compose exec web python build_graph.py         # AST + knowledge graph
docker compose exec web python -m src.temporal.run_changelog  # changelog
```

First scan time depends on the codebase size and LLM speed. Plan for ~1s per file on a fast LLM, more on slow ones. A 5k-file Python repo takes ~1h.

### 2.5 Verify

```bash
curl -s http://localhost:8080/healthz                       # OK
curl -s http://localhost:8080/api/stats | jq .             # chunks > 0
curl -s http://localhost:8080/mcp/sse                       # SSE handshake
```

Open `http://localhost:8080/debug/chat` for the debug UI.

### 2.6 Wire a client

Pick one:

- **Roo Code**: see `docs/clients/roo-code.md`
- **Cursor**: see `docs/clients/cursor.md`
- **Continue.dev**: see `docs/clients/continue.md`
- **Cline**: see `docs/clients/cline.md`
- **Claude Code**: see `docs/clients/claude-code.md` (stdio transport)

Endpoint: `http://localhost:8080/mcp/sse` for SSE clients, `python -m src.mcp.server` for stdio.

---

## 3. Repo map — where things live

```
heliograph/
├── src/
│   ├── mcp/                  # MCP server + framework
│   │   ├── base.py           # BaseTool ABC, ToolError, validation pipeline
│   │   ├── registry.py       # auto-discovers BaseTool subclasses
│   │   ├── server.py         # FastAPI/stdio entry, mounts SSE
│   │   ├── transports/       # sse.py, stdio.py
│   │   ├── middleware/       # auth, rate_limit, citation, logging
│   │   └── tools/            # one file = one tool. Edit here to add a tool.
│   ├── rag/                  # vector store + grounding + ingest
│   │   ├── store.py          # VectorStore (ChromaDB wrapper)
│   │   ├── ingest.py         # chunking + indexing pipeline
│   │   ├── grounding.py      # GROUNDING_INSTRUCTION, abstain tokens
│   │   ├── identifiers.py    # AST-based identifier extraction (tree-sitter)
│   │   └── graph.py          # KnowledgeGraph (NetworkX) — Phase 2
│   ├── graph/                # tree-sitter parsers + extractors
│   ├── temporal/             # changelog pipeline
│   │   ├── git_client.py     # git primitives
│   │   ├── store.py          # SQLite enriched commits
│   │   ├── enricher.py       # per-commit LLM enrichment (grounded)
│   │   ├── digest.py         # daily/weekly digest renderer
│   │   ├── channels/         # file / slack / email delivery
│   │   ├── sources/          # ChangeSource ABC + GitSource + FsDiffSource
│   │   └── run_changelog.py  # CLI entrypoint
│   ├── agents/               # BaseAgent + each agent subclass
│   ├── config.py             # loads config.yaml + env interpolation
│   ├── client.py             # ResilientClient (LLM HTTP with retries)
│   └── main.py               # CLI entrypoint (scan, synthesize, etc.)
├── web/                      # FastAPI app, IDE REST, admin UI
├── scripts/                  # build_mcp_docs.py + deploy helpers
├── tests/                    # golden + integration + unit
├── docs/                     # this directory
├── workspace/                # symlink to indexed codebase
├── context/                  # generated artefacts (docs, changelog, temporal db)
├── .vectordb/                # ChromaDB persistent storage
├── .graphdb/                 # graph persistent storage
├── config.yaml               # central runtime config
├── docker-compose.yml        # default stack
└── .env                      # secrets (not committed)
```

---

## 4. The four golden rules of this codebase

1. **Tools never speak directly to clients.** They subclass `BaseTool`, return `dict`, the framework validates I/O against JSON Schema and enforces citations. If you bypass it, you break the citation contract.
2. **Citations are required for code-related responses.** If `requires_citations = True`, your handler MUST return `{"sources": [{"path", "line_start", "line_end"}, …]}` with at least one valid entry — or an empty list **plus** a non-empty `notes` field justifying why.
3. **No new pip dependencies without a PR discussion.** `requirements.txt` is intentionally lean. Adding tree-sitter or z3 is fine (they buy capabilities). Adding helpers is not.
4. **English in code and prompts. French in conversation is fine, the repo isn't.**

---

## 5. Adding a new MCP tool — the 6-step recipe

1. Create `src/mcp/tools/my_tool.py`:
    ```python
    from src.mcp.base import BaseTool, ToolError
    from src.mcp.tools._common import SOURCES_LIST_SCHEMA

    class MyTool(BaseTool):
        name = "my_tool"
        description = "What it does, in one sentence."
        input_schema = {"type": "object", "required": ["x"],
                         "properties": {"x": {"type": "string"}},
                         "additionalProperties": False}
        output_schema = {"type": "object", "required": ["sources"],
                          "properties": {"result": {"type": "string"},
                                         "sources": SOURCES_LIST_SCHEMA,
                                         "notes": {"type": "string"}},
                          "additionalProperties": False}
        requires_citations = True

        def handle(self, args: dict) -> dict:
            # ... business logic ...
            return {"result": "...", "sources": [...]}
    ```
2. Add a golden test in `tests/golden/test_mcp_tools.py` (one parametrized test that asserts schema + smoke behavior).
3. Run `PYTHONPATH=. python3 scripts/build_mcp_docs.py` to regenerate `docs/mcp/tools.md`.
4. Run `pytest tests/golden/ tests/integration/` — must stay green.
5. If your tool touches a new data store, add a `lazy_xxx()` helper in `src/mcp/tools/_common.py` (singleton pattern, lazy init, cached).
6. Submit a PR with the changelog entry (we use Conventional Commits-ish; see `git log`).

No registry edit needed — auto-discovery picks it up on next server restart.

---

## 6. Adding a new agent / system prompt

Agents live in two files:

- `agents/defs/<name>.md` — system prompt + metadata (model, temperature, peers, functional context). Markdown front-matter style.
- `src/agents/<name>.py` — Python class extending `BaseAgent` if behavior is custom. Optional: most agents reuse `BaseAgent` directly.

Then register in `config.yaml` under `agents:` if you want to override the markdown defaults at runtime.

---

## 7. How to debug

### Logs

- Server logs: `docker compose logs -f web` (structured JSON via `logging.getLogger("mcp.*")`).
- Each tool call emits one log line: `{"tool", "call_id", "duration_ms", "success", "error_code"}`.

### Trace a single MCP call

1. Set log level: `mcp.log_level: DEBUG` in `config.yaml`.
2. Restart.
3. Invoke the tool from your client.
4. Grep for the `call_id` in logs.

### Inspect the index

```bash
# Vector store stats
docker compose exec web python -c "from src.rag.store import VectorStore; s=VectorStore.from_config(); print(s.stats())"

# Graph stats
docker compose exec web python -c "from src.rag.graph import KnowledgeGraph; g=KnowledgeGraph('.graphdb'); print(g.stats())"

# Temporal store
docker compose exec web python -c "from src.temporal.store import TemporalStore; s=TemporalStore('context/temporal/store.sqlite'); print('commits:', s.commit_count(), 'enriched:', s.enriched_count())"
```

### Citation failures

If a tool keeps returning `citation_failure`, set `MCP_WORKSPACE_PATH` correctly (default: `./workspace`). The middleware verifies every cited path against this root.

### "Insufficient evidence"

Means the RAG couldn't ground the answer. Three usual causes:
1. Index is empty or stale → re-run `python -m src.main scan && python synthesize.py`.
2. The query is too specific → rephrase broader.
3. The file is excluded (see `rag.extensions` in `config.yaml`).

---

## 8. How to extend the data pipeline

| Want to | Edit |
|---|---|
| Add a language to indexing | `config.yaml: scan.extensions` + `rag.extensions` |
| Add a tree-sitter parser | `src/graph/parsers.py` + a `.scm` query in `src/graph/queries/` |
| Add a delivery channel for the changelog | Subclass `Channel` in `src/temporal/channels/`, register via `@register("name")` |
| Add a new ChangeSource (e.g. SVN, Mercurial) | Subclass `ChangeSource` in `src/temporal/sources/`, wire in `resolve_source()` |
| Change chunking | `src/rag/ingest.py` — `chunk_size`, `chunk_overlap` in config |

---

## 9. Known sharp edges

1. **`tree_sitter` may need a manual rebuild** on first install for the graph extractor. If `python build_graph.py` fails with a parser error, run `pip install --upgrade --force-reinstall tree-sitter tree-sitter-languages`.
2. **ChromaDB is a single-writer**. If you scale horizontally, only ONE replica should index. The others must be read-only (`HELIOGRAPH_READONLY=true`).
3. **`apply_deliverable` was removed in the bridge cleanup.** It generated and applied LLM-produced patches. If you need it back, reimplement as a proper `BaseTool` with `dry_run` default true.
4. **Bridge removed.** Older code referenced `AgentHubBridge` in `src/mcp/server.py`. Anything still importing it will fail. Use `src.mcp.registry.discover_tools()` and call tools directly.
5. **fs_diff source does not retain content snapshots by default.** Per-line diffs are not available for fs sources — only file lists. Set `temporal.fs_diff.keep_content_snapshots: true` (Phase 5) if you need richer diffs.

---

## 10. Where the strategy lives

- **Vision**: `docs/roadmap/STRATEGY.md` — North star, four trust pillars.
- **Roadmap**: `docs/roadmap/00_MASTER_ROADMAP.md` — phase index.
- **Phase docs**: `docs/roadmap/0X_PHASE_*.md`.
- **Architecture**: `docs/architecture/` — current implementation diagrams.
- **Decisions**: `docs/decisions/` — ADRs.

If you change architecture, add an ADR. If you change scope, update the strategy.

---

## 11. CI / testing playbook

```bash
# Fast feedback loop (no LLM, no Docker)
python3 -m pytest tests/golden/ tests/integration/ tests/test_temporal_sources.py -q

# Full suite (skips tree_sitter tests if not installed)
python3 -m pytest -q

# After changing schemas, regenerate the docs
PYTHONPATH=. python3 scripts/build_mcp_docs.py

# Verify the server boots
PYTHONPATH=. python3 -c "from src.mcp.server import create_mcp_server; print('OK')"
```

Coverage target: 70% on `src/mcp/` and `src/temporal/`. Don't aim for 90% — diminishing returns on heavily I/O-bound code.

---

## 12. Operational basics

- **Backups**: `tar -czf heliograph-backup-$(date +%Y%m%d).tar.gz .vectordb/ .graphdb/ context/`
- **Reset everything**: `rm -rf .vectordb .graphdb context/temporal/*.sqlite context/temporal/state.json` (then re-scan)
- **Healthcheck**: `curl -f http://localhost:8080/healthz`
- **Memory**: ChromaDB consumes ~500MB per 1M chunks. NetworkX graph ~100MB per 100k nodes.

---

## 13. Who to ping

Tag in commits or PRs:
- Grounding / RAG / citation contract: `kip-engineer` role
- AST / graph: `graph-engineer` role
- MCP framework / tools: `mcp-engineer` role
- Changelog / temporal: `roadmap-executor` role
- Verification / Phase 6: `verifier-engineer` role (future)

These are role names, not necessarily individuals. Use the role to scope the review.

---

## 14. The "I want to ship a fix in 1h" checklist

- [ ] Identify which tool / module is involved (`git log -p` + `docs/architecture/mcp_tools_v2.md`)
- [ ] Reproduce locally (use the debug chat or `pytest -k <pattern>`)
- [ ] Fix in the smallest possible scope
- [ ] Add or update one test
- [ ] `pytest tests/golden/ tests/integration/` green
- [ ] Regenerate `docs/mcp/tools.md` if schemas changed
- [ ] Commit with Conventional Commits prefix (`fix:`, `feat:`, `refactor:`)
- [ ] PR with: what / why / tradeoffs

---

*Good luck. The code is honest with you — if something looks weird, it probably is. Don't paper over it. Ask in a PR.*
