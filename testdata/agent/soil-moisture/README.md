# 墒情 Agent 测试数据目录

本目录存放 `soil-moisture` Agent 的**唯一正式验收库**与对应维护说明。

## 正式入口

- `testdata/agent/soil-moisture/case-library.md`

## 正式规模

- 正式 Case 总数：`56`
- 测试方式：**每次全量跑完 56 条**
- 测试定位：**单元测试导向**
- 当前回答样例：**保留完整长文本**
- 数据真实性：**每条业务 Case 都必须带数据库校验断言，并标记 `是否符合事实`**

## 分布结构

| 章节 | 数量 | CaseID |
|---|---:|---|
| Guidance Cases | 15 | `SM-CONV-001 ~ SM-CONV-015` |
| Summary Cases | 10 | `SM-SUM-001 ~ SM-SUM-010` |
| Ranking Cases | 8 | `SM-RANK-001 ~ SM-RANK-008` |
| Detail Cases | 13 | `SM-DETAIL-001 ~ SM-DETAIL-013` |
| Fallback Cases | 10 | `SM-FB-001 ~ SM-FB-010` |

## 维护原则

- 只维护这一套正式 Case 主库
- 正式 Case 总数固定为 `56`
- 正式 Case 编号统一使用 `SM-*` 体系
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
- 正式门禁：见 `.claude/skills/soil-moisture-qa/SKILL.md`「发布前正式门禁」；仓库根目录可执行 `npm run qa:soil:formal`

## 其他说明

- `outputs/` 仍只放一次性测试结果，不作为长期规则源
- 当前正式库已覆盖 `最近13天 / 近2周 / 近3月 / 过去21天 / 两周 / 三个月` 等相对时间，以及 `这几天 / 最近400天 / 开始时间晚于结束时间` 的统一澄清口径
- 如未来确实需要结构化导出，再考虑新增 `json/csv/xlsx` 副本；当前仍以 Markdown 主库为准
