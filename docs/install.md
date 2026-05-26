# Install Heliograph

This guide takes you from zero to a running Heliograph indexing your own
codebase, ready to be queried by any MCP-capable AI agent. ~15 minutes.

---

## 0. Prerequisites

- **Docker** + **Docker Compose v2** (`docker compose version` ≥ 2.20)
- **Git**
- An **OpenAI-compatible LLM endpoint** (OpenAI cloud, your own vLLM /
  Ollama / Mistral, Azure OpenAI, LiteLLM proxy, anything that speaks
  `/v1/chat/completions`)
- A **codebase to index** — any language with a tree-sitter grammar
  works. Typical size : 50k – 5M LOC.

---

## 1. Clone

```bash
git clone https://github.com/GrIc/heliograph.git
cd heliograph
```

---

## 2. Configure `.env`

```bash
cp .env.example .env
$EDITOR .env
```

Minimum to set :

```bash
API_BASE_URL=https://api.openai.com/v1
API_KEY=sk-…

# Where YOUR codebase lives on the host (Docker bind-mount target)
HOST_WORKSPACE_PATH=/absolute/path/to/your/repo

# Port for the web UI / MCP endpoint
WEB_PORT=8080

# Open WebUI (only if you run `./heliograph ui`)
OPENWEBUI_PORT=3000
OPENWEBUI_SECRET_KEY=$(openssl rand -hex 32)   # generate one
```

That's it. Everything else has sane defaults — see
[`.env.example`](../.env.example) for the full list.

> **Where does a setting live ?**
> - `.env` holds **secrets** (`API_KEY`), **host paths** (`HOST_*`),
>   **host ports** (`WEB_PORT`, `OPENWEBUI_PORT`), and the **indexer
>   interval**. That's all.
> - `config.yaml` holds **everything else** : models, retry policy,
>   agents, RAG settings, scanning rules, runtime paths.
>
> No overlap — a value lives in exactly one of the two files.

---

## 3. Configure models (optional)

`config.yaml` ships with `gpt-4o` / `gpt-4o-mini` defaults. To switch :

```yaml
# config.yaml
models:
  heavy:  mistralai/Mistral-Small-3.2-24B-Instruct-2506   # indexing + synthesis
  light:  gpt-4o-mini                                      # user-facing Q&A
  embed:  text-embedding-3-small                           # vector index
  rerank: ""                                               # optional cross-encoder
```

`heavy` is used for the expensive jobs (codex scanning, documenter
synthesis) ; `light` for fast user-facing Q&A. Cheap when shared, but
each agent can override.

---

## 4. Point a workspace at your codebase

```bash
# Symbolic link (recommended — zero copy, live updates picked up by the indexer)
ln -s /absolute/path/to/your/repo workspace

# Or, if you prefer isolation :
cp -r /absolute/path/to/your/repo workspace
```

---

## 5. Start the stack

```bash
./heliograph                # web + indexer
./heliograph ui             # + Open WebUI on :${OPENWEBUI_PORT:-3000}
./heliograph -h             # all subcommands
```

Behind the scenes that runs `docker compose up -d`, rebuilding the
image only if source files changed since the last build.

Check it's alive :

```bash
./heliograph logs              # tail web logs
curl -sf http://localhost:8080/api/stats | head
```

---

## 6. Pre-heat the index (first run)

A cold Heliograph has zero indexed content. To produce useful answers,
run the three indexing passes once. The indexer container will keep them
fresh afterwards (`INDEXER_INTERVAL_SECONDS`, default 1 h).

### 6.1 Scan + synthesize the documentation pyramid

```bash
# Inside the web container :
docker exec heliograph-web python -m src.main --ingest
```

What happens :

1. **codex** agent walks the workspace, produces one L3 doc per source
   file (`context/codex_*.md`).
2. **documenter** agent synthesizes L3 → L2 → L1 → L0 (the architecture
   overview).
3. All docs are embedded into ChromaDB (`/.vectordb`).

Time : minutes to hours, depending on codebase size and LLM throughput.
Cost : 1 LLM call per file + a few per upper level.

### 6.2 Build the AST knowledge graph (GraphRAG)

```bash
docker exec heliograph-web python build_graph.py
```

Tree-sitter parses every supported source file, extracts symbols + call
edges, and stores them as a NetworkX pickle in `/.graphdb/`.

No LLM calls — pure static analysis. Fast (seconds to minutes).

### 6.3 Bootstrap the temporal store (changelog)

```bash
docker exec heliograph-web python -m src.temporal.run_changelog
```

Ingests the last N commits (default 100, `temporal.bootstrap_commits` in
`config.yaml`), enriches each with intent + summary + risk score.

Optional. Required only if you want `recent_changes`, `blame_plus`,
`what_changed_here`, `why_does_this_exist`.

### 6.4 Verify

```bash
curl -s http://localhost:8080/api/stats
# Expect : { "chunks": <N>, "agents": 2, ... }
docker exec heliograph-web python run.py --help          # CLI help
```

Open `http://localhost:${WEB_PORT}/debug/chat`. Ask any question about
your code. Look at the citations — they should point to real file paths
+ line ranges in your workspace.

---

## 7. Connect an AI client

Pick your client, follow its guide :

| Client | Guide |
|---|---|
| Claude Code | [`docs/clients/claude-code.md`](clients/claude-code.md) |
| Cursor | [`docs/clients/cursor.md`](clients/cursor.md) |
| Continue.dev | [`docs/clients/continue.md`](clients/continue.md) |
| Cline | [`docs/clients/cline.md`](clients/cline.md) |
| Roo Code | [`docs/clients/roo-code.md`](clients/roo-code.md) |
| OpenCode | [`docs/clients/opencode.md`](clients/opencode.md) |

Endpoint to point at : `http://localhost:${WEB_PORT}/mcp/sse`.

---

## 8. Day-to-day

See [`docs/usage.md`](usage.md) for the commands you'll use repeatedly
(reindex after a big merge, inspect tools, etc.).

If things go wrong : [`docs/operations/troubleshoot.md`](operations/troubleshoot.md).
