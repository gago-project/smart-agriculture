# 墒情 Agent 测试数据目录

本目录存放 `soil-moisture` Agent 的**唯一正式验收库**与对应维护说明。

## 当前正式入口

- `testdata/agent/soil-moisture/case-library.md`

## 当前正式规模

- 正式 Case 总数：`30`
- 测试方式：**每次全量跑完 30 条**
- 测试定位：**单元测试导向**
- 当前回答样例：**保留完整长文本**
- 数据真实性：**每条业务 Case 都必须带数据库校验断言，并标记 `是否符合事实`**

## 分布结构

| 一级 `answer_type` | 数量 | CaseID |
|---|---:|---|
| `guidance_answer` | 8 | `SM-CONV-001 ~ SM-CONV-008` |
| `soil_summary_answer` | 6 | `SM-SUM-001 ~ SM-SUM-006` |
| `soil_ranking_answer` | 4 | `SM-RANK-001 ~ SM-RANK-004` |
| `soil_detail_answer` | 8 | `SM-DETAIL-001 ~ SM-DETAIL-008` |
| `fallback_answer` | 4 | `SM-FB-001 ~ SM-FB-004` |

## 维护原则

- 旧三层测试模型已废弃
- 不再维护第二套正式 Case 主库
- 不再保留旧 `130` 条正式库
- 不再保留旧 `CaseID` 体系
- 正式 Case 的新增、删减、修订只改 `case-library.md`

## Case 设计要求

每条正式 Case 至少保留以下字段：

- `CaseID`
- `用户问题`
- `当前回答`
- `上下文`
- `预期 input_type`
- `是否域内业务问题`
- `是否必须命中 Tool`
- `预期 Tool`
- `预期 answer_type`
- `预期 output_mode`
- `预期 guidance_reason`
- `预期 fallback_reason`
- `是否写查询日志`
- `关键断言`
- `结构化证据断言`
- `数据库校验断言`
- `是否符合事实`
- `备注`

## 数据真实性要求

- `guidance_answer` 等非业务 Case 不要求查库，但不得包含事实性业务断言
- 每条业务 Case 都必须能落到：
  - `问题 -> Agent 回答 -> 回查数据库 -> 事实比对`
- 对正式通过样例：
  - 业务 Case：`是否符合事实=是`
  - 非业务 guidance Case：若不含事实性业务断言，也记为 `是`

## 相关 QA 入口

- `.claude/skills/soil-moisture-qa/SKILL.md`
- `.codex/skills/soil-moisture-qa/SKILL.md`
- `.agents/skills/soil-moisture-qa/SKILL.md`
- `.cursor/rules/soil-moisture-qa.mdc`

## 其他说明

- `outputs/` 仍只放一次性测试结果，不作为长期规则源
- 如未来确实需要结构化导出，再考虑新增 `json/csv/xlsx` 副本；当前仍以 Markdown 主库为准
