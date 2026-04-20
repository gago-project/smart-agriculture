#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

if [ -f ".runtime/local-agent-port" ]; then
  LOCAL_AGENT_PORT=$(cat .runtime/local-agent-port)
else
  LOCAL_AGENT_PORT=18010
fi

export AGENT_BASE_URL="${AGENT_BASE_URL:-http://localhost:${LOCAL_AGENT_PORT}}"
export NEXT_PUBLIC_BASE_URL="${NEXT_PUBLIC_BASE_URL:-http://localhost:3000}"

exec npm --prefix apps/web run start
