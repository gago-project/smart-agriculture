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

- Run `git status`, `lsof -nP -iTCP -sTCP:LISTEN`, `ps auxww`, `docker ps`, and `pm2 ls`.
- Run `pgrep -f cloudflared` to confirm the tunnel is active — domain smoke test requires it. If not running, warn before proceeding.
- Note any Docker containers for this project that may conflict.
- Note whether the `sa-agent` / `sa-web` pm2 apps are already running (they should be — pm2 supervises them). If they exist, deploy = `pm2 reload` (step 4). If pm2 has nothing, this is a first-time setup.

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

**Bump version (patch) — both files must stay in sync:**

```bash
# Guard: working tree must be clean before version bump
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ working tree 不干净，请先 commit 或 stash 再发布"
  exit 1
fi

# Read current version, increment patch, write to both apps
CURRENT=$(node -p "require('./apps/web/package.json').version")
NEW_VERSION=$(node -p "
  const [maj, min, pat] = '$CURRENT'.split('.').map(Number);
  \`\${maj}.\${min}.\${pat + 1}\`
")
echo "Bumping $CURRENT → $NEW_VERSION"

# apps/web/package.json
node -e "
  const fs = require('fs');
  const p = './apps/web/package.json';
  const pkg = JSON.parse(fs.readFileSync(p));
  pkg.version = '$NEW_VERSION';
  fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + '\n');
"

# apps/agent/pyproject.toml (replace version = "x.y.z" line)
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" apps/agent/pyproject.toml

# Commit version bump before building
git add apps/web/package.json apps/agent/pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
```

- Rebuild web after version bump: `npm run build:web`

### 4. Reload process-mode services via pm2

Services run under **pm2** (process supervisor — auto-restarts on crash/reboot). The
pm2 apps `sa-agent` and `sa-web` wrap `start-local-agent.sh` / `start-local-web.sh`,
defined in `ecosystem.config.cjs` at the repo root. **Do not hand-kill the uvicorn /
node processes** — pm2 would immediately restart the old build and fight you for the
port. Always go through pm2.

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture

