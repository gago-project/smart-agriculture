# Smart Agriculture

Smart Agriculture 是一个以“土壤墒情智能体”为核心的前后端一体项目。当前仓库采用 monorepo 组织：

- `apps/web`：Next.js 主应用，承接页面、管理后台、BFF API、Soniox 临时 token 接口
- `apps/agent`：Python FastAPI 智能体服务，严格按受限 Flow 实现事实查询、规则判断、预警模板与建议生成
- `infra/mysql`：独立的 `smart_agriculture` MySQL 初始化脚本与种子数据
- `infra/redis`：Redis 运行时配置
- `infra/docker`：`web / agent / mysql / redis` 四服务编排
- `scripts`：本地启动、验活与辅助脚本
- `docs`：系统架构、接口与 Docker 运维说明

## 目录与职责

### 1. Web

- 页面入口：`apps/web/app/page.tsx`
- 智能问答页：`apps/web/app/chat/page.tsx`
- 管理后台页：`apps/web/app/admin/page.tsx`
- 智能体代理接口：`apps/web/app/api/agent/chat/route.ts`
- 智能体概览代理：`apps/web/app/api/agent/summary/route.ts`
- Soniox 临时 token：`apps/web/app/api/soniox/token/route.ts`

### 2. Agent

- 服务入口：`apps/agent/app/main.py`
- 主业务服务：`apps/agent/app/services/agent_service.py`
- 受限 Flow 运行器：`apps/agent/app/flow/runner.py`
- 数据访问层：`apps/agent/app/repositories/soil_repository.py`
- Flow 状态契约：`apps/agent/app/schemas/state.py`

### 3. Infra

- Docker 编排：`infra/docker/docker-compose.yml`
- MySQL 建库建表：`infra/mysql/init/001_init_tables.sql`
- MySQL 业务初始化数据：`infra/mysql/init/002_insert_data.sql`
- MySQL 本地账号种子模板：`infra/mysql/local/seed_auth_users.local.sql.example`
- Redis 配置：`infra/redis/redis.conf`

## 快速启动

### 方案 A：Docker 启动完整环境

```bash
cp .env.example .env
# 按需填写 QWEN_API_KEY、SONIOX_API_KEY
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
```

启动后访问：

- Web 首页：`http://localhost:3000`
- Agent 健康检查：`http://localhost:8000/health`

### 方案 B：本地分开启动 Web + Agent

```bash
python3 -m venv .venv
npm --prefix apps/web install
npm run setup:agent
npm run build:web
```

终端 1：

```bash
bash scripts/dev/start-local-agent.sh
```

终端 2：

```bash
bash scripts/dev/start-local-web.sh
```

说明：

- 本地 agent 会优先选择 `18010~18014` 中的空闲端口，并写入 `.runtime/local-agent-port`
- `scripts/dev/start-local-web.sh` 与 `scripts/health/check-local.sh` 会自动读取这个运行时端口
- Docker Compose 场景仍使用容器内 `8000`，不受本地脚本默认值影响

## 数据库初始化

提交到仓库的 MySQL 初始化脚本只包含两类内容：

1. `infra/mysql/init/001_init_tables.sql`：创建 `smart_agriculture` 数据库、核心表、索引
2. `infra/mysql/init/002_insert_data.sql`：导入非敏感业务初始化数据，包括规则、模板、导入批次和墒情事实样例

真实登录账号、密码哈希、密码盐不放在 `infra/mysql/init/*.sql` 中。需要本地账号时，复制本地模板：

```bash
cp infra/mysql/local/seed_auth_users.local.sql.example infra/mysql/local/seed_auth_users.local.sql
```

然后只在本机 `.local.sql` 中填写账号哈希和盐；该文件已被 `.gitignore` 忽略，不能提交。

更推荐的本地账号初始化方式是复制 JSON 模板，由脚本在本机生成哈希后再写库：

```bash
cp infra/mysql/local/auth_users.local.json.example infra/mysql/local/auth_users.local.json
```

`auth_users.local.json` 只保留在本机，`db:init:local` 会自动读取并生成 `auth_user` 记录。
如需把外部土壤 Excel 全量导入本机 MySQL，可将文件放到
`infra/mysql/local/soil_data.local.xlsx`，或者通过 `SOIL_EXCEL_SOURCE` 指向外部文件。

初始化本机 `localhost` MySQL：

```bash
npm run db:init:local
```

脚本会读取 `.env` 中的 `MYSQL_*`，也支持用 `LOCAL_MYSQL_HOST`、`LOCAL_MYSQL_PORT`、
`MYSQL_APPLY_USER`、`MYSQL_APPLY_PASSWORD` 覆盖本机导入连接信息；并会按顺序执行：

1. `001_init_tables.sql`
2. `002_insert_data.sql`
3. 本地 JSON 账号引导或本地 SQL 账号种子（二选一）
4. 本地全量 Excel 导入（若检测到 `SOIL_EXCEL_SOURCE` 或 `infra/mysql/local/soil_data.local.xlsx`）

若未显式指定，脚本会优先使用 `MYSQL_ROOT_PASSWORD` 对应的初始化账号执行建库/建表。

## 验活

统一验活脚本：

```bash
bash scripts/health/check-local.sh
```

脚本默认检查：

1. `GET /api/health`
2. `GET /health`
3. `POST /api/agent/chat` 的一次烟雾请求

## 数据来源

- 土地墒情原始 Excel：`${GAGO_CLOUD_ROOT}/doc/0414/土壤墒情仪数据(2).xlsx`
- 规则与模板 PDF：`${GAGO_CLOUD_ROOT}/doc/江苏省农业农村指挥调度平台预警规则及发布模版.pdf`
- 当前提交版初始化脚本写入可公开的墒情事实样例；大体量原始 Excel 不直接提交到仓库

## 设计约束

当前智能体实现必须遵守 `${GAGO_CLOUD_ROOT}/plans` 中已确认的受限 Flow 设计，重点参考：

- `4.2026-04-20-soil-moisture-agent-python-flow-design.md`
- `5.2026-04-20-soil-moisture-agent-python-implementation-plan.md`
- `6.2026-04-20-soil-moisture-agent-python-pseudocode.md`
- `7.2026-04-20-soil-moisture-agent-system-design-diagram.md`
- `8.2026-04-21-soil-moisture-agent-flow-risk-contract.md`

## 现阶段说明

- 当前机器若未安装 Docker，则只能验证代码、构建和本地脚本，不能实跑 `docker compose`
- Agent 数据访问走 MySQL；数据库不可用时会返回明确错误，不使用内置样例记录伪造回答
- Soniox 与千问密钥都只通过 `.env` 注入，不写入代码
