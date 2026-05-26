# Heliograph — Deployment Guide

This guide covers deploying Heliograph in production environments using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- Git
- SSH access to target machine (if deploying remotely)
- Sufficient disk space for codebase indexing (~500MB per 1M LOC)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/youruser/heliograph.git
cd heliograph
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API credentials
```

### 3. Deploy

```bash
# Web-only deployment (no IDE integration)
./scripts/deploy.sh setup
./scripts/deploy.sh start

# With Open WebUI (IDE integration)
docker compose --profile ui up -d --build
```

### 4. Verify

```bash
# Health check
curl http://localhost:8080/healthz

# Check services
./scripts/deploy.sh status

# View logs
docker compose logs -f web
```

## Deployment Modes

### Mode 1: Web-Only (Recommended for Production)

Single container serving all interfaces:
- Web UI at `/debug/chat`
- `/v1/*` API endpoints
- `/mcp/sse` MCP server

**Services:**
- `heliograph-web`: Main service with all components
- `heliograph-indexer`: Periodic indexer (optional)

**Configuration:**
```bash
docker compose up -d
```

### Mode 2: Web + Open WebUI

Add Open WebUI as a chat frontend:

**Services:**
- `heliograph-web`: Main service
- `heliograph-indexer`: Indexer
- `open-webui`: Chat frontend

**Configuration:**
```bash
docker compose --profile ui up -d --build
```

Open WebUI will be available at `http://localhost:3000`


## Configuration

### Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `API_BASE_URL` | Yes | OpenAI-compatible endpoint (e.g., `https://api.openai.com/v1`) |
| `API_KEY` | Yes | API key for the LLM provider |
| `WORKSPACE_PATH` | No | Path to codebase (default: `./workspace`) |
| `CHROMADB_PATH` | No | Path to ChromaDB storage (default: `./.vectordb`) |
| `GRAPHDB_PATH` | No | Path to knowledge graph storage (default: `./.graphdb`) |

**Example:**
```bash
API_BASE_URL=https://api.openai.com/v1
API_KEY=sk-your-api-key-here
WORKSPACE_PATH=/opt/codebases/my-project
CHROMADB_PATH=/var/lib/heliograph/.vectordb
```

### Application Configuration (config.yaml)

See [`config.yaml`](config.yaml) for full configuration reference. Key sections:

```yaml
models:
  heavy: gpt-4o
  code: gpt-4o
  light: gpt-4o-mini
  embed: text-embedding-3-small
  rerank: ""

rag:
  rerank_top_k: 8
  hierarchical_search: true

graph:
  enabled: false
  persist_dir: .graphdb
```

## Scaling

### Horizontal Scaling

Heliograph supports horizontal scaling by sharing volumes between containers:

```bash
# Container 1
services:
  heliograph-web:
    volumes:
      - ./workspace:/app/workspace:ro
      - ./.vectordb:/app/.vectordb
      - ./.graphdb:/app/.graphdb

# Container 2 (read replica)
services:
  heliograph-web-replica:
    volumes:
      - ./workspace-replica:/app/workspace:ro
      - ./.vectordb:/app/.vectordb:ro
```

**Note:** ChromaDB supports concurrent readers but requires a single writer.

### Load Balancing

For high availability, use a load balancer in front of multiple Heliograph instances:

```
Load Balancer → Heliograph 1 (:8080)
              → Heliograph 2 (:8080)
              → Heliograph 3 (:8080)
```

**Health check endpoint:** `/healthz` returns 200 when ready

### Indexer Scaling

The indexer can run as a separate service:

```yaml
services:
  heliograph-indexer:
    image: heliograph
    command: ["python", "watch.py", "--continuous"]
    volumes:
      - ./workspace:/app/workspace
      - ./.vectordb:/app/.vectordb
      - ./.graphdb:/app/.graphdb
    environment:
      - API_BASE_URL=${API_BASE_URL}
      - API_KEY=${API_KEY}
```

## Persistent Storage

Heliograph uses three persistent volumes:

| Volume | Purpose | Size |
|--------|---------|------|
| `.vectordb/` | ChromaDB vector store | 500MB–5GB+ |
| `.graphdb/` | Knowledge graph | 100MB–2GB+ |
| `workspace/` | Codebase (read-only) | Depends on codebase |
| `context/` | Generated documentation | 100MB–1GB+ |
| `projects/` | Project data | 10MB–1GB+ |

**Backup Strategy:**
```bash
# Backup all volumes
tar -czf heliograph-backup-$(date +%Y%m%d).tar.gz .vectordb/ .graphdb/ context/ projects/

# Restore
mkdir -p .vectordb .graphdb context projects
tar -xzf heliograph-backup-20240421.tar.gz
```

## Security

### Network Security

- Bind to `0.0.0.0` for external access (not `127.0.0.1`)
- Use HTTPS in production (via reverse proxy)
- Restrict access to `/v1/*` and `/mcp/sse` endpoints

**Example Nginx configuration:**
```nginx
server {
    listen 443 ssl;
    server_name heliograph.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Authentication

- MCP tools require explicit client authorization
- `/v1/*` endpoints validate model names strictly (`expert-rag` only)
- No built-in user authentication (relies on MCP client authentication)

### File Access

- `read_file`/`edit_file` tools respect workspace boundaries
- Only files in `workspace/` are accessible
- No access to system files or other directories

## Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8080/healthz

# Expected response: "OK" with 200 status
```

### Metrics

Heliograph exposes basic metrics via `/api/stats`:

```bash
curl http://localhost:8080/api/stats
```

**Response:**
```json
{
  "total_queries": 125,
  "total_tokens_est": 45000,
  "queries_by_day": {
    "2024-04-20": 45,
    "2024-04-21": 80
  },
  "errors": 2,
  "index_size": 1250,
  "active_sessions": 5
}
```

### Logging

Heliograph logs to stdout/stderr:

```bash
# View web service logs
docker compose logs -f web

# View indexer logs
docker compose logs -f indexer

# View Open WebUI logs (if using)
docker compose logs -f open-webui
```

**Log format:** JSONL per day in `web/logs/`

## Maintenance

### Updating Heliograph

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
./scripts/deploy.sh setup
./scripts/deploy.sh start
```

### Reindexing

To rebuild the entire index:

```bash
./scripts/deploy.sh reset-index
```

**Note:** This clears `.vectordb/` and rebuilds from scratch


### Clearing Cache

```bash
# Clear ChromaDB index
docker compose exec web python run.py --clear-index

# Clear generated documentation
docker compose exec web rm -rf context/docs/*
```

## Troubleshooting

### Service won't start

1. Check logs: `docker compose logs web`
2. Verify .env is configured: `docker compose config`
3. Check port availability: `netstat -ano | findstr 8080` (Windows) or `lsof -i :8080` (macOS/Linux)
4. Verify disk space: `df -h`


### High memory usage

1. Check memory: `docker stats heliograph-web`
2. Reduce `rerank_top_k` in config.yaml
3. Use lighter models in config.yaml
4. Consider scaling horizontally

### Slow queries

1. Check index status: `curl http://localhost:8080/api/stats`
2. Verify ChromaDB is indexed: `ls -la .vectordb/`
3. Increase `rerank_top_k` for better results (but slower queries)
4. Use lighter models for quick lookups

### ChromaDB corruption

1. Stop services: `docker compose down`
2. Backup and remove corrupted index: `mv .vectordb .vectordb-corrupt`
3. Rebuild index: `docker compose up -d && ./scripts/deploy.sh reset-index`

## CI/CD Integration

Heliograph includes a GitLab CI configuration (`.gitlab-ci.yml`).


### Required CI/CD Variables

| Variable | Description |
|----------|-------------|
| `REGISTRY_URL` | Docker registry URL |
| `REGISTRY_USER` | Registry username |
| `REGISTRY_PASSWORD` | Registry password |
| `DEPLOY_HOST` | Target machine hostname |
| `DEPLOY_USER` | SSH user on target |
| `DEPLOY_SSH_KEY_B64` | Base64-encoded SSH key |
| `DEPLOY_PATH` | Path to cloned repo on target |

### Manual Deployment

The CI/CD pipeline is configured for manual deployment:

```bash
# After successful build
./scripts/deploy.sh update
```

## Performance Tuning

### ChromaDB Optimization

```yaml
# In config.yaml
rag:
  rerank_top_k: 12  # Default: 8, higher = better results but slower
  hierarchical_search: true  # Enable L0→L3 search
```

### Model Configuration

```yaml
models:
  heavy: gpt-4o  # Best for complex queries
  code: gpt-4o   # Code-specific
  light: gpt-4o-mini  # Fast/cheap for quick lookups
  embed: text-embedding-3-small  # Embeddings model
```

### Resource Limits

For production, set resource limits in `docker-compose.yml`:

```yaml
services:
  heliograph-web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Backup and Recovery

### Backup Strategy

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups/heliograph
mkdir -p $BACKUP_DIR

date=$(date +%Y%m%d)

# Backup volumes
tar -czf $BACKUP_DIR/heliograph-$date.tar.gz \
  .vectordb/ \
  .graphdb/ \
  context/ \
  projects/

# Keep last 7 days
find $BACKUP_DIR -name "heliograph-*.tar.gz" -mtime +7 -delete
```

### Recovery

```bash
# Stop services
docker compose down

# Restore from backup
rm -rf .vectordb .graphdb context projects
mkdir -p .vectordb .graphdb context projects
tar -xzf /backups/heliograph/heliograph-20240421.tar.gz

# Restart
docker compose up -d
```

## Support

- **Documentation**: https://github.com/GrIc/heliograph/tree/main/docs
- **Issues**: https://github.com/GrIc/heliograph/issues
- **Discussions**: https://github.com/GrIc/heliograph/discussions

---

**Next:** [Scaling Guide](scale.md) | [Troubleshooting Guide](troubleshoot.md)
