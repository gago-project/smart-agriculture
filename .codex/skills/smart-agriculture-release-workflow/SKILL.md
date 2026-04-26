---
name: smart-agriculture-release-workflow
description: Use when updating the Smart Agriculture repository, restarting localhost services, or verifying the ai.luyaxiang.com deployment chain on the maintainer machine.
---

# Smart Agriculture Release Workflow

## Overview

Handle code updates, localhost restarts, and `ai.luyaxiang.com` verification for the current Smart Agriculture deployment topology. Treat the running topology as the source of truth; do not assume Docker is active just because the repo includes Docker files.

Read [`references/current-runtime.md`](./references/current-runtime.md) before touching live services.

## Workflow

### 1. Confirm the active runtime mode

- Run `git status`, `lsof -nP -iTCP -sTCP:LISTEN`, `ps auxww`, and `docker ps`.
- Identify whether the active release is:
  - process mode: `node` on `3000` plus `uvicorn` on `.runtime/local-agent-port`
  - docker mode: `smart-agriculture-web` and `smart-agriculture-agent` containers actually running
- Do not switch modes unless the user explicitly asks for that migration.

### 2. Update code safely

- Work inside `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`.
- Inspect for local uncommitted changes before `git pull`.
- If dependencies changed:
  - Web: `npm --prefix apps/web install`
  - Agent: `npm run setup:agent`
- Rebuild web before restart: `npm run build:web`

### 3. Restart the live process-mode services

Use this path when the machine is serving the domain through `3000 -> 5173`.

- Agent:
  - Read `.runtime/local-agent-port`
  - Find the matching `uvicorn app.main:app` process
  - Stop only the process owned by this repo
  - Restart with `bash scripts/dev/start-local-agent.sh`
- Web:
  - Find the `next-server` / `.next/standalone/server.js` process on `3000`
  - Stop only the process owned by this repo
  - Restart with `bash scripts/dev/start-local-web.sh`
- Never kill `cloudflared`, `nginx`, or unrelated Python services on other ports.

### 4. Restart the Docker stack only when Docker is the active runtime

- Use `docker compose --env-file .env -f infra/docker/docker-compose.yml up -d --build agent web`.
- After restart, verify container health with `docker compose ... ps`.
- If Docker is active, remember `check-local.sh` may need `BASE_AGENT=http://localhost:8000`.

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
- Local web health: `http://localhost:3000/api/health`
- Local agent health: `http://localhost:18010/health` by default
- Live web health: `https://ai.luyaxiang.com/api/health`
- Frontdoor nginx listens on: `127.0.0.1:5173`

## Common Mistakes

- Assuming `ai.yaxianglu.com` is the correct domain. Use `ai.luyaxiang.com`.
- Assuming Docker is live because the repo has Compose files.
- Trusting `/api/health` without running login + chat smoke.
- Restarting nginx or cloudflared when only `3000` or `18010` needs refresh.
- Forgetting that `.runtime/local-agent-port` may point `check-local.sh` at `18010` even when Docker mode uses `8000`.

## Escalation Guide

- If the user asks for a release check only, inspect and verify without restarting.
- If the user asks for a real production update, restart localhost services first because the domain frontdoor depends on them.
- If the runtime mode is ambiguous, pause and show the concrete evidence: listening ports, relevant PIDs, and `docker ps`.
