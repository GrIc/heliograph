# Heliograph

> MCP server that gives AI coding agents senior-engineer-level knowledge of your codebase.

Heliograph indexes a codebase (vector + AST graph + git timeline) and exposes
that knowledge through the **Model Context Protocol** to any MCP-capable AI
agent (Claude Code, Cursor, Cline, Continue.dev, Roo Code, OpenCode).

Works with any **OpenAI-compatible LLM API** — OpenAI, Mistral, vLLM, Ollama,
LiteLLM, Azure OpenAI, or any provider that exposes `/v1/chat/completions`.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## What you get

- **20 MCP tools** for code retrieval, call-graph traversal, change history,
  and module-level Q&A — each response carries `path:line_start-line_end`
  citations.
- **Hybrid retrieval** : vector search (ChromaDB) + AST knowledge graph
  (tree-sitter + NetworkX) + temporal SQLite store.
- **Auto-generated documentation pyramid** : one L3 doc per file synthesized
  upward into L2/L1/L0 architecture summaries.
- **Multi-language** : Python, Java, TypeScript, Go, Rust, and any
  language with a tree-sitter grammar.
- **Two UIs** : a built-in `/debug/chat` for quick checks, plus an optional
  **Open WebUI** for a polished multi-user chat experience.
- **Eval harness** (`eval/`) to measure Heliograph's real impact on your
  agent vs. baseline.

---

## Quick start

```bash
git clone https://github.com/GrIc/heliograph.git
cd heliograph

cp .env.example .env
$EDITOR .env                                # set API_BASE_URL + API_KEY

ln -s /path/to/your/codebase workspace      # or copy: cp -r ... workspace

./heliograph                                # docker compose up -d
./heliograph ui                             # + Open WebUI on :3000
./heliograph -h                             # see all subcommands
```

Then point your AI client at `http://localhost:8080/mcp/sse`.

Full step-by-step (including index pre-heating) : [`docs/install.md`](docs/install.md).

---

## Documentation

| Doc | Read it for |
|---|---|
| [`docs/install.md`](docs/install.md) | Install, configure, pre-heat the index |
| [`docs/usage.md`](docs/usage.md) | Day-to-day commands, every MCP tool with examples |
| [`docs/architecture.md`](docs/architecture.md) | How the indexing pipeline + tool lifecycle work |
| [`docs/clients/`](docs/clients/) | Per-client setup : Claude Code, Cursor, Continue, Cline, Roo Code, OpenCode |
| [`docs/operations/`](docs/operations/) | Deploy + troubleshoot |
| [`docs/mcp/tools.md`](docs/mcp/tools.md) | Auto-generated schema reference for every tool |
| [`eval/README.md`](eval/README.md) | Eval harness — measure real impact |

---

## License

Apache 2.0. See [`LICENSE`](LICENSE).
