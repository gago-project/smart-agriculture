# Soil Moisture Agent

LLM + Function Calling 单 Agent 服务，按 `plans/1/` 的结构设计，`plans/2026-04-27-llm-function-calling-agent.md` 的任务计划实施。

## 架构概览

```
用户输入
  -> InputGuard          （安全门：拦截非业务/越界输入）
  -> AgentLoop           （LLM + Function Calling 核心循环）
  -> DataFactCheck       （事实核查：数字/地区/时间）
  -> AnswerVerify        （回答合规：防空答/防内部术语）
  -> FallbackGuard       （统一兜底）
```

LLM 负责理解用户意图、选择工具、决定调用顺序。代码负责参数验证、SQL 执行、事实核查。

## 工具集（7 个）

| 工具 | 作用 |
|------|------|
| `get_soil_overview` | 整体概况 |
| `get_soil_ranking` | 排名对比 |
| `get_soil_detail` | 区域/设备详情 |
| `get_soil_anomaly` | 异常查询 |
| `get_warning_data` | 预警数据 |
| `get_advice_context` | 建议背景数据 |
| `diagnose_empty_result` | 空结果诊断 |

## 关键设计原则

- **LLM 是决策者**：意图理解、工具选择、多轮上下文全部交给 LLM
- **代码是守门员**：参数验证、SQL 执行、事实核查不经过 LLM
- **消息历史驱动多轮**：Redis 存储真实对话消息（user/assistant/tool），LLM 天然理解多轮上下文
- **facts only**：LLM 不得编造数字、地区、设备号，所有事实来自 `fact_soil_moisture`

## 文档导航

- `plans/1/1.plan.md` — Agent 核心架构契约
- `plans/1/4.python-flow-design.md` — Python 工程分层设计
- `plans/1/7.system-design-diagram.md` — 系统设计图与时序图
- `plans/1/8.flow-risk-contract.md` — 安全契约与降级策略
- `plans/2026-04-27-llm-function-calling-agent.md` — 实施 Plan（Tasks 1-9）
