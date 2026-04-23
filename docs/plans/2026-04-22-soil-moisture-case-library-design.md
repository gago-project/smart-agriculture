# Soil Moisture Case Library Design

**Date:** `2026-04-22`

> Update: the single formal case library was later expanded from the original `36` business-review cases to `120` formal cases in the same Markdown source. The 120-case distribution is business-weighted rather than evenly split across categories.

## Background

当前仓库里实际并存两套墒情 Agent Case：

- `docs/testing/agent/soil-moisture/acceptance-test-matrix.md` 中的 `44` 个研发验收 Case
- `outputs/business-review-20260422/smart-agriculture-36问题-商务评审版-2026-04-22.xlsx` 中的 `36` 个对外商务评审 Case

这会带来两个问题：

- 后续新增或修订 Case 时，需要维护两套来源
- `docs/testing` 与 `testdata` 的边界不清，Case 数据和测试说明仍然混在一起

## Final Decision

本次统一后的唯一主库以 `36` 个商务评审 Case 为准。

原因：

- 这 `36` 个 Case 已经被拿去对外沟通，是当前最真实的“已使用口径”
- 用户明确要求后续只维护一套 Case
- `44` 个研发矩阵中的额外 `8` 个 Case，后续不再作为第二套正式 Case 库保留

## Directory Responsibilities

- `apps/agent/plans/`：只保留 Agent 能力设计、工程方案、风险契约
- `docs/testing/agent/soil-moisture/`：只保留测试规则、验收说明、回归维护说明
- `testdata/agent/soil-moisture/`：保留唯一主 Case 库
- `outputs/`：只保留一次性导出物，不作为长期维护来源

## Single Source of Truth

唯一主库文件：

- `testdata/agent/soil-moisture/case-library.md`

该文件承载：

- 当前 `130` 个正式 Case，其中新增多轮话题边界专项 Case 直接并入同一主库
- 每个 Case 的业务分类与测试期望
- 当前用于商务评审的“当前回答”样例

后续对 Case 的新增、删减、修订，都只改这个文件。

## Case Shape

每个 Case 使用固定模板，字段如下：

- `CaseID`
- `一级分类`
- `二级分类`
- `用户问题`
- `当前回答`
- `上下文`
- `预期 input_type`
- `预期 intent`
- `预期 slots`
- `预期 query_type / SQL`
- `ExecutionGate`
- `预期 answer_type`
- `规则触发`
- `是否写查询日志`
- `关键断言`
- `备注`

其中：

- `一级分类 / 二级分类 / 当前回答` 以 `36` Case 商务评审表为准
- 结构化测试字段以当前 `acceptance-test-matrix.md` 中对应 `CaseID` 的定义为准

## What Happens to the 44-Case Matrix

`docs/testing/agent/soil-moisture/acceptance-test-matrix.md` 不再保留完整 `44` 个 Case 表格。

它将改为“验收使用说明”文档，只保留：

- 测试前置假设
- 主库来源说明
- `36` Case 的分类覆盖说明
- 高风险重点断言
- 执行建议

原 `44` Case 中多出的地区别名与生产保护专项，不再作为第二套正式 Case 库存在；若仍需保留，只以“专项检查点”形式出现在测试说明文档中。

## Migration Rules

- 不修改业务代码、SQL、测试逻辑
- 不处理 `outputs/` 历史产物
- 原 `36` 个商务评审 Case 的 `CaseID` 保持不变
- 新增正式 Case 直接补入同一个 `case-library.md`，按业务价值加权分布，不按分类均分
- `docs/testing` 中不再保留另一套完整 Case 内容
- `testdata` 作为唯一主库入口，需要在 README 中明确写清

## Success Criteria

- 仓库内只有一套正式 Case 主库
- `testdata/agent/soil-moisture/case-library.md` 可直接作为维护入口
- `docs/testing` 只提供说明，不再构成第二套 Case 源
- 文档引用全部指向新的唯一主库