# Reload picks up the freshly built code (web: new .next/standalone; agent: new app code).
# Restarts (crash or reload) NEVER bump the version — that only happens in step 3.
pm2 reload ecosystem.config.cjs
pm2 save               # persist updated process list
pm2 ls                 # confirm both online, sane restart counts
```

- **First-time / fresh machine** (pm2 not yet managing these apps — `pm2 ls` shows
  nothing): use `pm2 start ecosystem.config.cjs && pm2 save` instead of reload. If a
  stale manual process still holds `3000`/`18010`, kill that one first so pm2 can bind.
- **Boot persistence:** run `pm2 startup` once and execute the `sudo` line it prints
  (registers a launchd entry); `pm2 save` captures the current list for resurrect.
- Logs: `pm2 logs sa-agent` / `pm2 logs sa-web` (also at `.runtime/logs/`).
- Never `pm2 delete`/kill `cloudflared`, `nginx`, or unrelated services.

### 5. 验活（本地 → 域名，完整三步）

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
# load-root-env.sh has a BASH_SOURCE guard that breaks in non-interactive subshells;
# use set -a / source .env directly, then pull keychain secrets explicitly.
set -a && source .env && set +a

LOCAL_AGENT_PORT=$(cat .runtime/local-agent-port 2>/dev/null || echo "18010")
HEALTH_USERNAME=${HEALTH_USERNAME:-gago-admin}
if [ -z "${HEALTH_PASSWORD:-}" ]; then
  echo "❌ HEALTH_PASSWORD 未加载，请确认 .env 中已配置"; exit 1
fi

EXPECTED_VERSION=$(node -p "require('./apps/web/package.json').version")

smoke_test() {
  local base_web=$1 base_agent=$2 label=$3
  echo ""; echo "══ 验活：${label} ══"

  echo "[1/3] web health + version"
  WEB_HEALTH=$(curl -fsS "$base_web/api/health")
  echo "$WEB_HEALTH" | python3 -m json.tool
  WEB_VERSION=$(echo "$WEB_HEALTH" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))')
  if [ "$WEB_VERSION" != "$EXPECTED_VERSION" ]; then
    echo "❌ 版本不符：期望 $EXPECTED_VERSION，实际 $WEB_VERSION"; return 1
  fi
  echo "  ✓ web version $WEB_VERSION"

  # agent health：仅本地可直接访问，域名验活跳过此步
  if [ "$base_agent" != "skip" ]; then
    echo "[2/3] agent health + version"
    AGENT_HEALTH=$(curl -fsS "$base_agent/health")
    echo "$AGENT_HEALTH" | python3 -m json.tool
    AGENT_VERSION=$(echo "$AGENT_HEALTH" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))')
    if [ "$AGENT_VERSION" != "$EXPECTED_VERSION" ]; then
      echo "❌ 版本不符：期望 $EXPECTED_VERSION，实际 $AGENT_VERSION"; return 1
    fi
    echo "  ✓ agent version $AGENT_VERSION"
  else
    echo "[2/3] agent health — skipped (not exposed at domain level)"
  fi

  echo "[3/3] chat smoke"
  AUTH_TOKEN=$(curl -fsS -X POST "$base_web/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$HEALTH_USERNAME\",\"password\":\"$HEALTH_PASSWORD\"}" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')
  [ -z "$AUTH_TOKEN" ] && echo "❌ 登录失败" && return 1
  # Pipe directly to Python (avoid storing JSON in bash var — json.load(sys.stdin)
  # fails on responses that contain actual newlines inside string values).
  curl -fsS -X POST "$base_web/api/agent/chat" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -d '{"message":"最近墒情怎么样","session_id":"health-check","turn_id":1,"client_message_id":"hc-1"}' \
    | python3 -c '
import json, sys
raw = sys.stdin.buffer.read()
d = json.loads(raw)
if not (d.get("final_text") or d.get("answer")):
    print("❌ chat 无有效响应:", raw.decode("utf-8","replace")[:200])
    sys.exit(1)
print("  ✓ chat ok, final_text len:", len(d.get("final_text") or d.get("answer","")))
' || return 1
  echo "  ✓ ${label} 验活通过 (version: $EXPECTED_VERSION)"
}

# 本地验活（agent 直接访问）
smoke_test "http://localhost:3000" "http://localhost:${LOCAL_AGENT_PORT}" "localhost"

# 域名验活 — web version 必须等于 EXPECTED_VERSION 才算发布成功
smoke_test "https://ai.luyaxiang.com" "skip" "ai.luyaxiang.com"
```

> **chat smoke + version 是发布门禁**，域名返回的 version 必须与本次发布版本一致才算完成。


## Quick Reference

- Repo root: `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- Agent port: `.runtime/local-agent-port`, default `18010`
- pm2 config: `ecosystem.config.cjs` (apps `sa-agent`, `sa-web`)
- Reload after deploy: `pm2 reload ecosystem.config.cjs && pm2 save`
- First-time start: `pm2 start ecosystem.config.cjs && pm2 save`
- Status / logs: `pm2 ls`, `pm2 logs sa-agent`, `pm2 logs sa-web`
- Start agent (raw, normally pm2-managed): `bash scripts/dev/start-local-agent.sh`
- Start web (raw, normally pm2-managed): `bash scripts/dev/start-local-web.sh`
- Local web health: `http://localhost:3000/api/health`
- Live web health: `https://ai.luyaxiang.com/api/health`

## Common Mistakes

- Assuming `ai.yaxianglu.com` is the correct domain. Use `ai.luyaxiang.com`.
- Hand-killing the uvicorn/node process — pm2 instantly restarts the OLD build and re-grabs the port. Use `pm2 reload` instead.
- Forgetting to stop Docker containers before starting process mode (port conflicts on `3000`).
- Trusting `/api/health` without running login + chat smoke.
- Restarting `nginx` or `cloudflared` when only `3000` or `18010` needs refresh.
