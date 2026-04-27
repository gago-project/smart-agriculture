# Soil Moisture Agent

LLM + Function Calling 单 Agent 服务，正式设计以 `plans/1/` 下的架构文档为准。

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

## 目标工具契约（4 类真实能力）

| 工具 | 作用 |
|------|------|
| `query_soil_summary` | 整体概况 / 聚合概览 |
| `query_soil_ranking` | 排名对比 / TopN |
| `query_soil_detail` | 区域 / 设备详情 |
| `diagnose_empty_result` | 空结果诊断 |

当前代码在迁移期可能仍保留 `7` 个名义 tool，但正式设计目标是把它们收口到以上 `4` 类真实执行能力。`anomaly / warning / advice` 作为输出模式保留，不再作为一层级工具分类。

## 关键设计原则

- **LLM 是决策者**：意图理解、工具选择、多轮上下文全部交给 LLM
- **代码是守门员**：参数验证、SQL 执行、事实核查不经过 LLM
- **域内问题必须命中 tool**：只要是业务问题，就不能允许模型绕过工具直接编造回答
- **消息历史驱动多轮**：目标是标准 transcript（user/assistant/tool），LLM 基于历史理解多轮上下文
- **facts only**：LLM 不得编造数字、地区、设备号，所有事实来自 `fact_soil_moisture`
- **回答契约要收口**：一级 `answer_type` 目标收口为 `5` 类，`warning / advice / anomaly` 作为输出模式处理

## 文档导航

- `plans/1/1.plan.md` — Agent 核心架构契约
- `plans/1/2.answer-types-business.md` — 当前 11 类业务回答底稿与后续收口方向
- `plans/1/4.python-flow-design.md` — Python 工程分层设计
- `plans/1/7.system-design-diagram.md` — 系统设计图与时序图
- `plans/1/8.flow-risk-contract.md` — 安全契约与降级策略
- `plans/1/9.llm-fc-design-audit.md` — 当前设计审计、风险清单与整改建议
