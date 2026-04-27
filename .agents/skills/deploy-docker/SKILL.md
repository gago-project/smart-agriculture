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

### 3.5 DB Sync（Docker 启动前必须执行）

**在 Docker 容器启动之前**，先把本地开发的 schema 变更和种子数据同步到 Docker MySQL，确保新容器启动时看到的数据库结构与代码一致。

完整逻辑见 `.Codex/skills/db-sync/SKILL.md`，deploy 阶段标准执行：前置读取连接信息 → 场景一（Schema）→ 场景二（种子数据）→ 场景三（Auth 用户，若文件存在）。

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
source scripts/dev/load-root-env.sh

MYSQL_HOST_SYNC=127.0.0.1
MYSQL_PORT_SYNC=${MYSQL_PORT:-3306}
MYSQL_DB=${MYSQL_DATABASE:-smart_agriculture}
MYSQL_USER_SYNC=${MYSQL_APPLY_USER:-${MYSQL_USER:-root}}
MYSQL_PWD_SYNC=${MYSQL_APPLY_PASSWORD:-${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}}

snapshot_counts() {
  MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
    -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
    --skip-column-names -s 2>/dev/null \
    -e "USE \`$MYSQL_DB\`;
        SELECT
          COALESCE((SELECT COUNT(*) FROM fact_soil_moisture),0),
          COALESCE((SELECT COUNT(*) FROM auth_user),0),
          COALESCE((SELECT COUNT(*) FROM region_alias),0),
          COALESCE((SELECT COUNT(*) FROM metric_rule),0),
          COALESCE((SELECT COUNT(*) FROM warning_template),0),
          COALESCE((SELECT COUNT(*) FROM auth_session),0);"
}

print_summary() {
  local label="$1" before="$2" after="$3"
  IFS=$'\t' read -r b_soil b_user b_alias b_rule b_tmpl b_sess <<< "$before"
  IFS=$'\t' read -r a_soil a_user a_alias a_rule a_tmpl a_sess <<< "$after"
  row() { local d=$(($2-$1)); [ $d -gt 0 ] && printf "%s → %s  (+%s 行)" $1 $2 $d || [ $d -lt 0 ] && printf "%s → %s  (%s 行)" $1 $2 $d || printf "%s" $2; }
  echo ""; echo "════════ DB Sync Summary — ${label} ════════"
  printf "  %-22s %s\n" "fact_soil_moisture"  "$(row $b_soil  $a_soil)"
  printf "  %-22s %s\n" "auth_user"           "$(row $b_user  $a_user)"
  printf "  %-22s %s\n" "region_alias"        "$(row $b_alias $a_alias)"
  printf "  %-22s %s\n" "metric_rule"         "$(row $b_rule  $a_rule)"
  printf "  %-22s %s\n" "warning_template"    "$(row $b_tmpl  $a_tmpl)"
  echo "═══════════════════════════════════════════"
}

# 场景一：Schema
BEFORE=$(snapshot_counts)
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 < infra/mysql/init/001_init_tables.sql
AFTER=$(snapshot_counts)
print_summary "Schema (001)" "$BEFORE" "$AFTER"

# 场景二：种子数据
BEFORE=$(snapshot_counts)
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 < infra/mysql/init/002_insert_data.sql
AFTER=$(snapshot_counts)
print_summary "种子数据 (002)" "$BEFORE" "$AFTER"

# 场景三：Auth 用户（仅当文件存在时）
LOCAL_AUTH_JSON="${LOCAL_AUTH_USERS_JSON:-infra/mysql/local/auth_users.local.json}"
if [ -f "$LOCAL_AUTH_JSON" ]; then
  BEFORE=$(snapshot_counts)
  MYSQL_HOST=$MYSQL_HOST_SYNC MYSQL_PORT=$MYSQL_PORT_SYNC \
  MYSQL_DATABASE=$MYSQL_DB MYSQL_USER=$MYSQL_USER_SYNC \
  MYSQL_PASSWORD=$MYSQL_PWD_SYNC \
  LOCAL_AUTH_USERS_JSON="$LOCAL_AUTH_JSON" \
  node apps/web/scripts/seed-local-auth-users.mjs
  AFTER=$(snapshot_counts)
  print_summary "Auth 用户" "$BEFORE" "$AFTER"
fi
```

> **不需要执行：** `--soil`（003 太慢）、`--flush-redis`（会话应跨 deploy 保留）。

### 4. Start the Docker stack

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml up -d --build agent web
```

- After start, verify containers are healthy:

```bash
docker compose --env-file .env -f infra/docker/docker-compose.yml ps
```

- In Docker mode, the agent is on port `8000`, not `18010`.

### 5. 验活（本地 → 域名，完整三步）

完整验活逻辑见 `.Codex/skills/local-health/SKILL.md`，此处内联标准流程：

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
source scripts/dev/load-root-env.sh

# Docker 模式：agent 固定在 8000
BASE_WEB_LOCAL="http://localhost:3000"
BASE_AGENT_LOCAL="http://localhost:8000"
HEALTH_USERNAME=${HEALTH_USERNAME:-gago-admin}

if [ -z "${HEALTH_PASSWORD:-}" ]; then
  echo "❌ 缺少 HEALTH_PASSWORD，请检查 .env 或 Keychain"; exit 1
fi

smoke_test() {
  local base_web=$1 base_agent=$2 label=$3
  echo ""; echo "══ 验活：${label} ══"

  echo "[1/3] web health"
  curl -fsS "$base_web/api/health" | python3 -m json.tool

  echo "[2/3] agent health"
  curl -fsS "$base_agent/health" | python3 -m json.tool

  echo "[3/3] chat smoke"
  AUTH_TOKEN=$(curl -fsS -X POST "$base_web/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$HEALTH_USERNAME\",\"password\":\"$HEALTH_PASSWORD\"}" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')
  [ -z "$AUTH_TOKEN" ] && echo "❌ 登录失败" && return 1
  curl -fsS -X POST "$base_web/api/agent/chat" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -d '{"question":"最近墒情怎么样","thread_id":"health-check","history":[]}' \
    | python3 -m json.tool
  echo "  ✓ ${label} 验活通过"
}

# 本地验活
smoke_test "$BASE_WEB_LOCAL" "$BASE_AGENT_LOCAL" "localhost (Docker)"

# 域名验活（agent 经由 web BFF 代理，不直接暴露）
smoke_test "https://ai.luyaxiang.com" "https://ai.luyaxiang.com" "ai.luyaxiang.com"
```

> **chat smoke 是真正的发布门禁**，不能只看 `/api/health` 就算完成。

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
