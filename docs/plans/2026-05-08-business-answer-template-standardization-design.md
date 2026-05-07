# Business Answer Template Standardization Design

**Date:** 2026-05-08

## Goal

统一 Soil Agent 业务回答模板的文本结构，让设备台账、预警规则、预警分布、预警数量、预警处置和模板输出这几类回答在真实页面里呈现出一致的阅读节奏。

## Scope

本轮只收口“业务模板型回答”的文本格式，不改数据库 schema，不改路由判定，不重做 block 结构。重点覆盖以下能力：

- `device_registry_count`
- `device_registry_distribution`
- `device_registry_county_detail`
- `warning_rule_description`
- `warning_list`
- `warning_group`
- `warning_count`
- `warning_disposal`
- `template_output`

`summary / detail / compare / field` 暂不强制改成同一套公文模板，只保留现有较自然的表达。

## Chosen Format

采用统一的三段式 Markdown 模板：

1. 总述句
2. 明细列表
3. 说明锚点

### 1. 总述句

第一段固定回答三个问题：

- 查的是什么范围
- 得到的是什么核心结论
- 总量或状态是什么

示例：

- `截至当前，苏农云指挥调度中心已接入 528 套土壤墒情仪设备。`
- `最近7天江苏省全省内共出现 44 条满足当前预警规则的墒情预警信息。`

### 2. 明细列表

有枚举型结果时，统一用 Markdown 列表展示，不再混用长段落和裸数字序号：

- `- 南京市：48 套`
- `- 徐州市睢宁县：涝渍预警 9 条`
- `- 已处理：12 条`

没有可枚举明细时，可以省略这一段。

### 3. 说明锚点

最后一段固定承接“为什么是这样”或“如何理解这组数据”，按能力类型选择：

- 规则类：固定话术说明判定标准
- 预警类：固定补一句“以上结果均按当前预警规则筛选”
- 处置类：固定说明“展示顺序为已处理、待处理、超时已处理、超时待处理”
- 模板输出类：保留当前模板正文，不额外拼接杂项说明

## Formatting Rules

- 统一优先使用 Markdown `-` 列表，不再手拼 `1. 2. 3.` 文本。
- 总述句尽量一行说完，不在同一段反复追加“当前”“另外”“其中”。
- 规则说明避免暴露内部实现元数据，如 `rule_code`、更新时间、详情标签。
- 设备类回答保持“截至当前”作为固定前缀。
- 预警类回答保持“满足当前预警规则”作为固定锚点。
- 处置类回答保持四状态固定顺序。

## Implementation Strategy

- 在 `data_answer_service.py` 中增加少量通用文本 helper，统一拼装“总述 + 列表 + 说明锚点”。
- 各 reply 分支尽量只负责准备事实数据，不各自手写长段文本。
- 现有 block 数据结构尽量不动，只更新 `final_text`。

## Risks

- 现有单测里有不少 `final_text` 精确断言，需要同步更新。
- 页面如果对 Markdown 渲染不完整，列表格式会受影响；因此需要一起回归本地聊天页。

## Success Criteria

- 同类业务问题在页面里的文本结构一致。
- 正式验收模板对应的回答不再出现“同类能力不同文风”的情况。
- 单测与文档同步更新，不出现“代码改了、说明没改”的漂移。
