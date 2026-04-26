---
name: local-health
description: >
  Use when verifying the local Smart Agriculture stack is healthy — after any
  deploy, restart, or mode switch. Runs web health, agent health, and a real
  login + chat smoke test. Works for both process mode and Docker mode.
---

# Smart Agriculture — 联调验活 Skill

## 什么时候用

- 每次 deploy（进程模式或 Docker 模式）之后
- 怀疑服务异常、返回 502 或无响应时
- 切换进程模式 ↔ Docker 模式后
- 发布前的最终确认

---

## 前置：确定连接参数

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
source scripts/dev/load-root-env.sh

BASE_WEB=${BASE_WEB:-http://localhost:3000}

# 烟雾测试专用账号，凭据已在 .env 中（由 load-root-env.sh 加载）
HEALTH_USERNAME=${HEALTH_USERNAME:-gago-1}
HEALTH_PASSWORD=${HEALTH_PASSWORD:-}
if [ -z "$HEALTH_PASSWORD" ]; then
  echo "❌ HEALTH_PASSWORD 未加载，请确认 .env 中已配置 HEALTH_PASSWORD=..."
  exit 1
fi

# 自动检测 agent 端口
# 进程模式：读 .runtime/local-agent-port（默认 18010）
# Docker 模式：8000
if [ -z "${BASE_AGENT:-}" ]; then
  if [ -f ".runtime/local-agent-port" ]; then
    LOCAL_AGENT_PORT=$(cat .runtime/local-agent-port)
    BASE_AGENT="http://localhost:${LOCAL_AGENT_PORT}"
  elif curl -fsS "http://localhost:18010/health" >/dev/null 2>&1; then
    BASE_AGENT="http://localhost:18010"
  else
    BASE_AGENT="http://localhost:8000"
  fi
fi

echo "BASE_WEB   = $BASE_WEB"
echo "BASE_AGENT = $BASE_AGENT"
```

---

## 三步验活

### 步骤一：Web 健康检查

```bash
echo "[1/3] web health"
curl -fsS "$BASE_WEB/api/health" | python3 -m json.tool
```

期望：`{"status":"ok"}` 或包含 `ok` 的 JSON。  
失败：返回 502/连接拒绝 → web 服务未启动或端口冲突。

---

### 步骤二：Agent 健康检查

```bash
echo "[2/3] agent health"
curl -fsS "$BASE_AGENT/health" | python3 -m json.tool
```

期望：`{"status":"ok"}` 或包含 `ok` 的 JSON。  
失败：进程模式检查 `lsof -nP -iTCP -sTCP:LISTEN | grep 18010`；Docker 模式检查 `docker compose --env-file .env -f infra/docker/docker-compose.yml ps agent`。

---

### 步骤三：登录 + Chat 冒烟（最关键）

```bash
echo "[3/3] agent chat smoke"

AUTH_RESPONSE=$(curl -fsS -X POST "$BASE_WEB/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$HEALTH_USERNAME\",\"password\":\"$HEALTH_PASSWORD\"}")

AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("token",""))')

if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ 登录失败，未获取到 token"
  echo "   响应内容: $AUTH_RESPONSE"
  exit 1
fi

echo "  ✓ 登录成功，token 已获取"

curl -fsS -X POST "$BASE_WEB/api/agent/chat" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"question":"最近墒情怎么样","thread_id":"health-check","history":[]}' \
  | python3 -m json.tool
```

期望：返回包含 `answer` 或 `response` 的 JSON，有实际文字内容。  
失败：检查 agent 日志 `docker compose --env-file .env -f infra/docker/docker-compose.yml logs agent --tail=50`。

---

## 一键执行（快捷方式）

以上三步已封装在 `scripts/health/check-local.sh`，可直接运行：

```bash
# 进程模式（自动检测 .runtime/local-agent-port）
HEALTH_PASSWORD="xxx" bash scripts/health/check-local.sh

# Docker 模式（明确指定 agent 端口）
HEALTH_PASSWORD="xxx" BASE_AGENT="http://localhost:8000" bash scripts/health/check-local.sh

# 指向线上域名
HEALTH_PASSWORD="xxx" \
BASE_WEB="https://ai.luyaxiang.com" \
BASE_AGENT="https://ai.luyaxiang.com" \
bash scripts/health/check-local.sh
```

---

## 常见失败与处理

| 现象 | 原因 | 处理 |
|------|------|------|
| `curl: (7) Failed to connect` | 服务未启动 | 检查 `docker ps` 或 `lsof` 端口 |
| `curl: (22) 502 Bad Gateway` | nginx 代理失败 | 检查 web 容器/进程是否在跑 |
| `登录失败，未获取到 token` | 密码错 / auth 表没用户 | 检查 `HEALTH_PASSWORD`，运行 db-sync `--auth` |
| agent health 返回 500 | agent 启动异常 | 查 agent 日志，检查 DB/Redis 连接 |
| chat smoke 返回空 answer | LLM API key 失效 | 检查 `QWEN_API_KEY` |

---

## 提示

- **步骤三（chat smoke）是真正的发布门禁**，不能只看步骤一二就算验活完成。
- 进程模式 agent 端口不固定，始终从 `.runtime/local-agent-port` 读取，不要硬编码 18010。
- 不要重启 `nginx` 或 `cloudflared`，这两个服务与本项目无关。
