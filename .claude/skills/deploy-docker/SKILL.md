---
name: deploy-docker
description: Use when you want to force-switch or deploy Smart Agriculture using Docker mode, regardless of the current runtime. Stops any running process-mode services first, then starts the Docker stack.
---

# Smart Agriculture Docker Deploy Workflow

## Overview

Force the Smart Agriculture stack into Docker mode. This skill always uses Docker regardless of what is currently running. It stops any live process-mode services first, then brings up the Docker stack, and verifies the full chain.

Read [`references/current-runtime.md`](./references/current-runtime.md) before touching live services.

## Workflow

### 1. Inspect the current state

- Run `git status`, `lsof -nP -iTCP -sTCP:LISTEN`, `ps auxww`, and `docker ps`.
- Note which process-mode services are running (node on 3000, uvicorn on 18010).
- Note any Docker containers already running for this project.

### 2. Stop process-mode services

Stop any process-mode services owned by this repo before starting Docker.

- Web: find the `next-server` / `.next/standalone/server.js` process on port `3000`.
  - Kill only the process owned by this repo.
- Agent: find the `uvicorn app.main:app` process on `.runtime/local-agent-port` (default `18010`).
  - Kill only the process owned by this repo.
- Never kill `cloudflared`, `nginx`, or unrelated processes.

### 3. Update code safely

- Work inside `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`.
- Check for local uncommitted changes before `git pull`.
- Dependencies are handled by the Docker build step — no need to run `npm install` manually.

### 4. Start the Docker stack

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml up -d --build agent web
```

- After start, verify containers are healthy:

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml ps
```

- In Docker mode, the agent is on port `8000`, not `18010`.

### 5. Verify localhost first, then the domain

- Local health:
  - `curl http://localhost:3000/api/health`
  - `curl http://localhost:8000/health`
  - login + `POST /api/agent/chat` smoke
- Domain health:
  - `curl https://ai.luyaxiang.com/api/health`
  - login + `POST https://ai.luyaxiang.com/api/agent/chat` smoke
- Do not stop at `/api/health`. The chat smoke is the real release gate.

## Quick Reference

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Docker compose file: `infra/docker/docker-compose.yml`
- Docker agent port: `8000`
- Docker web port: `3000`
- Health check script (Docker): `BASE_AGENT=http://localhost:8000 bash scripts/health/check-local.sh`

## Common Mistakes

- Forgetting to stop process-mode services before starting Docker (port conflicts on `3000`).
- Using `.runtime/local-agent-port` (18010) instead of `8000` when Docker is active.
- Only checking `/api/health` without running login + chat smoke.
- Restarting `nginx` or `cloudflared` — these are shared and must not be touched.
