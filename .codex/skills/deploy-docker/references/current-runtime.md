# Docker Runtime Reference

Use this reference when running the Smart Agriculture stack in Docker mode on the maintainer machine.

## Canonical Paths

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Docker compose file: `infra/docker/docker-compose.yml`
- Env file: `.env` (repo root)
- Frontdoor script: `/Users/mac/.doc-cloud/bin/run-smart-agriculture-frontdoor.sh`
- Frontdoor nginx config: `/Users/mac/.doc-cloud/config/ai-luyaxiang-smart-agriculture.nginx.conf`

## Port Map in Docker Mode

| Service | Port | Notes |
|---------|------|-------|
| Next web | 3000 | Same as process mode |
| Python Agent | 8000 | Different from process mode (18010) |
| Frontdoor nginx | 5173 | Shared, do not restart |

## Domain Chain

1. `cloudflared`
2. `nginx` on `127.0.0.1:5173`
3. Docker web container on `127.0.0.1:3000`
4. Docker agent container on `127.0.0.1:8000`

## Key Differences from Process Mode

- Agent listens on `8000`, not `18010`.
- `check-local.sh` needs `BASE_AGENT=http://localhost:8000` when Docker is active.
- Dependencies are built inside containers — no manual `npm install` or `pip install`.
- `.runtime/local-agent-port` still points to `18010`; ignore it in Docker mode.

## Important Notes

- `ai.luyaxiang.com` is the correct domain. Treat `ai.yaxianglu.com` as a typo.
- Do not restart `nginx` or `cloudflared` — they are shared infrastructure.
- Always run a login + chat smoke test after deployment; `/api/health` alone is not enough.
