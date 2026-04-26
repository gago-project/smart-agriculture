---
name: deploy
description: Use when updating and deploying Smart Agriculture in process mode (node + uvicorn) on the maintainer machine. Always uses process mode — never Docker.
---

# Smart Agriculture Process Mode Deploy Workflow

## Overview

Deploy the Smart Agriculture stack in process mode. This skill always uses `start-local-agent.sh` and `start-local-web.sh` — never Docker. If Docker containers are running for this project, stop them first.

Read [`references/current-runtime.md`](./references/current-runtime.md) before touching live services.

## Workflow

### 1. Inspect the current state

- Run `git status`, `lsof -nP -iTCP -sTCP:LISTEN`, `ps auxww`, and `docker ps`.
- Note any Docker containers for this project that may conflict.
- Note which process-mode services are already running.

### 2. Stop Docker containers if running

If `smart-agriculture-web` or `smart-agriculture-agent` containers are running, stop them first:

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml stop agent web
```

Never stop `cloudflared`, `nginx`, or unrelated containers.

### 3. Update code safely

- Work inside `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`.
- Check for local uncommitted changes before `git pull`.
- If dependencies changed:
  - Web: `npm --prefix apps/web install`
  - Agent: `npm run setup:agent`
- Rebuild web before restart: `npm run build:web`

### 4. Restart process-mode services

- Agent:
  - Read `.runtime/local-agent-port` to confirm the target port (default `18010`).
  - Find the existing `uvicorn app.main:app` process owned by this repo.
  - Kill only that process.
  - Restart with `bash scripts/dev/start-local-agent.sh`
- Web:
  - Find the existing `next-server` / `.next/standalone/server.js` process on port `3000`.
  - Kill only that process.
  - Restart with `bash scripts/dev/start-local-web.sh`
- Never kill `cloudflared`, `nginx`, or unrelated Python services on other ports.

### 5. Verify localhost first, then the domain

- Local health:
  - `curl http://localhost:3000/api/health`
  - `curl http://localhost:${LOCAL_AGENT_PORT}/health`
  - login + `POST /api/agent/chat` smoke
- Domain health:
  - `curl https://ai.luyaxiang.com/api/health`
  - login + `POST https://ai.luyaxiang.com/api/agent/chat` smoke
- Do not stop at `/api/health`. The chat smoke is the real release gate.

## Quick Reference

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Agent port: `.runtime/local-agent-port`, default `18010`
- Start agent: `bash scripts/dev/start-local-agent.sh`
- Start web: `bash scripts/dev/start-local-web.sh`
- Local web health: `http://localhost:3000/api/health`
- Live web health: `https://ai.luyaxiang.com/api/health`

## Common Mistakes

- Assuming `ai.yaxianglu.com` is the correct domain. Use `ai.luyaxiang.com`.
- Forgetting to stop Docker containers before starting process mode (port conflicts on `3000`).
- Trusting `/api/health` without running login + chat smoke.
- Restarting `nginx` or `cloudflared` when only `3000` or `18010` needs refresh.

## Escalation Guide

- If `start-local-web.sh` fails with port conflict, a Docker web container may still be running. Stop it first.
- If the agent doesn't start, check `.runtime/local-agent-port` and the script logs.
- If the runtime mode is ambiguous, show the user concrete evidence (ports, PIDs, `docker ps`) and confirm before proceeding.
