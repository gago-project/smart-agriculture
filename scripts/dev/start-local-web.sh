#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

LOAD_ROOT_ENV_EXCLUDE_PATTERN='^(AGENT_BASE_URL|WEB_PORT|NEXT_PUBLIC_BASE_URL)$'
source "${ROOT_DIR}/scripts/dev/load-root-env.sh"
unset LOAD_ROOT_ENV_EXCLUDE_PATTERN

if [ -f ".runtime/local-agent-port" ]; then
  LOCAL_AGENT_PORT=$(cat .runtime/local-agent-port)
else
  LOCAL_AGENT_PORT=18010
fi

# Deterministic, fixed web port — no auto-increment.
WEB_PORT="${WEB_PORT:-18030}"

export AGENT_BASE_URL="${AGENT_BASE_URL:-http://localhost:${LOCAL_AGENT_PORT}}"
export NEXT_PUBLIC_BASE_URL="${NEXT_PUBLIC_BASE_URL:-http://localhost:${WEB_PORT}}"

# On a pm2 restart the old instance may take a moment to release the socket, so
# wait briefly for OUR own previous process to let go. If something *foreign*
# still holds the port, refuse to start (do not move to another port).
# Note: lsof exits non-zero when nothing matches; `|| true` keeps `set -e` from
# aborting the script in the (normal) free-port case.
for attempt in 1 2 3 4 5; do
  holder=$(lsof -nP -iTCP:"${WEB_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
  [ -z "${holder}" ] && break
  echo "[web] 端口 ${WEB_PORT} 被 pid ${holder} 占用，等待释放 (${attempt}/5)…" >&2
  sleep 1
done
holder=$(lsof -nP -iTCP:"${WEB_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
if [ -n "${holder}" ]; then
  echo "❌ 端口 ${WEB_PORT} 已被 pid ${holder} 占用，web 拒绝启动（端口固定，不再自动顺延）。" >&2
  echo "   排查：lsof -nP -iTCP:${WEB_PORT} -sTCP:LISTEN" >&2
  exit 1
fi

# Prepare standalone static assets (formerly npm's prestart-style step).
npm --prefix apps/web run copy:standalone-assets

# exec the Next standalone server DIRECTLY — NOT via `npm run start`. Going through
# npm leaves the real `node` server as a grandchild; on a pm2 restart npm gets
# killed but the node grandchild orphans (PPID 1) and keeps holding the port,
# causing the next start to crash-loop on EADDRINUSE. Exec'ing node here makes
# pm2 supervise the actual listener, so restarts are clean.
echo "本地 web 启动端口: ${WEB_PORT} (固定)"
cd apps/web
exec env HOSTNAME=0.0.0.0 PORT="${WEB_PORT}" node .next/standalone/server.js
