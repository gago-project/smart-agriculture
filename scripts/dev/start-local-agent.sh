#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

LOAD_ROOT_ENV_EXCLUDE_PATTERN='^(AGENT_PORT|AGENT_BASE_URL|WEB_PORT|NEXT_PUBLIC_BASE_URL)$'
source "${ROOT_DIR}/scripts/dev/load-root-env.sh"
unset LOAD_ROOT_ENV_EXCLUDE_PATTERN

if [ ! -x ".venv/bin/python" ]; then
  echo "缺少 .venv/bin/python，请先在项目根目录创建虚拟环境。"
  exit 1
fi

# Deterministic, fixed port — no auto-increment. The agent always binds 18010.
# A conflict is surfaced as an error, never silently dodged.
AGENT_PORT="${AGENT_PORT:-18010}"

# On a pm2 restart the old instance may take a moment to release the socket, so
# wait briefly for OUR own previous process to let go. If something *foreign*
# still holds the port after that, refuse to start (do not move to another port).
for attempt in 1 2 3 4 5; do
  holder=$(lsof -nP -iTCP:"${AGENT_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1)
  [ -z "${holder}" ] && break
  echo "[agent] 端口 ${AGENT_PORT} 被 pid ${holder} 占用，等待释放 (${attempt}/5)…" >&2
  sleep 1
done
holder=$(lsof -nP -iTCP:"${AGENT_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1)
if [ -n "${holder}" ]; then
  echo "❌ 端口 ${AGENT_PORT} 已被 pid ${holder} 占用，agent 拒绝启动（端口固定，不再自动顺延）。" >&2
  echo "   排查：lsof -nP -iTCP:${AGENT_PORT} -sTCP:LISTEN" >&2
  exit 1
fi

mkdir -p .runtime
printf '%s\n' "${AGENT_PORT}" > .runtime/local-agent-port

echo "本地 agent 启动端口: ${AGENT_PORT} (固定)"

# Avoid inheriting desktop SOCKS proxy settings into httpx, which would
# otherwise require the optional socksio extra just to reach DashScope.
exec env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  PYTHONPATH=apps/agent .venv/bin/python -m uvicorn app.main:app --app-dir apps/agent --host 0.0.0.0 --port "${AGENT_PORT}"
