# 本地启动联调手册（5 条命令版）

适合本机开发、页面联调、Agent 联调、数据库联调。

## 前提

- 已安装 Python 3、Node.js、npm
- 本机 `localhost` MySQL 已可连接
- `.env` 已填写 `MYSQL_*`、`REDIS_URL` 等非敏感配置
- 本地推荐把 `QWEN_API_KEY`、`SONIOX_API_KEY` 存入 macOS Keychain
- 第 4、5 条命令需要分别放在两个终端执行

本地脚本读取顺序为：

1. 当前 shell 环境变量
2. macOS Keychain
3. `.env`

默认 Keychain 配置为：

- service：`smart-agriculture-local`
- account：`QWEN_API_KEY`
- account：`SONIOX_API_KEY`

## 5 条命令

命令 1：准备本地环境文件

```bash
([ -f .env ] || cp .env.example .env) && ([ -f infra/mysql/local/auth_users.local.json ] || cp infra/mysql/local/auth_users.local.json.example infra/mysql/local/auth_users.local.json)
```

命令 2：安装 Web 与 Agent 依赖

```bash
python3 -m venv .venv && npm --prefix apps/web install && npm run setup:agent && npm run build:web
```

命令 3：初始化本机数据库

```bash
npm run db:init:local
```

命令 4：启动本地 Agent

```bash
bash scripts/dev/start-local-agent.sh
```

命令 5：启动本地 Web

```bash
bash scripts/dev/start-local-web.sh
```

## 启动后访问

- Web 工作台：`http://localhost:3000`
- Agent 健康检查：以 `.runtime/local-agent-port` 记录的端口为准，例如 `http://localhost:18010/health`
- 统一验活：`bash scripts/health/check-local.sh`

## 补充说明

- Agent 会自动选择 `18010~18014` 的空闲端口，并写入 `.runtime/local-agent-port`
- Web 启动脚本和验活脚本会自动读取这个运行时端口，无需手工改 `AGENT_BASE_URL`
- 如果只想补导入本地 Excel，可单独执行 `npm run db:import:soil:local`
- 如果只想补本地登录账号，可单独执行 `npm run db:seed:auth:local`

## 相关文件

- 环境加载脚本：`scripts/dev/load-root-env.sh`
- Agent 启动脚本：`scripts/dev/start-local-agent.sh`
- Web 启动脚本：`scripts/dev/start-local-web.sh`
- 数据库初始化脚本：`scripts/db/apply-local-init.sh`
