# 墒情 Agent 能力方案包（`plans/1`）

本目录用于存放围绕「墒情（土壤墒情）Agent MVP」的能力设计、工程方案、架构图与风险契约。历史编号保留为 `1`、`2`、`4`～`9`；当前测试入口以 `testdata/agent/soil-moisture/README.md` 与对应 QA skill/rule 为准，数据库表设计和地区别名解析的数据库侧说明已迁移到 `infra/mysql/docs`。

---

## 文档索引（能力设计）

| 序号 | 文件 | 用途简述 | 主要读者 |
|:---:|---|---|---|
| **1** | [`1.plan.md`](./1.plan.md) | **总实施方案**：目标、架构（主控 Agent + 受限 Flow + 工具）、技术栈、数据与规则来源、交付范围（做/不做）、全局约束与命名约定等，是整套方案的「母文档」。 | 研发 / 架构 / 产品（通读） |
| **2** | [`2.answer-types-business.md`](./2.answer-types-business.md) | **【已归档】历史 11 类回答类型与业务对照表**：旧管线的 intent/tool/输出格式对照，供历史参考。当前已收口为 `5` 个一级 `answer_type`（`soil_summary_answer` / `soil_ranking_answer` / `soil_detail_answer` / `guidance_answer` / `fallback_answer`）+ `output_mode` / `guidance_reason` / `fallback_reason` 辅助字段。 | 商务 / 产品（历史参考） |
| **4** | [`4.python-flow-design.md`](./4.python-flow-design.md) | **Python 工程方案**：在文档 1 之上说明如何用 Python + **自研受限 Flow** 落地（不引入 LangChain/LangGraph 的阶段性理由）、目录与分层、状态与节点职责等工程设计。 | 研发 / 架构 |
| **5** | [`5.python-implementation-plan.md`](./5.python-implementation-plan.md) | **已归档的旧 Python 实施计划**：保留旧版受限 Flow 的 Task 拆分与历史实施路径，当前版本不要单独依赖本文件推进实现。 | 研发（历史参考） |
| **6** | [`6.python-pseudocode.md`](./6.python-pseudocode.md) | **已归档的旧 Python 伪代码**：保留旧版受限 Flow 的代码骨架参考，当前版本请优先以文档 1、4、8、9 为准。 | 研发（历史参考） |
| **7** | [`7.system-design-diagram.md`](./7.system-design-diagram.md) | **系统设计图**：把文档 1～6 收敛成可对齐多方（研发/测试/运维/产品）的**架构与主链路**说明，含 Mermaid 图、模块职责、轻量可靠性与失败降级口径。 | 全员（对齐理解） |
| **8** | [`8.flow-risk-contract.md`](./8.flow-risk-contract.md) | **Flow 风险契约与补强方案**：在文档 1/4/5/6/7 基础上，写清自研 Flow 相对图框架多出来的工程风险（路由、状态合并、重试回路、上下文继承、知识污染事实等）及**必须遵守的契约与最少测试**，不推翻架构、补齐安全边界。 | 研发 / 架构 / 测试 |
| **9** | [`9.llm-fc-design-audit.md`](./9.llm-fc-design-audit.md) | **LLM + FC 设计审计与整改建议**：对照当前正式设计与 live path 实现，梳理不对齐项、遗留区、Function Calling 风险、上下文风险、工具语义问题与整改优先级，适合作为后续架构收口的执行入口。 | 研发 / 架构 / 测试 |
---

## 已迁移文档

- 数据库表设计入口：`infra/mysql/docs/README.md`
- 地区别名解析设计：`infra/mysql/docs/region-alias-resolution.md`
- 测试与 Case 入口：`testdata/agent/soil-moisture/README.md`（当前为单一正式验收库，30 条 Case，每次全量执行）
- QA / 验收 skill 入口：`.claude/skills/soil-moisture-qa/SKILL.md`（以及 `.codex` / `.agents` / `.cursor` 同步副本）

---

## 阅读建议

- **快速建立全局认识**：读 **1** → **7**。
- **和业务方对齐「怎么答」**：**2**。  
- **开发设计**：优先阅读 **1**、**4**、**7**、**8**、**9**；**5**、**6** 仅作历史参考。
- **测试与验收**：查看 `testdata/agent/soil-moisture/` 与 soil-moisture QA skill；数据库表结构和地区别名解析补充说明见 `infra/mysql/docs`。
