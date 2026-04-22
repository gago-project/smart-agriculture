# 墒情 Agent 验收测试说明

本文件用于说明 `soil-moisture` Agent 的验收口径、执行方式与重点断言，不再承载完整 Case 明细。

完整正式 Case 主库见：

- `testdata/agent/soil-moisture/case-library.md`

## 1. 文档定位

- 正式 Case 主库：`testdata/agent/soil-moisture/case-library.md`
- 测试规则与验收说明：`docs/testing/agent/soil-moisture/`
- 一次性导出结果：`outputs/`

从现在开始：

- 正式 Case 的新增、删减、修订，只改 `case-library.md`
- 不要再在本文件里维护第二套完整矩阵

## 2. 正式 Case 主库范围

当前正式主库以 `120` 个 Case 为准，其中前 `36` 个来自 `2026-04-22` 商务评审版，后续又在同一主库内补充了 `84` 个正式样本。

分类覆盖不按 10 类均分，而是按业务价值和真实使用频率加权：墒情概览、排名对比、地区/设备详情、异常分析、预警模板输出保留更多样例；非业务、安全提示、能力边界只保留少量代表性样例。

覆盖分类如下：

| 一级分类 | Case 数 |
|---|---:|
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

如需查看每个 Case 的：

- 用户问题
- 当前回答
- `input_type / intent / slots / query_type`
- `ExecutionGate / answer_type / 日志写入 / 关键断言`

请直接查看 `testdata/agent/soil-moisture/case-library.md`。

## 3. 测试前置假设

- 默认时区：`Asia/Shanghai`
- 默认库内最新业务时间：`2026-04-20 00:00:00`
- 默认已存在有效地区：
  - `南通市`
  - `如东县`
  - `镇江市`
  - `镇江经开区`
- 默认地区解析支持静态 alias 种子：
  - `南京 -> 南京市`
  - `南通 -> 南通市`
  - `如东 -> 如东县`
- 默认地区解析支持轻度模糊兜底，但只允许**唯一高置信**的一编辑距离命中；多候选必须澄清
- 默认已存在有效设备：
  - `SNS00204333`
  - `SNS00213807`
- 默认存在最近导入批次，且 `fact_soil_moisture.batch_id` 已正确关联 `etl_import_batch.batch_id`
- 默认所有事实查询只查当前有效数据
- 默认 `ExecutionGate` 生效：
  - 排名类最大时间窗 `365` 天
  - 异常类最大时间窗 `180` 天
  - 详情/趋势类最大时间窗 `90` 天
  - `TopN` 最大值 `20`
  - 不允许无约束全省全表扫描
  - 不允许批量设备趋势查询

## 4. 必须重点抽查的 13 个断言

- 非业务输入不得触发 SQL。
- `safe_hint_answer`、`clarification_answer`、`boundary_answer` 默认不写 `agent_query_log`。
- “现在 / 当前 / 最新”必须先取库内最新业务时间。
- “这一批”必须优先按 `batch_id` 解析。
- 异常 SQL 只拉候选，最终异常统计必须以 `RuleEngine` 结果为准。
- 概览回答默认不直接暴露样本数、最新业务时间、数据来源。
- 排名回答默认不直接暴露 `soil_anomaly_score`、异常分或内部排序字段名。
- 异常回答默认不直接点名 `SoilStatusRuleEngine` 等内部规则组件。
- `soil_warning_answer` 未命中时，内部返回应是 `soil_status=not_triggered`、`warning_level=none`。
- 模板 `strict_mode` 下，正文不能被自由改写。
- 上下文继承只允许白名单槽位，且最近 1~2 轮高置信，3~5 轮弱继承。
- `ExecutionGate` 超限后不得继续调用 `SoilDataQueryTool`。
- 数字、时间、地区、设备号必须通过 `DataFactChecker`，不能漂移。

## 5. 技术专项补充检查点

以下内容如发生实现变更，建议在正式 `120` Case 之外做专项抽查，但不再单独维护为第二套正式 Case 库：

- 地区别名、简称补全、轻度模糊解析
- 大范围趋势查询与批量设备趋势查询门禁
- 过大时间窗下的异常/排名阻断与澄清

## 6. 建议执行方式

- 第一轮：先跑 `testdata/agent/soil-moisture/case-library.md` 中的 `120` 个正式 Case。
- 第二轮：对其中需要查库的 Case，补真实数据断言，检查数值与模板输出是否一致。
- 第三轮：如本次改动涉及地区解析或生产保护门禁，额外补做专项抽查。

一句话结论：

> 正式维护入口只有一个：`testdata/agent/soil-moisture/case-library.md`。
