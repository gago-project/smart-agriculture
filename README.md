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
- 墒情概览接口：`apps/web/app/api/soil/summary/route.ts`
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
- MySQL 种子数据：`infra/mysql/init/002_seed_data.sql`
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

- 土地墒情原始 Excel：`/Users/mac/Desktop/gago-cloud/doc/0414/土壤墒情仪数据(2).xlsx`
- 规则与模板 PDF：`/Users/mac/Desktop/gago-cloud/doc/江苏省农业农村指挥调度平台预警规则及发布模版.pdf`
- 当前种子数据从 Excel 中抽取样例写入 `smart_agriculture.fact_soil_moisture`

## 设计约束

当前智能体实现必须遵守 `/Users/mac/Desktop/gago-cloud/plans` 中已确认的受限 Flow 设计，重点参考：

- `4.2026-04-20-soil-moisture-agent-python-flow-design.md`
- `5.2026-04-20-soil-moisture-agent-python-implementation-plan.md`
- `6.2026-04-20-soil-moisture-agent-python-pseudocode.md`
- `7.2026-04-20-soil-moisture-agent-system-design-diagram.md`
- `8.2026-04-21-soil-moisture-agent-flow-risk-contract.md`

## 现阶段说明

- 当前机器若未安装 Docker，则只能验证代码、构建和本地脚本，不能实跑 `docker compose`
- Agent 数据访问优先走 MySQL；本地无库时，会安全降级到内置样例记录，保证页面和问答链路可运行
- Soniox 与千问密钥都只通过 `.env` 注入，不写入代码
