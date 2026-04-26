#!/usr/bin/env bash
set -euo pipefail

BASE_WEB=${BASE_WEB:-http://localhost:3000}
HEALTH_USERNAME=${HEALTH_USERNAME:-gago-admin}
HEALTH_PASSWORD=${HEALTH_PASSWORD:-}

if [ -z "$HEALTH_PASSWORD" ]; then
  echo "❌ 缺少 HEALTH_PASSWORD。请确认 .env 中已配置 HEALTH_PASSWORD，或通过环境变量传入。"
  exit 1
fi

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
AUTH_PAYLOAD=$(printf '{"username":"%s","password":"%s"}' "$HEALTH_USERNAME" "$HEALTH_PASSWORD")
AUTH_RESPONSE=$(curl -fsS -X POST "$BASE_WEB/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$AUTH_PAYLOAD")
AUTH_TOKEN=$(printf '%s' "$AUTH_RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')

if [ -z "$AUTH_TOKEN" ]; then
  echo "登录失败，未获取到 token"
  exit 1
fi

curl -fsS -X POST "$BASE_WEB/api/agent/chat" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"question":"最近墒情怎么样","thread_id":"health-check","history":[]}' | print_json
