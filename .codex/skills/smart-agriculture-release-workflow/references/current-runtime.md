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
3. Next web on `127.0.0.1:3000`
4. Python Agent on `127.0.0.1:18010` by default

`ai.luyaxiang.com` is the correct domain. Treat `ai.yaxianglu.com` as a typo unless the user explicitly says otherwise.

## Important Runtime Notes

- Do not assume Docker is live just because `infra/docker/docker-compose.yml` exists.
- Check actual listeners before restarting anything:
  - Web: port `3000`
  - Frontdoor nginx: port `5173`
  - Agent: `.runtime/local-agent-port`, usually `18010`
- `scripts/health/check-local.sh` prefers `.runtime/local-agent-port`. If the user is intentionally running Docker and the agent is on `8000`, set `BASE_AGENT=http://localhost:8000`.
- A green `/api/health` on the domain only proves the web layer is healthy. Always run a login + chat smoke test to verify the full chain.
