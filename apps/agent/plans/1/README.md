# 墒情 Agent 方案包（`plans/1`）

本目录是一套围绕「墒情（土壤墒情）Agent MVP」的配套文档，编号 `1`～`9` 表示推荐阅读与落地顺序：**业务与总方案 → 业务对齐表 → 验收矩阵 → Python 工程与实施 → 伪代码 → 架构图 → 风险契约 → 地区别名补全设计**。实现代码在 `apps/agent` 中演进时，可对照这些文件核对范围与验收口径。

---

## 文档索引（1～9）

| 序号 | 文件 | 用途简述 | 主要读者 |
|:---:|---|---|---|
| **1** | [`1.2026-04-20-soil-moisture-agent-plan.md`](./1.2026-04-20-soil-moisture-agent-plan.md) | **总实施方案**：目标、架构（主控 Agent + 受限 Flow + 工具）、技术栈、数据与规则来源、交付范围（做/不做）、全局约束与命名约定等，是整套方案的「母文档」。 | 研发 / 架构 / 产品（通读） |
| **2** | [`2.2026-04-20-soil-moisture-agent-answer-types-business.md`](./2.2026-04-20-soil-moisture-agent-answer-types-business.md) | **10 类回答类型与业务对照表**：用户怎么问、对应 `intent`、是否查库/规则/模板、系统动作与输出重点，供商务、产品、运营确认行为边界（偏业务确认，不要求按实现细节读）。 | 商务 / 产品 / 运营 |
| **3** | [`3.2026-04-20-soil-moisture-agent-task16-test-matrix.md`](./3.2026-04-20-soil-moisture-agent-task16-test-matrix.md) | **Task 16 验收测试矩阵（通关版）**：前置假设 + 多类典型用例表，每例落到 `input_type`、`intent`、`slots`、`query_type`/SQL、`answer_type`、规则、日志与关键断言，用于研发 / 测试 / 产品联调验收。 | 研发 / 测试 / 产品 |
| **4** | [`4.2026-04-20-soil-moisture-agent-python-flow-design.md`](./4.2026-04-20-soil-moisture-agent-python-flow-design.md) | **Python 工程方案**：在文档 1 之上说明如何用 Python + **自研受限 Flow** 落地（不引入 LangChain/LangGraph 的阶段性理由）、目录与分层、状态与节点职责等工程设计。 | 研发 / 架构 |
| **5** | [`5.2026-04-20-soil-moisture-agent-python-implementation-plan.md`](./5.2026-04-20-soil-moisture-agent-python-implementation-plan.md) | **Python 实施计划**：按 Task 拆分的具体落地清单（文件、依赖、顺序），与文档 4 配套，指导从项目初始化到 Task 16 测试接入的编码步骤。 | 研发 |
| **6** | [`6.2026-04-20-soil-moisture-agent-python-pseudocode.md`](./6.2026-04-20-soil-moisture-agent-python-pseudocode.md) | **Python 实现伪代码**：补充文档 4、5 的「怎么写」——`FlowState`、Runner/Router、核心节点与 Service、Repository、Redis 上下文、`/chat` 入口等骨架与执行顺序（非完整可运行代码）。 | 研发 |
| **7** | [`7.2026-04-20-soil-moisture-agent-system-design-diagram.md`](./7.2026-04-20-soil-moisture-agent-system-design-diagram.md) | **系统设计图**：把文档 1～6 收敛成可对齐多方（研发/测试/运维/产品）的**架构与主链路**说明，含 Mermaid 图、模块职责、轻量可靠性与失败降级口径。 | 全员（对齐理解） |
| **8** | [`8.2026-04-21-soil-moisture-agent-flow-risk-contract.md`](./8.2026-04-21-soil-moisture-agent-flow-risk-contract.md) | **Flow 风险契约与补强方案**：在文档 1/4/5/6/7 基础上，写清自研 Flow 相对图框架多出来的工程风险（路由、状态合并、重试回路、上下文继承、知识污染事实等）及**必须遵守的契约与最少测试**，不推翻架构、补齐安全边界。 | 研发 / 架构 / 测试 |
| **9** | [`9.2026-04-22-soil-region-alias-resolution-design.md`](./9.2026-04-22-soil-region-alias-resolution-design.md) | **地区别名补全与轻度模糊识别设计**：补充 `region_alias` 表、静态 SQL 种子、简称补全、唯一高置信错字纠正、多候选澄清的实现边界，保证地区解析能力与当前 Agent 实现一致。 | 研发 / 测试 / 产品 |

---

## 阅读建议

- **快速建立全局认识**：读 **1** → **7** → **9**。
- **和业务方对齐「怎么答」**：**2**。  
- **开发与验收**：**3** 与 **5** 对照实现；**4**、**6** 解决结构与写法；涉及地区简称、别名、错字补全时同步参考 **9**；上线前用 **8** 做风险与契约检查。
