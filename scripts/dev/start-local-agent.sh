#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "缺少 .venv/bin/python，请先在项目根目录创建虚拟环境。"
  exit 1
fi

find_free_port() {
  for candidate in 18010 18011 18012 18013 18014; do
    if ! lsof -nP -iTCP:"${candidate}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

AGENT_PORT=${AGENT_PORT:-$(find_free_port)}

if [ -z "${AGENT_PORT}" ]; then
  echo "未找到可用的本地 agent 端口。"
  exit 1
fi

mkdir -p .runtime
printf '%s\n' "${AGENT_PORT}" > .runtime/local-agent-port

echo "本地 agent 启动端口: ${AGENT_PORT}"

exec env PYTHONPATH=apps/agent .venv/bin/python -m uvicorn app.main:app --app-dir apps/agent --host 0.0.0.0 --port "${AGENT_PORT}"
