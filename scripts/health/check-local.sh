#!/usr/bin/env bash
set -euo pipefail

BASE_WEB=${BASE_WEB:-http://localhost:3000}

if [ -z "${BASE_AGENT:-}" ]; then
  ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
  if [ -f "${ROOT_DIR}/.runtime/local-agent-port" ]; then
    LOCAL_AGENT_PORT=$(cat "${ROOT_DIR}/.runtime/local-agent-port")
    BASE_AGENT="http://localhost:${LOCAL_AGENT_PORT}"
  elif curl -fsS "http://localhost:18010/health" >/dev/null 2>&1; then
    BASE_AGENT="http://localhost:18010"
  else
    BASE_AGENT="http://localhost:8000"
  fi
fi

print_json() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  else
    python3 -m json.tool
  fi
}

echo "[1/3] web health"
curl -fsS "$BASE_WEB/api/health" | print_json

echo "[2/3] agent health"
curl -fsS "$BASE_AGENT/health" | print_json

echo "[3/3] agent chat smoke"
curl -fsS -X POST "$BASE_WEB/api/agent/chat" \
  -H 'Content-Type: application/json' \
  -d '{"message":"最近墒情怎么样","session_id":"health-check","turn_id":1}' | print_json
