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

### 5. 验活（本地 → 域名，完整三步）

完整验活逻辑见 `.Codex/skills/local-health/SKILL.md`，此处内联标准流程：

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
source scripts/dev/load-root-env.sh

# 进程模式：从 .runtime/local-agent-port 读端口
LOCAL_AGENT_PORT=$(cat .runtime/local-agent-port 2>/dev/null || echo "18010")
BASE_WEB_LOCAL="http://localhost:3000"
BASE_AGENT_LOCAL="http://localhost:${LOCAL_AGENT_PORT}"
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
smoke_test "$BASE_WEB_LOCAL" "$BASE_AGENT_LOCAL" "localhost"

# 域名验活（agent 经由 web BFF 代理，不直接暴露）
smoke_test "https://ai.luyaxiang.com" "https://ai.luyaxiang.com" "ai.luyaxiang.com"
```

> **chat smoke 是基础发布门禁**，不能只看 `/api/health` 就算完成。

### 6. 正式 QA 门禁（56 条全量）

发布后的最终门禁还必须跑一次正式验收库：

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
npm run qa:soil:formal
```

（分步命令与前置条件见 `.claude/skills/soil-moisture-qa/SKILL.md`「发布前正式门禁」。底层串行为 `scripts/health/check-local.sh` 与 `testdata/agent/soil-moisture/scripts/generate_formal_acceptance_report.py`。）

要求：

- 必须串行通过 `local smoke + 56 条正式 Case`
- 任一基础测试、自检或正式 Case 失败，都不能宣称发布完成
- 正式报告固定输出到 `testdata/agent/soil-moisture/outputs/formal-acceptance-report.md`

## Quick Reference

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Agent port: `.runtime/local-agent-port`, default `18010`
- Start agent: `bash scripts/dev/start-local-agent.sh`
- Start web: `bash scripts/dev/start-local-web.sh`
- Formal QA gate: `npm run qa:soil:formal`（步骤见 `soil-moisture-qa` 技能「发布前正式门禁」）
- Local web health: `http://localhost:3000/api/health`
- Live web health: `https://ai.luyaxiang.com/api/health`

## Common Mistakes

- Assuming `ai.yaxianglu.com` is the correct domain. Use `ai.luyaxiang.com`.
- Forgetting to stop Docker containers before starting process mode (port conflicts on `3000`).
- Trusting `/api/health` without running login + chat smoke.
- Stopping after smoke test without running the 56-case formal QA gate.
- Restarting `nginx` or `cloudflared` when only `3000` or `18010` needs refresh.
