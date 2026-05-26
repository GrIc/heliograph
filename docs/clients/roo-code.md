# Heliograph — Roo Code Integration Guide

Roo Code is an AI coding assistant that works inside VS Code. To use Heliograph with Roo Code, you need to configure Roo Code to connect to Heliograph's MCP server and use Heliograph as your LLM provider.

## Prerequisites

- Roo Code extension installed in VS Code
- Heliograph running (`docker compose up -d` or `python -m web.server`)
- Heliograph accessible at `http://localhost:8080`

## Configuration Steps

### Step 1: Configure LLM Provider

Roo Code needs to use Heliograph as an OpenAI-compatible LLM provider.

1. Open VS Code settings (`Ctrl+,`)
2. Search for "Roo Code: Model Provider"
3. Select "OpenAI Compatible" from the dropdown

4. Configure the provider with these settings:

| Setting | Value |
|---------|-------|
| Base URL | `http://localhost:8080/v1` |
| API Key | *(your `API_KEY` from `.env`)* |
| Model | `expert-rag` |

**Alternative:** Edit your VS Code `settings.json` directly:

```json
{
  "roo.modelProvider": "openai-compatible",
  "roo.openAiCompatible.baseUrl": "http://localhost:8080/v1",
  "roo.openAiCompatible.apiKey": "your-api-key-here",
  "roo.model": "expert-rag"
}
```

### Step 2: Configure MCP Tools

Roo Code uses MCP tools for agentic tasks. Add Heliograph as an MCP server:

1. Open VS Code settings (`Ctrl+,`)
2. Search for "Roo Code: MCP Servers"
3. Add the following configuration:

```json
{
  "mcpServers": {
    "heliograph": {
      "type": "sse",
      "url": "http://localhost:8080/mcp/sse"
    }
  }
}
```

**Alternative:** Edit your VS Code `settings.json` directly:

```json
{
  "mcpServers": {
    "heliograph": {
      "type": "sse",
      "url": "http://localhost:8080/mcp/sse"
    }
  }
}
```

### Step 3: Restart Roo Code

After saving the configuration, restart Roo Code for the changes to take effect.

## Using Heliograph with Roo Code

### Chat Mode

Roo Code chat uses Heliograph's RAG-augmented expert agent:

```
> Explain how the authentication system works
> What are the main components of the backend API?
> How do I add a new endpoint to the user service?
```

All chat messages go through Heliograph's full hybrid search pipeline (RAG + GraphRAG).

### Agent Mode (Tools)

Roo Code can call Heliograph tools during agentic tasks:

```
> Use expert_ask to explain the UserService class
> Search the RAG index for database migration patterns
> What does search_graph say about dependencies of UserService?
> List deliverables for project my-feature
```

**Available Tools:**
- `expert_ask` — RAG-powered code Q&A
- `search_rag` — Search the vector index directly
- `search_graph` — Entity relationships and dependency queries
- `read_file` / `edit_file` — Browse and edit workspace files
- `list_deliverables` / `read_deliverable` / `apply_deliverable` — Project deliverables
- `call_graph` — Generate call graphs
- `discover_patterns` — Discover team conventions

### Example Workflows

**Code Review:**
```
> Review the changes in my recent commit
> Use expert_ask to analyze the security implications
> Use search_graph to find all authentication-related components
> Use impact_preview to see what else might be affected
```

**Onboarding:**
```
> Explain the architecture of the backend API
> Use search_rag to find documentation about the main modules
> Use call_graph to visualize the request flow
> Use discover_patterns to understand team conventions
```

**Debugging:**
```
> The UserService is throwing a NullPointerException
> Use expert_ask with the error trace to find the root cause
> Use read_file to check the UserService implementation
> Use search_rag to find similar issues in the codebase
```

## Configuration Files

### Continue.dev Compatible Config

Roo Code uses similar configuration to Continue.dev. You can use the provided `continue-sse.yaml` file:

```bash
# Copy to your project's .continue directory
mkdir -p .continue/mcpServers
cp continue-sse.yaml .continue/mcpServers/heliograph.yaml
```

Then configure Roo Code to use this file.

## Troubleshooting

### Roo Code can't connect to Heliograph

1. Verify Heliograph is running: `curl http://localhost:8080/healthz`
2. Check the API endpoint: `curl http://localhost:8080/v1/models`
3. Verify MCP endpoint: `curl http://localhost:8080/mcp/sse`
4. Check network connectivity between Roo Code and Heliograph
5. Verify firewall settings

### "Model not found" error

1. Check available models: `curl http://localhost:8080/v1/models`
2. Verify you're using `expert-rag` (not `expert`, `documenter`, etc.)
3. Check Heliograph logs for errors

### Tools not available in Agent Mode

1. Verify MCP configuration is correct in VS Code settings
2. Check that Heliograph is configured as an MCP server
3. Restart both Roo Code and Heliograph
4. Verify tools are registered in [`src/mcp_server.py`](src/mcp_server.py)

### High latency

1. Check index status: `curl http://localhost:8080/api/stats`
2. Verify ChromaDB is indexed: `ls -la .vectordb/`
3. For large codebases, allow extra time for first query
4. Consider increasing LLM timeout in config

## Advanced Configuration

### Remote Heliograph

If Heliograph is running on a remote server:

```json
{
  "mcpServers": {
    "heliograph": {
      "type": "sse",
      "url": "http://<server-ip>:8080/mcp/sse"
    }
  },
  "roo.openAiCompatible.baseUrl": "http://<server-ip>:8080/v1"
}
```

### Custom Port

If Heliograph uses a different port:

```json
{
  "mcpServers": {
    "heliograph": {
      "type": "sse",
      "url": "http://localhost:9090/mcp/sse"
    }
  },
  "roo.openAiCompatible.baseUrl": "http://localhost:9090/v1"
}
```

### Multiple Models

You can configure multiple models in Roo Code, but only `expert-rag` will work with Heliograph:

```json
{
  "roo.model": "expert-rag",
  "roo.models": [
    {"title": "Heliograph — Expert RAG", "provider": "openai", "model": "expert-rag", "apiBase": "http://localhost:8080/v1"}
  ]
}
```

## Best Practices

1. **Use specific queries**: The more specific your query, the better Heliograph can ground the answer
2. **Check sources**: Always review the source citations provided by Heliograph
3. **Combine tools**: Use multiple Heliograph tools together for complex tasks
4. **Iterative refinement**: Start with broad queries, then refine based on results
5. **Use Agent Mode for tools**: MCP tools only work in Agent Mode, not Chat Mode

## Performance Tips

- Heliograph performs best with a pre-built index (run `python run.py --ingest` after setup)
- For large codebases, allow extra time for the first query (index loading)
- Use `search_rag` for quick lookups, `expert_ask` for complex questions
- Configure appropriate model in Roo Code settings (`expert-rag`)

## Security Considerations

- Heliograph respects workspace boundaries (only reads files in `workspace/`)
- File editing tools (`edit_file`) require explicit confirmation
- MCP tools are scoped to the configured workspace
- No telemetry

---

**See Also:**
- [Continue.dev Integration Guide](continue.md)
- [Cline Integration Guide](cline.md)
- [Claude Code Integration Guide](claude-code.md)
- [Cursor Integration Guide](cursor.md)
- [MCP Tools Reference](../mcp/tools.md)
