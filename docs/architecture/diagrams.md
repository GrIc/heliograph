# Architecture diagrams

> Mermaid sources for key Agent Hub flows. Render in any Markdown viewer with Mermaid support.

---

## 1. MCP tool call lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP Client (Roo/Cursor)
    participant T as Transport (SSE/stdio)
    participant A as Auth middleware
    participant R as Rate limit
    participant B as BaseTool.__call__
    participant H as handle()
    participant V as Citation enforcer
    participant L as Logging

    C->>T: JSON-RPC tools/call
    T->>A: bearer token check
    A-->>T: 401 if invalid
    T->>R: token bucket check
    R-->>T: rate_limited if over
    T->>B: invoke tool
    B->>B: jsonschema.validate(input)
    B->>H: handle(args)
    H-->>B: result dict
    B->>B: jsonschema.validate(output)
    alt requires_citations
        B->>V: enforce_citations(result)
        V-->>B: citation_failure or OK
    end
    B->>L: structured JSON log
    B-->>T: result or error envelope
    T-->>C: JSON-RPC response
```

---

## 2. Tool registry auto-discovery

```mermaid
flowchart LR
    A[python -m src.mcp.server] --> B[create_mcp_server]
    B --> C[discover_tools]
    C --> D[pkgutil.iter_modules<br/>src/mcp/tools]
    D --> E{For each module}
    E --> F[importlib.import_module]
    F --> G[inspect classes]
    G --> H{Subclass of<br/>BaseTool?<br/>not abstract?}
    H -->|Yes| I[Instantiate]
    I --> J[Validate name unique]
    J --> K[registry name → instance]
    H -->|No| E
    K --> L[Server.list_tools<br/>Server.call_tool]
```

---

## 3. Changelog dual-source pipeline

```mermaid
flowchart TD
    A[watch.py --changelog-only] --> B{resolve_source}
    B -->|.git exists| C[GitSource]
    B -->|no .git| D[FsDiffSource]
    B -->|config override| C
    B -->|config override| D

    C --> C1[git_client.new_commits_since]
    C1 --> E[ChangeSet list]

    D --> D1[Walk workspace<br/>skip patterns]
    D1 --> D2[Hash sha256<br/>compare to snapshot]
    D2 --> D3[Build ChangeSet<br/>id=fs-timestamp]
    D3 --> E

    E --> F[store.upsert_changeset<br/>SQLite]
    F --> G[enrich_pending<br/>grounded LLM]
    G --> H[digest.render_daily]
    H --> I{For each channel}
    I --> I1[file.write]
    I --> I2[slack.webhook]
    I --> I3[email.smtp]
    F --> J[source.mark_processed]
```

---

## 4. Citation enforcement

```mermaid
flowchart TD
    A[Tool result with sources] --> B{sources field<br/>present?}
    B -->|No| Z[OK — caller responsibility]
    B -->|Yes empty| F1[ERROR: empty sources]
    B -->|Yes list| C{For each source}
    C --> D{path exists in<br/>workspace?}
    D -->|No| F2[ERROR: cited path missing]
    D -->|Yes| E{1 ≤ line_start ≤<br/>line_end ≤ file_lines?}
    E -->|No| F3[ERROR: invalid range]
    E -->|Yes| G{end - start ≤ 200?}
    G -->|No| F4[ERROR: range too large]
    G -->|Yes| H{identifiers_mentioned<br/>present?}
    H -->|No| OK[OK]
    H -->|Yes| I{Each identifier<br/>in cited text?}
    I -->|No| F5[ERROR: ungrounded mention]
    I -->|Yes| OK
```

---

## 5. Phase dependency graph

```mermaid
graph TD
    P0[Phase 0 — Cleanup ✅] --> P1
    P1[Phase 1 — Grounding ✅] --> P2
    P1 --> P3
    P1 --> P4
    P2[Phase 2 — GraphRAG 🚧]
    P3[Phase 3 — Changelog 🟢<br/>+ dual source extension]
    P4[Phase 4 — MCP Tools 🟡<br/>framework done, 10/23 tools]
    P2 --> P4
    P3 --> P4
    P4 --> P5[Phase 5 — Advanced]
    P5 --> P6[Phase 6 — Verifiable<br/>autonomy v2.0]
    P6 --> P7[Phase 7 — Adaptive<br/>intelligence v3.0]
```

---

## 6. Layered knowledge model

```mermaid
flowchart LR
    subgraph workspace
        TEXT[Layer 1<br/>Raw source]
    end
    subgraph indexing
        TEXT --> CODEX[Codex L3 docs]
        CODEX --> SYNTH[Synthesize<br/>L2 → L1 → L0]
        TEXT --> AST[Tree-sitter AST]
        AST --> GRAPH[KuzuDB graph]
        TEXT --> COMMITS[Git + fs_diff]
        COMMITS --> ENRICH[Enriched commits<br/>SQLite]
    end
    subgraph runtime
        SYNTH --> CHROMA[ChromaDB<br/>vector store]
        GRAPH --> TOOLS
        ENRICH --> TOOLS
        CHROMA --> TOOLS[MCP tools]
        TOOLS --> CITE[Citation contract]
        CITE --> AGENT[AI coding agent]
    end
```
