# Docker Runtime Reference

Use this reference when running the Smart Agriculture stack in Docker mode on the maintainer machine.

## Canonical Paths

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Docker compose file: `infra/docker/docker-compose.yml`
- Env file: `.env` (repo root)
- Frontdoor script: `/Users/mac/.doc-cloud/bin/run-smart-agriculture-frontdoor.sh`
- Frontdoor nginx config: `/Users/mac/.doc-cloud/config/ai-luyaxiang-smart-agriculture.nginx.conf`

## Port Map in Docker Mode

| Service | Host port | Container-internal | Notes |
|---------|-----------|--------------------|-------|
| Next web | 18030 | 3000 | Same host port as process mode |
| Python Agent | 18010 | 8000 | Same host port as process mode |
| MySQL | 3306 | 3306 | Shared container |
| Redis | 6379 | 6379 | Shared container |
| Frontdoor nginx | 5173 | — | Shared, do not restart |

> Host-facing ports are unified across both modes: **web `18030`, agent `18010`**.
> Inside the containers the servers still bind `3000`/`8000`; docker-compose publishes
> them on `18030`/`18010`.

## Domain Chain

1. `cloudflared`
2. `nginx` on `127.0.0.1:5173` → `proxy_pass 127.0.0.1:18030`
3. Docker web container published on host `127.0.0.1:18030` (internal `3000`)
4. Docker agent container published on host `127.0.0.1:18010` (internal `8000`)

## Key Differences from Process Mode

- Host ports are identical to process mode (web `18030`, agent `18010`); only the
  container-internal ports differ (`3000`/`8000`).
- From the host, smoke-test the published ports `18030`/`18010` — not `3000`/`8000`.
- Dependencies are built inside containers — no manual `npm install` or `pip install`.

## Important Notes

- `ai.luyaxiang.com` is the correct domain. Treat `ai.yaxianglu.com` as a typo.
- Do not restart `nginx` or `cloudflared` — they are shared infrastructure.
- Always run a login + chat smoke test after deployment; `/api/health` alone is not enough.
