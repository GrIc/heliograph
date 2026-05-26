# Use Heliograph

Day-to-day commands and the full MCP tool reference.

---

## 1. The `./heliograph` CLI

One wrapper around `docker compose` + lifecycle. Run `./heliograph -h`
for the full list.

| Command | What it does |
|---|---|
| `./heliograph` | Start web + indexer (auto-rebuild if source changed) |
| `./heliograph ui` | + Open WebUI on `:${OPENWEBUI_PORT:-3000}` |
| `./heliograph dev` | Bind-mount source — edit code, then `./heliograph restart` |
| `./heliograph restart` | Restart the web service (dev iteration) |
| `./heliograph logs [service]` | Tail logs (default : `web`) |
| `./heliograph down` | Stop everything |
| `./heliograph clean` | Stop + drop image (forces full rebuild next time) |
| `./heliograph -h` | Show all subcommands |

---

## 2. Indexing : keep it fresh

The indexer container auto-reindexes every `INDEXER_INTERVAL_SECONDS`
(default : 1 hour). For ad-hoc passes :

```bash
# Re-document only files that changed since last scan
docker exec heliograph-web python watch.py

# Rebuild the AST graph
docker exec heliograph-web python build_graph.py

# Ingest new commits into the temporal store
docker exec heliograph-web python -m src.temporal.run_changelog

# Full re-index from scratch (drops the vector DB first)
docker exec heliograph-web python -m src.main --clear-index --ingest

# Purge entries for files that were deleted from the workspace
docker exec heliograph-web python -m src.main --purge-removed
```

`watch.py --dry-run` previews changes without writing.
`watch.py --status` shows the current hash state.

---

## 3. Two ways to chat

### Built-in debug chat
`http://localhost:${WEB_PORT}/debug/chat` — minimal, no auth, good for
quick checks while developing.

### Open WebUI (recommended for a team)
`./heliograph ui` → `http://localhost:${OPENWEBUI_PORT:-3000}`. First
user that signs up becomes admin ; signup then disabled. Default model
preselected : `expert`.

---

## 4. MCP tool reference

Every tool returns `sources: [{path, line_start, line_end}]` so the
caller can verify each claim.

### Q&A
| Tool | What it does |
|---|---|
| `ask_expert` | Free-form Q&A : RAG over the doc pyramid + vector search, returns answer + sources |
| `explain_module` | Multi-paragraph explanation of a module / package |
| `explain_change` | Plain-English summary of a commit or diff |

### Retrieval
| Tool | What it does |
|---|---|
| `find_code` | Keyword + semantic search over the vector index |
| `find_similar` | Given a file or description, returns the closest matches |
| `locate_feature` | "Where is feature X implemented ?" — ranked file list |
| `workspace_tree` | Project layout overview |
| `read_file` | Read a file from the workspace (with line range) |

### Graph (AST)
| Tool | What it does |
|---|---|
| `get_callers` | Who calls this function ? |
| `get_callees` | What does this function call ? |
| `get_module_dependencies` | Imports + exports for a module |
| `find_hub_modules` | High-degree modules (most-connected) |
| `preview_impact` | Modules affected by changing a given file |
| `search_graph` | Free-form Cypher-ish queries over the graph |

### History (temporal)
| Tool | What it does |
|---|---|
| `recent_changes` | Latest enriched commits |
| `blame_plus` | `git blame` + commit summary + risk score |
| `what_changed_here` | Recent commits touching a file or symbol |
| `why_does_this_exist` | First commit that introduced a piece of code, with its intent |

### Discovery
| Tool | What it does |
|---|---|
| `list_tools` | List every available tool with description |
| `ping` | Health + tool count |

Auto-generated schema reference (full input/output types) :
[`docs/mcp/tools.md`](mcp/tools.md). Regenerate with :

```bash
docker exec heliograph-web python scripts/build_mcp_docs.py
```

---

## 5. Asking an AI agent to use Heliograph

Once connected (`docs/clients/<your-client>.md`), just ask in natural
language. The agent picks the tool. Examples that work well :

```
Where is authentication handled in this codebase ?
What calls process_order ?
Why does retry.py use random.uniform(0, 5) on the backoff ?
What modules would I break if I change services/billing/handler.py ?
Summarize the last 10 commits on the payments service.
```

---

## 6. Tuning : what to touch when

| Want to … | Edit |
|---|---|
| Change LLM / embed / rerank | `config.yaml → models:` |
| Skip dirs from indexing | `config.yaml → scanning.skip_dirs` |
| Adjust rerank top-K | `config.yaml → rag.rerank_top_k` |
| Change indexer interval | `INDEXER_INTERVAL_SECONDS` in `.env` |
| Change ports | `WEB_PORT`, `OPENWEBUI_PORT` in `.env` |
| Adjust retry / timeout | `RETRY_*` in `.env` |

Restart after edits :

```bash
./heliograph restart       # picks up .env + config.yaml (no rebuild)
```

---

## 7. Eval : measure the impact

```bash
cd eval
./scripts/setup.sh             # one-time
./scripts/run_baseline.sh      # agent WITHOUT Heliograph
./scripts/run_with_hub.sh      # agent WITH Heliograph
./scripts/compare.sh           # markdown delta report
```

Full doc : [`eval/README.md`](../eval/README.md).
