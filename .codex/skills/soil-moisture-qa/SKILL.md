---
name: soil-moisture-qa
description: >
  Use when running QA, regression testing, or business review for the
  soil-moisture Agent. Covers three test layers (smoke / acceptance /
  specialist), when to run each, key assertions, how to extend the case
  library, and how to prepare for business review sessions.
---

# Smart Agriculture — 墒情 Agent QA Skill

## 测试资产分布（权威）

| 资产 | 路径 | 说明 |
|------|------|------|
| **正式 Case 主库** | `testdata/agent/soil-moisture/case-library.md` | **唯一入口**，所有新增/修订/删除只改这里 |
| Agent 能力方案 | `apps/agent/plans/1/1.plan.md` | 路由、能力设计 |
| 回答类型与业务边界 | `apps/agent/plans/1/2.answer-types-business.md` | intent → answer_type 映射 |
| Flow 风险契约 | `apps/agent/plans/1/8.flow-risk-contract.md` | ExecutionGate 规则 |
| 一次性测试产物 | `outputs/` | Excel/CSV/截图，不作为长期规则 |

**原则：** 测试文档与实现不一致时，优先核对代码和 SQL，再同步回写 case-library。

---

## 三层测试资产

### 冒烟层（每次改动后快速自测）

**目标：** 快速判断主链路是否还能跑通。

至少覆盖以下 5 类各 1 条：
- 概览问题（如："最近墒情怎么样"）
- 地区详情（如："南通市今天墒情"）
- 设备异常（如："SNS00204333 有没有异常"）
- 预警模板输出（如："生成一条南通的预警"）
- 兜底/澄清（如："帮我查一下大数据"）

**适用时机：**
- 本地改动后快速自测
- 部署前后快速验证
- 线上问题修复后最小复测

---

### 验收层（里程碑 / 合并主分支前）

**目标：** 验证 MVP 公开承诺的能力边界。

**当前主库：** `testdata/agent/soil-moisture/case-library.md`，共 **130 个 Case**。

| 分类 | Case 数 |
|------|--------:|
| A. 非业务 / 安全提示 | 6 |
| B. 澄清引导 | 8 |
| C. 墒情概览 | 15 |
| D. 排名对比 | 15 |
| E. 地区 / 设备详情 | 18 |
| F. 异常分析 | 16 |
| G. 预警模板输出 | 16 |
| H. 指标解释 / 指导建议 | 11 |
| I. 无数据 / 找不到 / 兜底 | 10 |
| J. 能力边界 | 5 |
| K. 多轮话题边界 | 10 |

**执行顺序：**
1. 第一轮：跑 case-library.md 全部 130 个 Case
2. 第二轮：对需要查库的 Case，补真实数据断言（数值与模板输出）
3. 第三轮：如本次改动涉及地区解析或 ExecutionGate，额外做专项抽查

**适用时机：** 里程碑验收、功能合并到主分支前、对商务/产品展示前。

---

### 专项回归层（高风险链路加密测试）

重点专项：
- 地区别名与轻度模糊解析
- 多轮上下文继承与衰减（最近 1~2 轮高置信，3~5 轮弱继承）
- ExecutionGate 超限拦截（排名 ≤ 365 天，异常 ≤ 180 天，TopN ≤ 20）
- 模板 strict_mode（正文不能被自由改写）vs 解释模式
- 查询日志写入 / 不写入边界
- 无数据 / 找不到对象 / 公共异常兜底

---

## 测试前置假设

在跑任何 Case 前，确认以下假设成立：

- 默认时区：`Asia/Shanghai`
- 库内最新业务时间：`2026-04-20 00:00:00`
- 存在有效地区：`南通市` / `如东县` / `镇江市` / `镇江经开区`
- 地区解析支持静态 alias：`南通 → 南通市`，`如东 → 如东县`，`南京 → 南京市`
- 地区解析支持唯一高置信的一编辑距离模糊命中，多候选必须澄清
- 存在有效设备：`SNS00204333` / `SNS00213807`
- 事实查询统一按 `create_time` 过滤和排序

---

## 必须重点抽查的 13 个断言

1. 非业务输入不得触发 SQL
2. `safe_hint_answer` / `clarification_answer` / `boundary_answer` 默认不写 `agent_query_log`
3. "现在/当前/最新"必须先取库内最新业务时间，不得用系统时间
4. "这批/本批"不再作为查询能力，应引导用明确时间窗问法
5. 异常 SQL 只拉候选，最终异常统计必须以 `RuleEngine` 结果为准
6. 概览回答默认不直接暴露样本数、最新业务时间、数据来源
7. 排名回答默认不直接暴露 `risk_score` 或内部排序字段名
8. 异常回答默认不直接点名 `SoilStatusRuleEngine` 等内部组件
9. `soil_warning_answer` 未命中时，内部返回应是 `soil_status=not_triggered`，`warning_level=none`
10. 模板 `strict_mode` 下，正文不能被自由改写
11. 上下文继承只允许白名单槽位，且最近 1~2 轮高置信，3~5 轮弱继承
12. `ExecutionGate` 超限后不得继续调用 `SoilDataQueryTool`
13. 数字、时间、地区、设备号必须通过 `DataFactChecker`，不能漂移

---

## 什么时候必须补 Case

出现以下任一情况，必须在 `case-library.md` 补回归样例：

- 新增了 `input_type`、`intent` 或 `answer_type`
- 新增了 SQL 模板、查询路由或门禁规则
- 调整了地区解析、简称补全、模糊匹配逻辑
- 调整了预警模板、异常判断规则或展示口径
- 修复了线上 Bug（且 Bug 可稳定复现）
- 调整了"是否写查询日志"的策略

---

## Case 设计要求

每个新 Case 至少回答以下问题：

| 问题 | 说明 |
|------|------|
| 用户怎么问？ | 真实用法，不要写过于工整的问题 |
| 是否依赖上下文？ | 多轮 Case 需标注上下文来源 |
| 预期命中哪个 intent？ | 明确的 intent 值 |
| 是否允许查库？ | ExecutionGate 判断 |
| 预期走哪个 query_type / SQL 模板？ | 具体模板编号 |
| 回答归属哪个 answer_type？ | 明确的 answer_type 值 |
| 最关键的断言是什么？ | 1~2 条最重要的 assert |

**加权原则：** 概览、排名对比、地区/设备详情、异常分析、预警模板加密；非业务、安全提示、能力边界只保留代表性样例。

---

## 商务评审模式

给商务/产品同事发测时：

**他们需要关注：**
- 问法是否像真实用户会说的话
- 回答是否能直接被业务理解和使用
- 模板类输出是否符合日常沟通习惯
- 澄清/无数据/超范围时的回复是否合理

**他们不需要关注：**
- SQL 模板编号、内部路由、门禁字段、代码实现

**高质量反馈格式：**
> "这条预警模板太像技术说明，不像发给业务人员的话术，建议更口语一点。"  
> "这条地区详情先讲背景，结论太靠后，建议先给结论再给解释。"

**评审反馈分类：**
- **表达优化** → 回写到问答模板与回答策略
- **能力缺口** → 回写到 `apps/agent/plans/` 能力设计，再同步更新 case-library

**配套材料：** 提供简化 Excel（只保留问题分类、用户问法、系统回答、是否符合预期、备注），不要发完整 case-library。
