---
name: soil-moisture-qa
description: >
  Use when running QA, regression testing, or business review for the
  soil-moisture Agent. Covers three test layers (smoke / acceptance /
  specialist), when to run each, key assertions, how to extend the case
  library, and how to prepare for business review sessions.
---

# Smart Agriculture — 墒情 Agent QA Skill

> **架构版本**：LLM + Function Calling 5 节点（已于 2026-04-27 完成迁移）。
> 原 IntentSlot / ExecutionGate / RuleEngine / Template / Advice 管线已删除。

## 测试资产分布（权威）

| 资产 | 路径 | 说明 |
|------|------|------|
| **正式 Case 主库** | `testdata/agent/soil-moisture/case-library.md` | **唯一入口**，所有新增/修订/删除只改这里 |
| Agent 能力方案 | `apps/agent/plans/1/1.plan.md` | 路由、能力设计 |
| 回答类型与业务边界 | `apps/agent/plans/1/2.answer-types-business.md` | intent → answer_type 映射 |
| 一次性测试产物 | `outputs/` | Excel/CSV/截图，不作为长期规则 |

**原则：** 测试文档与实现不一致时，优先核对代码和工具定义，再同步回写 case-library。

---

## 架构约束（QA 必须对齐）

### 5 节点 Flow

`InputGuard → AgentLoop → DataFactCheck → AnswerVerify → FallbackGuard`

### 4 个 Tool（LLM 唯一可调用的接口）

| Tool | 作用 | 对应 answer_type |
|------|------|-----------------|
| `query_soil_summary` | 聚合概览：总条数、平均含水量、状态分布、预警 TopN | `soil_summary_answer` |
| `query_soil_ranking` | 排名 TopN（已排序，不含原始记录） | `soil_ranking_answer` |
| `query_soil_detail` | 单实体详情：最新记录、预警记录、状态摘要 | `soil_detail_answer` |
| `diagnose_empty_result` | 诊断空结果：区分对象不存在 vs 时间窗无数据 | `fallback_answer` |

### 5 个 answer_type（不允许出现其他值）

| answer_type | 来源 | guidance_reason / fallback_reason |
|-------------|------|-----------------------------------|
| `soil_summary_answer` | query_soil_summary 命中 | — |
| `soil_ranking_answer` | query_soil_ranking 命中 | — |
| `soil_detail_answer` | query_soil_detail 命中 | — |
| `guidance_answer` | InputGuard 拦截 | `safe_hint` / `clarification` / `boundary` / `closing` |
| `fallback_answer` | P0 兜底 / diagnose 结果 / FactCheck 失败 | `tool_missing` / `entity_not_found` / `no_data` / `fact_check_failed` |

### output_mode（可叠加在 summary/detail 上）

`normal` / `anomaly_focus` / `warning_mode` / `advice_mode`

### P0 红线

业务类问题（非问候/闲聊/越界）LLM **必须先调用 Tool** 才能给出业务回答。
未调用 Tool 直接回答 → 系统强制截停，返回 `fallback_answer`（fallback_reason=tool_missing）。

---

## 三层测试资产

### 冒烟层（每次改动后快速自测）

**目标：** 快速判断主链路是否还能跑通。

至少覆盖以下 5 类各 1 条：
- 概览问题（如："最近墒情怎么样"）
- 地区详情（如："南通市今天墒情"）
- 设备异常（如："SNS00204333 有没有异常"）
- 排名问题（如："过去一个月哪里最严重"）
- 兜底/澄清（如："谢谢" / "查一下天气"）

**适用时机：**
- 本地改动后快速自测
- 部署前后快速验证
- 线上问题修复后最小复测

---

### 验收层（里程碑 / 合并主分支前）

**目标：** 验证 MVP 公开承诺的能力边界。

**当前主库：** `testdata/agent/soil-moisture/case-library.md`，共 **130 个 Case**。

| 分类 | Case 数 | CaseID |
|------|--------:|--------|
| A. 非业务 / 安全提示 | 6 | SM-CONV-001 ~ SM-CONV-006 |
| B. 澄清引导 | 8 | SM-CONV-007 ~ SM-CONV-014 |
| C. 墒情概览 | 15 | SM-SUM-001 ~ SM-SUM-015 |
| D. 排名对比 | 15 | SM-RANK-001 ~ SM-RANK-015 |
| E. 地区 / 设备详情 | 18 | SM-DETAIL-001 ~ SM-DETAIL-018 |
| F. 异常分析 | 16 | SM-DETAIL-019 ~ SM-DETAIL-034 |
| G. 预警模板输出 | 16 | SM-DETAIL-035 ~ SM-DETAIL-050 |
| H. 指标解释 / 指导建议 | 11 | SM-CONV-015 ~ SM-CONV-025 |
| I. 无数据 / 找不到 / 兜底 | 10 | SM-EMPTY-001 ~ SM-EMPTY-005, SM-FB-001 ~ SM-FB-005 |
| J. 能力边界 | 5 | SM-CONV-026 ~ SM-CONV-030 |

