# Soil Moisture Case Library Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Update: after the initial unification to a 36-case single source, the formal case library was further expanded in-place to `120` cases. The 120-case distribution is business-weighted rather than evenly split across categories.

**Goal:** 将墒情 Agent 的两套 Case 文档收敛为以 `36` 个商务评审 Case 为准的唯一 Markdown 主库，并把 `docs/testing` 调整为纯说明层。

**Architecture:** 从商务评审 Excel 中提取 `36` 个正式 Case 的分类、问题与当前回答，再与现有研发验收矩阵中相同 `CaseID` 的结构化期望字段合并，生成 `testdata/agent/soil-moisture/case-library.md`。随后把 `docs/testing` 下相关文档改成围绕唯一主库的入口与说明，不再保留第二套完整矩阵。

**Tech Stack:** Markdown、Python（只做一次性数据提取）、`node:test`

---

### Task 1: 固化唯一主库口径

**Files:**
- Create: `docs/plans/2026-04-22-soil-moisture-case-library-design.md`
- Create: `docs/plans/2026-04-22-soil-moisture-case-library.md`

**Step 1: 写清设计结论**

把“唯一主库以 `36` 个商务评审 Case 为准”的设计写入正式文档，明确目录职责与迁移规则。

**Step 2: 写清实施计划**

把本次文档收敛需要修改的文件、迁移顺序和验证方式写成实施计划，避免后续又回到双写状态。

### Task 2: 生成唯一主库文件

**Files:**
- Create: `testdata/agent/soil-moisture/case-library.md`
- Modify: `testdata/agent/soil-moisture/README.md`

**Step 1: 提取 36 Case 基础字段**

从 `outputs/business-review-20260422/smart-agriculture-36问题-商务评审版-2026-04-22.xlsx` 提取：

- `CaseID`
- `一级分类`
- `二级分类`
- `用户问题`
- `当前回答`

**Step 2: 补齐结构化测试字段**

从 `docs/testing/agent/soil-moisture/acceptance-test-matrix.md` 中按相同 `CaseID` 补齐：

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

**Step 3: 生成 Markdown 主库**

以 `## 一级分类` + `### CaseID` 的方式生成 `case-library.md`，确保后续人工维护时不需要修改超宽大表格。

**Step 4: 更新 testdata README**

在 `testdata/agent/soil-moisture/README.md` 中明确：

- `case-library.md` 是唯一维护入口
- `outputs/` 不再视为长期源数据

### Task 3: 把 testing 目录改成说明层

**Files:**
- Modify: `docs/testing/agent/soil-moisture/README.md`
- Modify: `docs/testing/agent/soil-moisture/acceptance-test-matrix.md`
- Modify: `docs/testing/agent/soil-moisture/regression-case-guide.md`

**Step 1: 更新 testing README**

明确 `docs/testing` 只负责：

- 测试规则
- 验收方式
- 回归补 Case 规范

并把完整 Case 主库入口指向 `testdata/agent/soil-moisture/case-library.md`。

**Step 2: 精简 acceptance-test-matrix**

删除完整 `44` Case 表格，改为：

- 测试前置假设
- 主库说明
- `36` Case 分类覆盖
- 高风险断言
- 执行建议

**Step 3: 更新 regression-case-guide**

明确新增和修订 Case 时，统一改 `case-library.md`，不再在 `docs/testing` 里维护第二份完整样例。

### Task 4: 校验引用与契约

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`

**Step 1: 调整文档契约测试**

把“验收与地区别名文档位于独立目录”契约扩展为：

- `docs/testing` 存在说明入口
- `testdata/agent/soil-moisture/case-library.md` 存在且作为唯一主库

**Step 2: 运行验证**

Run: `node --test apps/web/tests/file-contract.test.mjs`

Expected: PASS

### Task 5: 全仓一致性检查

**Files:**
- No new code files

**Step 1: 搜索残留双写口径**

Run: `rg -n "44 个典型 Case|商务评审版|case-library.md|36 个 Case" apps docs testdata`

Expected: 结果与新的目录职责一致，不再存在另一份完整正式 Case 库。
