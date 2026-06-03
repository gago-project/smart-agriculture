# Current Runtime Topology

Use this reference when the release task targets the maintainer machine that currently serves `ai.luyaxiang.com`.

## Canonical Paths

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Frontdoor script: `/Users/mac/.doc-cloud/bin/run-smart-agriculture-frontdoor.sh`
- Frontdoor nginx config: `/Users/mac/.doc-cloud/config/ai-luyaxiang-smart-agriculture.nginx.conf`

## Current Domain Chain

The current production-style chain on this machine is:

1. `cloudflared`
2. `nginx` on `127.0.0.1:5173`
3. Next web on `127.0.0.1:18030`
4. Python Agent on `127.0.0.1:18010` by default

`ai.luyaxiang.com` is the correct domain. Treat `ai.yaxianglu.com` as a typo unless the user explicitly says otherwise.

## Process Supervision (pm2)

The web and agent run under **pm2** as apps `sa-web` and `sa-agent` (config:
`ecosystem.config.cjs` at repo root). pm2 auto-restarts them on crash and — once
`pm2 startup` is registered — after reboot. Restarts only re-launch the already-built
servers; they never bump the version (version bumps happen only in the deploy step).

- Status: `pm2 ls` · Logs: `pm2 logs sa-web` / `pm2 logs sa-agent` (also `.runtime/logs/`)
- Redeploy: `pm2 reload ecosystem.config.cjs && pm2 save`
- Do NOT hand-kill the uvicorn/node process — pm2 will restart the old build and re-grab the port. Go through pm2.

## Important Runtime Notes

- Do not assume Docker is live just because `infra/docker/docker-compose.yml` exists.
- Check actual listeners before restarting anything:
  - Web: port `18030`
  - Frontdoor nginx: port `5173`
  - Agent: fixed `18010` (also written to `.runtime/local-agent-port`; no auto-increment — a conflict makes the agent refuse to start)
- `scripts/health/check-local.sh` prefers `.runtime/local-agent-port`. Host-facing ports are unified across process/Docker modes: web `18030`, agent `18010` (in Docker the containers bind `3000`/`8000` internally but are published on `18030`/`18010`).
- A green `/api/health` on the domain only proves the web layer is healthy. Always run a login + chat smoke test to verify the full chain.
