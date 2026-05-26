# Heliograph — Documentation Index

> All documentation in one place. Start here.

---

## 🚀 First time here?

| Goal | Read |
|---|---|
| Understand what Heliograph is | [`../README.md`](../README.md) |
| Get up and running in 15 minutes | [`HANDOVER.md`](HANDOVER.md) §2 |
| Take ownership of the codebase | [`HANDOVER.md`](HANDOVER.md) (full) |
| Run the evaluation harness | [`../eval/README.md`](../eval/README.md) |

---

## 🏗 Architecture

| Doc | What's in it |
|---|---|
| [`architecture.md`](architecture.md) | High-level system architecture (legacy overview) |
| [`architecture/mcp_tools_v2.md`](architecture/mcp_tools_v2.md) | MCP layered architecture + tool catalog + contract |
| [`architecture/changelog_dual_source.md`](architecture/changelog_dual_source.md) | Git + filesystem-diff change sources |
| [`architecture/diagrams.md`](architecture/diagrams.md) | Mermaid diagrams (lifecycle, registry, pipeline) |

---

## 🔌 MCP tools

| Doc | What's in it |
|---|---|
| [`mcp/tools.md`](mcp/tools.md) | Auto-generated reference — every tool's schema + examples |
| [`architecture/mcp_tools_v2.md`](architecture/mcp_tools_v2.md) | Architecture, status table (real vs stub) |

Regenerate `tools.md` with: `PYTHONPATH=. python3 scripts/build_mcp_docs.py`.

---

## 🔗 Client integrations

| Client | Doc |
|---|---|
| Roo Code | [`clients/roo-code.md`](clients/roo-code.md) |
| Cursor | [`clients/cursor.md`](clients/cursor.md) |
| Continue.dev | [`clients/continue.md`](clients/continue.md) |
| Cline | [`clients/cline.md`](clients/cline.md) |
| Claude Code | [`clients/claude-code.md`](clients/claude-code.md) |
| OpenCode | [`clients/opencode.md`](clients/opencode.md) |

---

## ⚙ Operations

| Doc | What's in it |
|---|---|
| [`operations/deploy.md`](operations/deploy.md) | Docker compose + production hardening |
| [`operations/scale.md`](operations/scale.md) | Horizontal scaling, ChromaDB single-writer caveat |
| [`operations/troubleshoot.md`](operations/troubleshoot.md) | Common failure modes + fixes |

---

## 🔍 Diagnostics & audits

| Doc | What's in it |
|---|---|
| [`diagnostics/changelog_audit.md`](diagnostics/changelog_audit.md) | Original audit that motivated the Phase 3 rewrite |
| [`diagnostics/mcp_audit.md`](diagnostics/mcp_audit.md) | T-401 audit of the legacy MCP server |
| [`diagnostics/phase4_compliance_report.md`](diagnostics/phase4_compliance_report.md) | First Phase 4 review (v1) |
| [`diagnostics/phase4_compliance_report_v2.md`](diagnostics/phase4_compliance_report_v2.md) | Updated review after bridge removal + tool migration |

---

## 📜 Decisions (ADRs)

ADRs live in [`decisions/`](decisions/). Format: `NNNN-short-slug.md`. Required for any change to:

- Tool framework (BaseTool contract)
- Citation contract
- Persistence stores (ChromaDB, NetworkX, SQLite)
- Phase scope changes

---

## 🧾 Contributing

| Doc | What's in it |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Development setup + contribution guidelines |
| [`HANDOVER.md`](HANDOVER.md) §5 | How to add a new MCP tool |
| [`HANDOVER.md`](HANDOVER.md) §11 | Testing playbook |

---

## 📊 Project status (snapshot)

| Phase | State | Notes |
|---|---|---|
| 0 — Cleanup | ✅ | done |
| 1 — Grounding | ✅ | done, golden tests in place |
| 2 — GraphRAG | 🚧 | tree-sitter + topology mostly done; some languages exotic |
| 3 — Changelog | ✅ | T-301..T-308 + dual-source extension |
| 4 — MCP Tools | 🟡 | framework + **14 real tools + 4 stubs** (27 registered) |
| 5 — Advanced | 📋 | not started |
| 6 — Verifiable | 📋 | not started |
| 7 — Adaptive | 📋 | not started |

Last updated: 2026-05-25.

---

## 🆘 If something's broken

1. [`HANDOVER.md`](HANDOVER.md) §7 "How to debug"
2. [`operations/troubleshoot.md`](operations/troubleshoot.md)
3. Logs: `docker compose logs -f web`
4. Healthcheck: `curl -f http://localhost:8080/healthz`

---

*This index is the single entry point. Update it when you add new docs.*
