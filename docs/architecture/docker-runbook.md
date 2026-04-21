# Docker Runbook

## Start

```bash
cd ${GAGO_CLOUD_ROOT}/code/smart-agriculture
cp .env.example .env
# Fill QWEN_API_KEY and SONIOX_API_KEY in .env when available.
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
```

Open:

- Web: http://localhost:3000
- Chat: http://localhost:3000/chat
- Admin: http://localhost:3000/admin
- Agent health: http://localhost:8000/health

## Validate

```bash
bash scripts/health/check-local.sh
PYTHONPATH=apps/agent python -m unittest discover -s apps/agent/tests -p '*_unittest.py' -v
```

## Stop

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml down
```

## Reset Local Data

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml down -v
rm -rf mysql-data redis-data
```
