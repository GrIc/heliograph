# OpenCode — connect to Heliograph

[OpenCode](https://opencode.ai) is an open-source terminal AI coding agent
(SST). It speaks MCP natively and supports both remote (SSE/HTTP) and local
(stdio) MCP servers.

Heliograph exposes both transports, so no code change is required — only a
config entry in OpenCode.

---

## Option A — remote (SSE) — recommended

Use when Heliograph runs as a long-lived service (Docker, systemd, etc.).

### 1. Start Heliograph

```bash
docker compose up -d
# Endpoint should be reachable: http://localhost:8080/mcp/sse
curl -sf http://localhost:8080/mcp/sse -o /dev/null && echo ok
```

### 2. Add the MCP entry in your OpenCode config

OpenCode reads `opencode.json` from (in order):
1. `./opencode.json` (project-scoped, preferred for per-repo setup)
2. `~/.config/opencode/opencode.json` (user-global)

Merge the following into the `mcp` block:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "heliograph": {
      "type": "remote",
      "url": "http://localhost:8080/mcp/sse",
      "enabled": true
    }
  }
}
```

A ready-to-copy file ships at [`opencode-sse.json`](../../opencode-sse.json)
in the repo root.

### 3. Use it

```bash
opencode                                  # interactive TUI
# Or one-shot:
opencode run "Use heliograph to list the MCP tools available"
```

OpenCode lists discovered MCP tools at startup. Each Heliograph tool appears
as `heliograph_<tool_name>`. Reference them naturally in your prompts.

---

## Option B — local (stdio)

Use when you want OpenCode to spawn Heliograph as a subprocess — no port, no
Docker, lifecycle bound to the OpenCode session.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "heliograph": {
      "type": "local",
      "command": ["python", "-m", "src.mcp.transports.stdio"],
      "enabled": true,
      "environment": {
        "PYTHONPATH": "/absolute/path/to/heliograph"
      }
    }
  }
}
```

Ready-to-copy: [`opencode-stdio.json`](../../opencode-stdio.json).

Requires: Python venv with Heliograph deps installed, and `.env` set up at
the path referenced by `PYTHONPATH`.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `heliograph` tools missing from OpenCode startup banner | `opencode mcp list` — should show `heliograph: connected`. If not, run `opencode --print-logs` and look for MCP init errors. |
| SSE: `connection refused` | `docker compose ps`; verify port 8080 not taken; try `curl http://localhost:8080/mcp/sse`. |
| stdio: `ModuleNotFoundError: src.mcp.transports.stdio` | `cwd` / `PYTHONPATH` wrong. Use absolute paths. |
| Tools respond but answers empty | Index not built yet. `./scripts/index.sh` or wait for `watch.py` to catch up. |

---

## Notes

- OpenCode supports both the older `command` array style and the newer
  HTTP/SSE remote transport. Heliograph works with both — pick based on
  whether you want a service (SSE) or a subprocess (stdio).
- Citations returned by Heliograph appear as plain JSON in the tool result;
  OpenCode's TUI renders them as clickable references when the path is
  recognized.
- For an OpenCode-specific permissions config (allow/deny per Heliograph
  tool), use OpenCode's `permission` section — Heliograph itself doesn't
  enforce client-side permissions.
