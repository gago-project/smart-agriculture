# 墒情 Agent 测试文档

本目录用于存放 `soil-moisture` Agent 的测试规则、验收说明和评审指引，和 `apps/agent/plans/` 中的能力设计文档分层维护：

- `apps/agent/plans/` 只保留 Agent 能力、架构、实现与风险契约。
- `docs/testing/agent/soil-moisture/` 统一承载测试规则、验收说明、回归策略、业务评审指引。
- `testdata/agent/soil-moisture/` 承载唯一主 Case 库。
- `outputs/` 只保留一次性测试产物，不作为长期设计文档入口。

## 权威依据

- Agent 总方案：`apps/agent/plans/1/1.plan.md`
- 回答类型与业务边界：`apps/agent/plans/1/2.answer-types-business.md`
- Flow 风险契约：`apps/agent/plans/1/8.flow-risk-contract.md`
- 数据库与地区别名设计：`infra/mysql/docs/README.md`

如测试文档与实现不一致，应优先核对代码、初始化 SQL 与主方案文档，再同步回写本目录。

## 目录索引

- [`acceptance-test-matrix.md`](./acceptance-test-matrix.md)：验收使用说明，定义前置假设、分类覆盖、关键断言与执行方式；完整 Case 主库不再放在这里。
- [`regression-case-guide.md`](./regression-case-guide.md)：回归样例扩展与维护规则，说明哪些变更必须补 Case、如何分层回归。
- [`business-review-guide.md`](./business-review-guide.md)：给商务/产品评审时的使用说明，帮助聚焦“问法是否自然、回答是否能用、模板是否贴近业务”。

## 使用建议

- 研发联调：先看 `testdata/agent/soil-moisture/case-library.md`，再结合 `acceptance-test-matrix.md` 和 `apps/agent/plans/1/5.python-implementation-plan.md` 核对链路。
- QA 回归：按 `regression-case-guide.md` 维护冒烟、验收、专项回归三层用例。
- 商务评审：优先使用 `business-review-guide.md`，避免直接阅读实现细节文档。

## 维护原则

- 新增或调整 Agent 能力时，先更新 `apps/agent/plans/` 的能力设计，再同步更新本目录测试口径。
- 新增或修订正式 Case 时，只改 `testdata/agent/soil-moisture/case-library.md`，不要在 `docs/testing` 再维护第二份完整样例。
- 新增真实回归样例时，优先沉淀到 `testdata/agent/soil-moisture/`，不要把长期样例放进 `outputs/`。
- 文档只描述当前已落地能力；未来计划需要明确标注为“未落地”。