**执行顺序：**
1. 第一轮：跑 case-library.md 全部 130 个 Case
2. 第二轮：对需要查库的 Case，补真实数据断言（数值与结构化证据字段）
3. 第三轮：如本次改动涉及地区解析或工具参数校验，额外做专项抽查

**适用时机：** 里程碑验收、功能合并到主分支前、对商务/产品展示前。

---

### 专项回归层（高风险链路加密测试）

重点专项：
- **P0 红线**：业务问题 LLM 绕过 Tool 直接回答必须被截停
- **Tool 命中准确性**：summary/ranking/detail/diagnose 对应正确
- **ranking 真正排序**：items 按 alert_count 降序，rank 字段从 1 开始
- **empty_result 诊断**：entity_not_found vs no_data_in_window 区分正确
- **guidance_reason / fallback_reason / output_mode 契约**：字段存在且值合法
- **结构化证据**：tool_trace / answer_facts / query_result 可用于事实验证
- 地区别名解析：query_soil_detail city/county 参数正确
- 多轮上下文继承：通过 history 消息链，非 session slot 复用
- 工具参数校验：top_n ≤ 20，时间窗 ≤ 365 天
- 查询日志写入 / 不写入边界
- 无数据 / 找不到对象 / 公共异常兜底

---

## 测试前置假设

在跑任何 Case 前，确认以下假设成立：

- 默认时区：`Asia/Shanghai`
- 库内最新业务时间：`2026-04-20 00:00:00`（LLM 时间计算锚点）
- 存在有效地区：`南通市` / `如东县` / `镇江市` / `镇江经开区`
- 存在有效设备：`SNS00204333` / `SNS00213807`
- 事实查询统一按 `create_time` 过滤和排序

---

## 必须重点抽查的 13 个断言

1. 非业务输入（问候/越界/闲聊）不得触发 Tool 调用
2. `guidance_answer` 默认不写 `agent_query_log`
3. "现在/当前/最新"必须以库内最新业务时间为锚点，不得用系统时间
4. "这批/本批"不再作为查询能力，应引导用明确时间窗问法
5. 业务问题未调用 Tool 直接回答 → `fallback_answer`（fallback_reason=tool_missing）
6. 概览回答默认不直接暴露样本数、最新业务时间、数据来源
7. 排名回答默认不直接暴露内部 `alert_count` 字段名或排序算法说明
8. `query_soil_ranking` 返回的 `items` 必须真正排序（rank=1 严重度最高）
9. `diagnose_empty_result` 须区分 `entity_not_found` 与 `no_data_in_window`
10. `tool_trace` / `answer_facts` / `query_result` 三个证据字段必须存在
11. `output_mode` 字段存在且值在合法集合内（`normal` / `anomaly_focus` / `warning_mode` / `advice_mode`）
12. 工具参数校验：top_n > 20 或时间窗 > 365 天（device）必须 raise ToolValidationError
13. 数字、时间、地区、设备号必须通过 `DataFactChecker`，不能漂移

---

## 什么时候必须补 Case

出现以下任一情况，必须在 `case-library.md` 补回归样例：

- 新增了 `input_type`、`intent` 或 `answer_type`
- 新增了 Tool、调整了 Tool 参数或返回结构
- 调整了地区解析或设备识别逻辑
- 修复了线上 Bug（且 Bug 可稳定复现）
- 调整了"是否写查询日志"的策略

---

## Case 设计要求

每个新 Case 至少回答以下问题：

| 问题 | 说明 |
|------|------|
| 用户怎么问？ | 真实用法，不要写过于工整的问题 |
| 是否依赖上下文？ | 多轮 Case 需标注上下文来源 |
| 预期命中哪个 Tool？ | `query_soil_summary` / `query_soil_ranking` / `query_soil_detail` / `diagnose_empty_result` / 无 |
| 预期 output_mode？ | `normal` / `anomaly_focus` / `warning_mode` / `advice_mode` |
| 回答归属哪个 answer_type？ | 明确的 answer_type 值（5 类之一） |
| guidance_reason / fallback_reason？ | 当 answer_type=guidance_answer 或 fallback_answer 时需填 |
| 最关键的断言是什么？ | 1~2 条最重要的 assert |

**加权原则：** 概览、排名对比、地区/设备详情、异常分析、预警模板加密；非业务、安全提示、能力边界只保留代表性样例。

---

## 商务评审模式

给商务/产品同事发测时：

**他们需要关注：**
- 问法是否像真实用户会说的话
- 回答是否能直接被业务理解和使用
- 异常/预警类输出是否符合日常沟通习惯
- 澄清/无数据/超范围时的回复是否合理

**他们不需要关注：**
- Tool 名称、内部路由、证据字段、代码实现

**高质量反馈格式：**
> "这条预警回答太像技术说明，不像发给业务人员的话术，建议更口语一点。"
> "这条地区详情先讲背景，结论太靠后，建议先给结论再给解释。"

**评审反馈分类：**
- **表达优化** → 回写到回答策略与 case-library 当前回答
- **能力缺口** → 回写到 `apps/agent/plans/` 能力设计，再同步更新 case-library

**配套材料：** 提供简化 Excel（只保留问题分类、用户问法、系统回答、是否符合预期、备注），不要发完整 case-library。
