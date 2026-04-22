# 墒情 Agent 能力方案包（`plans/1`）

本目录用于存放围绕「墒情（土壤墒情）Agent MVP」的能力设计、工程方案、架构图与风险契约。历史编号保留为 `1`、`2`、`4`～`8`；原测试矩阵已迁移到 `docs/testing/agent/soil-moisture/`，数据库表设计和地区别名解析的数据库侧说明已迁移到 `infra/mysql/docs`。

---

## 文档索引（能力设计）

| 序号 | 文件 | 用途简述 | 主要读者 |
|:---:|---|---|---|
| **1** | [`1.plan.md`](./1.plan.md) | **总实施方案**：目标、架构（主控 Agent + 受限 Flow + 工具）、技术栈、数据与规则来源、交付范围（做/不做）、全局约束与命名约定等，是整套方案的「母文档」。 | 研发 / 架构 / 产品（通读） |
| **2** | [`2.answer-types-business.md`](./2.answer-types-business.md) | **10 类回答类型与业务对照表**：用户怎么问、对应 `intent`、是否查库/规则/模板、系统动作与输出重点，供商务、产品、运营确认行为边界（偏业务确认，不要求按实现细节读）。 | 商务 / 产品 / 运营 |
| **4** | [`4.python-flow-design.md`](./4.python-flow-design.md) | **Python 工程方案**：在文档 1 之上说明如何用 Python + **自研受限 Flow** 落地（不引入 LangChain/LangGraph 的阶段性理由）、目录与分层、状态与节点职责等工程设计。 | 研发 / 架构 |
| **5** | [`5.python-implementation-plan.md`](./5.python-implementation-plan.md) | **Python 实施计划**：按 Task 拆分的具体落地清单（文件、依赖、顺序），与文档 4 配套，指导从项目初始化到 Task 16 测试接入的编码步骤。 | 研发 |
| **6** | [`6.python-pseudocode.md`](./6.python-pseudocode.md) | **Python 实现伪代码**：补充文档 4、5 的「怎么写」——`FlowState`、Runner/Router、核心节点与 Service、Repository、Redis 上下文、`/chat` 入口等骨架与执行顺序（非完整可运行代码）。 | 研发 |
| **7** | [`7.system-design-diagram.md`](./7.system-design-diagram.md) | **系统设计图**：把文档 1～6 收敛成可对齐多方（研发/测试/运维/产品）的**架构与主链路**说明，含 Mermaid 图、模块职责、轻量可靠性与失败降级口径。 | 全员（对齐理解） |
| **8** | [`8.flow-risk-contract.md`](./8.flow-risk-contract.md) | **Flow 风险契约与补强方案**：在文档 1/4/5/6/7 基础上，写清自研 Flow 相对图框架多出来的工程风险（路由、状态合并、重试回路、上下文继承、知识污染事实等）及**必须遵守的契约与最少测试**，不推翻架构、补齐安全边界。 | 研发 / 架构 / 测试 |
---

## 已迁移文档

- 数据库表设计入口：`infra/mysql/docs/README.md`
- 地区别名解析设计：`infra/mysql/docs/region-alias-resolution.md`
- 测试文档入口：`docs/testing/agent/soil-moisture/README.md`
- 验收测试矩阵：`docs/testing/agent/soil-moisture/acceptance-test-matrix.md`

---

## 阅读建议

- **快速建立全局认识**：读 **1** → **7**。
- **和业务方对齐「怎么答」**：**2**。  
- **开发设计**：**1**、**4**、**5**、**6**、**7**、**8** 对照实现。
- **测试与验收**：查看 `docs/testing/agent/soil-moisture/`；数据库表结构和地区别名解析补充说明见 `infra/mysql/docs`。
