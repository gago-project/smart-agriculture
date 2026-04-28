# Agent 能力分析与升级规划

> 分析时间：2026-04-28  
> 分析范围：LLM + Function Calling 重构后的 soil-moisture Agent  
> 重点关注：数据真实性（P0）、意图识别、对话上下文

---

## 一、当前架构概述

```
用户输入
  → InputGuard（规则分类）
  → AgentLoop（LLM + 工具调用）
  → DataFactCheck（答案核实）
  → AnswerVerify（完整性校验）
  → 返回用户
```

**核心原则**：LLM 负责理解意图 + 选择工具；工具负责查真实数据库；禁止 LLM 直接生成业务数据。

**关键组件**：

| 组件 | 文件 | 职责 |
|------|------|------|
| InputGuard | `services/input_guard_service.py` | 关键词规则分类，决定是否进入业务流程 |
| AgentLoop | `services/agent_loop_service.py` | LLM ↔ 工具调用循环，最多 5 次迭代 |
| 工具定义 | `llm/tools/soil_tools.py` | 4 个工具：summary / ranking / detail / diagnose |
| 数据库访问 | `repositories/soil_repository.py` | MySQL 异步查询，fact_soil_moisture 表 |
| 对话历史 | `repositories/session_context_repository.py` | Redis 存储，最多 20 条，TTL 2 小时 |
| DataFactCheck | `flow/nodes/data_fact_check.py` | 验证答案与工具证据一致性 |
| System Prompt | `llm/prompts/system_prompt.py` | 角色定义、规则约束、时间基准注入 |

---

## 二、总体升级原则

> **确定性治理优先，语义理解交给 LLM。**

不是"用规则替代 LLM"，而是明确分工边界：

| 层 | 职责 |
|----|------|
| **LLM** | 意图识别、指代消解、工具选择、答案组织 |
| **程序层** | 实体标准化、时间解析/校验、规则判定、空结果诊断、事实核验 |

LLM 擅长语义，不擅长精确计算和规则执行；程序层擅长确定性，不擅长语义理解。把这两件事分开，是整套系统能稳定运行的前提。

### Parameter Resolver 是整个方案的枢纽

新增 **Parameter Resolver** 层，位于 LLM 输出工具参数之后、ToolExecutor 之前：

```
LLM 输出工具参数
        ↓
  Parameter Resolver
    ├── 实体标准化（统一收口 RegionAlias 别名表）
    ├── 时间语义槽 → 绝对时间展开
    ├── 参数合法性校验（含安全硬上限）
    └── 置信度标记（entity_confidence, time_confidence）
        ↓
  ToolExecutor（只接收干净的参数）
```

**职责边界**：
- 实体标准化统一收口 `RegionAlias`，不新增第三套地名逻辑，避免三套规则并存
- 状态/风险判定统一收口 `metric_rule`，与实体标准化职责分离

这层一旦建好，其余改动都有基础设施：
- 空结果诊断能明确区分"标准化失败"和"查库无数据"
- FactCheck 逐项映射时有可信的"参数原文"作为基准
- 时间参数校验有了统一入口
- 多 tool_call 可对每个调用独立过 Resolver

---

## 三、缺陷分析

### P0 — 数据真实性

> 返回给用户的数据必须是真实的，这是最高优先级。

**1. 状态评估阈值写死在代码里，不走数据库规则表**

- 位置：`soil_repository.py`
- 现状：`water20cm < 50 → heavy_drought`、`≥ 150 → waterlogging` 硬编码在 Python
- 问题：`metric_rule` 表（`soil_anomaly_v1`、`soil_warning_v1`）存在但形同虚设；所有消费 `soil_status` / `warning_level` 的路径（排名、FactCheck、前端展示）都可能因此联动出错
- 风险：运营修改规则表不生效，系统仍按代码阈值判断，返回错误状态

**2. 实体名称无标准化，导致查询静默返回空**

- 位置：`tool_executor_service.py`
- 现状：工具参数（city/county/sn）由 LLM 直接填写，无规范化处理
- 问题：LLM 填"安徽"，数据库存"安徽省"；LLM 填"合肥"，数据库存"合肥市"
- 风险：查询返回空结果，系统误判为"该地区无数据"，实际上是参数有误，向用户返回错误结论

**3. 诊断工具的 scenario 由 LLM 自行选择，无验证**

- 位置：`llm/tools/soil_tools.py`（tool schema）+ `llm/prompts/system_prompt.py`（prompt 引导）+ FC 执行链路（共同导致）
- 现状：scenario 枚举（region_exists / device_exists / period_exists）由 LLM 自由决定
- 风险：LLM 选错 scenario，返回错误的空结果诊断结论（"地区不存在"实际是"时间段无数据"）

**4. 时间参数完全依赖 LLM 推算，无校验**

- 位置：`system_prompt.py` 注入 `latest_business_time`，LLM 自行计算相对时间
- 问题：LLM 算错"上周""前3天"等相对时间时，工具收到错误的时间窗口
- 风险：查询窗口错误但系统无感知，返回错误时段的数据，用户无法察觉

**5. 事实核验偏弱：有证据但细节答错无法检出**

- 位置：`fact_check_service.py`
- 现状：只校验"是否用了工具"、"实体名是否出现在答案里"、"别把有数据说成没数据"
- 问题：没有校验答案中的数值、状态、时间窗是否能逐项映射回工具结果
- 风险：用户看到"看起来很像真的错答案"，比完全没查库更危险，且难以发现

**6. 测试偏合同验证，缺真实性回归**

- 现状：测试数量不少，但多在测结构和返回字段；`test_region_alias_resolution_unittest.py` 没有真正验证别名标准化是否生效
- 问题：规则表、别名表、时间校验这些关键能力缺少强约束
- 风险：功能看起来在，真实性保障其实很脆，P0 问题容易静默回归

---

### P1 — 意图识别与执行稳定性

**7. InputGuard 是纯关键词规则，不是语义理解**

- 位置：`input_guard_service.py`
- 现状：基于字符串匹配和正则判断输入类型
- 问题：口语化表达识别率低；新表达方式需手动维护关键词列表
- 风险：合法业务问题被拦截，用户体验差

**8. 意图/答案类型由"第一把成功工具"反推，不稳定**

- 位置：`agent_loop.py` line 56
- 现状：`answer_type` / `intent` 基本由第一把成功工具反推
- 问题：多工具链路下，第一把工具不代表最终意图（如先诊断、再查详情，intent 可能被错标为诊断）
- 风险：日志统计失真；下游校验、埋点、产品分析被污染；后续意图驱动路由不稳定

**9. Qwen Function Calling 只消费第一条 tool_call**

- 位置：`qwen_client.py`
- 现状：模型一次返回多个 tool calls 时，只取第一条
- 问题：复合查询能力被提前卡死；模型规划对了，执行层悄悄丢动作
- 风险：多工具场景 silently degrade，难以排查

**10. 多轮指代消解完全依赖 LLM**

- 位置：`agent_loop_service.py`
- 现状：没有显式的指代解析步骤，"它""那个地区"直接进入 LLM 上下文
- 风险：LLM 在长对话中可能解析到错误的历史实体，工具参数填错

**11. 意图类型枚举固定，扩展成本高**

- 位置：`schemas/enums.py`
- 现状：`IntentType` 枚举固定，新增业务意图需同时改枚举 + system prompt + 工具定义
- 风险：业务扩展耦合重，容易遗漏改点

**12. 排名逻辑有领域偏置**

- 位置：`tool_executor_service.py`
- 现状：告警数相同时按 `avg_water20cm` 升序排，天然偏向"越干越严重"
- 问题：对涝渍风险不公平；"重旱"和"涝渍"混排时缺少统一风险度量
- 风险：排名结果业务含义不稳，用户误解"更严重"的定义

---

### P1 — 对话上下文

**13. 消息数量截断，不按 token 控制**

- 位置：`session_context_repository.py`，`_MAX_MESSAGES = 20`
- 问题：工具调用每轮产生 3-4 条消息，20 条只能撑 5-6 轮有效对话
- 风险：频繁工具调用场景下，早期重要上下文快速丢失

**14. 无上下文压缩/摘要机制**

- 位置：全局缺失
- 风险：超出窗口的历史直接丢弃，LLM 忘记"用户之前说的是安徽"，后续工具参数填错

**15. 会话 TTL 2 小时，无前端感知**

- 位置：`session_context_repository.py`，TTL = 7200
- 问题：用户中断超过 2 小时回来继续问，上下文已丢失但前端不提示
- 风险：用户以为 LLM 记得之前的对话，实际已从零开始，产生误解

---

### P2 — 其他

**16. 工具集不支持复合查询**

- 现状：4 个工具均为单实体查询
- 风险：LLM 拼凑两次单查询结果，答案质量不稳，可能前后矛盾

**17. 无流式输出**

- 风险：复杂查询（多次工具调用）延迟高，用户长时间等待空白页面

**18. LLM 无备用链路**

- 位置：`llm/qwen_client.py`，仅 Qwen-max
- 风险：模型服务不可用时直接 fallback，不能自动切换

---

## 四、升级建议

### P0 — 立刻动手：先补真实性闭环

**1. 规则表接管状态判定**

- 废弃 `soil_repository.py` 和 `rule_repository.py` 中的硬编码阈值，正式从 `metric_rule` 表读取激活规则
- 工具结果里返回 `rule_code` / `rule_version` / `rule_source`，供 FactCheck 做规则溯源
- **rule_version 来源**：若库表尚无显式 `rule_version` 字段，过渡期可用 `rule_code + updated_at` 近似表示版本；后续在 schema 里正式补 `version` 字段
- **切换策略**：采用 feature flag 双写过渡，而非一次性切换
  - 过渡期：同时计算代码阈值结果和规则表结果，写入日志对比，不改变线上行为
  - 确认两套结果一致、历史数据对齐后，再切规则表为唯一真相，废弃代码路径
  - 过渡期需跑迁移校验脚本，确认 `metric_rule` 表数据与历史判定结果无冲突
- **联动范围**：状态判定变更后，排名逻辑、FactCheck、前端展示都需同步验证

**2. 新增 Parameter Resolver 层**（枢纽，优先级最高）

- 位置：LLM 输出工具参数之后、ToolExecutor 之前
- **整合而非新增**：RegionAlias 负责实体标准化，metric_rule 负责状态/风险判定，两者职责分离，Resolver 只负责前者
- 子能力：
  - **实体标准化**：通过 `RegionAlias` 表将"合肥"→"合肥市"、"安徽"→"安徽省"，SN 格式校验
  - **时间窗收口**：正式契约只认 `start_time` / `end_time`。程序优先解析"今天 / 上周 / 最近13天 / 近2周 / 近3个月"等相对时间并展开为绝对窗口；LLM 仅在用户给出绝对日期表达时补充 `start_time` / `end_time`，所有结果都要经过未来时间、非法区间、超范围校验
  - **参数合法性校验**：必填字段、格式、值域；含安全硬上限（时间范围、limit、批量），防止提示词诱导大扫表
  - **参数置信度标记**：结构化字段 `entity_confidence` / `time_confidence`，下游可程序判断
- **置信度策略**（Resolver 是清洗层也是决策层）：
  - 高置信度 → 直接执行工具
  - 中置信度 → 执行，响应中附加 warning / trace
  - 低置信度 → 不查库，直接触发澄清流程，返回明确的澄清问题

**3. 空结果诊断改为程序自动判定**

- 不再让 LLM 决定 scenario
- 执行层按固定顺序自动判断：标准化失败 → 实体不存在 → 时间窗无数据
- `diagnose_empty_result` 保留但由系统内部编排，不暴露给模型自由选择

**4. FactCheck 升级为证据逐项映射**

- 在 `fact_check_service.py` 增加白名单字段级校验，明确边界：
  - **校验字段**（要求可映射回工具结果）：实体 ID/名称、时间窗、枚举状态/预警等级、排名序号
  - **数值校验**：允许合理容差（浮点 ±0.5%、日期边界 ±1 天），不要求逐字对齐
  - **不校验**：自然语言同义复述、单位换算表述、修辞性描述
  - 答案引用"排名第 N""最严重"等表述，必须能在返回结构中定位到对应项
- **上线策略**：先告警不拦截，观察误判分布后再切强校验

**5. 补全可观测性 / 审计链路**

- 在 `agent_query_log` 中持久化完整解析链路：
  - `raw_args`：LLM 原始输出的工具参数
  - `resolved_args`：Parameter Resolver 标准化后的参数
  - `final_tool_args`：实际执行时的参数
  - `entity_confidence` / `time_confidence`：置信度
  - `rule_code` / `rule_version`：状态判定所用规则版本
  - `empty_result_path`：空结果诊断路径（normalize_failed / entity_not_found / no_data_in_window）
- 不做这条，线上出现"为什么查不到合肥"或"为何判重旱"时仍无法排查

**6. 建立真实性回归测试集**

- 新增专门的 P0 测试，不再只测结构，至少覆盖：
  - 规则表更新后状态判定立即变化（feature flag 切换后验证）
  - 合肥 → 合肥市、安徽 → 安徽省标准化成功
  - "上周/最近7天"时间展开正确
  - 空结果能区分"参数错 / 实体不存在 / 时间窗无数据"
  - FactCheck 能拦截"有证据但答错细节"
- 作为 CI 强制门槛，跨阶段持续投入

---

### P1 — 近期规划：补理解质量与执行稳定性

**7. InputGuard 改为轻规则 + LLM 分类**

- 保留高确定性快速通道（问候/结束语/明显越界），这类不走 LLM，避免增加延迟
- **触发条件**：仅当规则层 confidence 低于阈值时，才调用轻量 LLM 分类（few-shot）
- **超时降级**：LLM 分类超时则默认进入业务主流程（宁可多查一次，不拦截合法请求）
- 不再扩关键词表来承载语义理解

**8. 显式指代消解**

- AgentLoop 前增加一步：从上下文提取当前有效实体、时间范围、查询对象
- 把"它""那个地区""换成上周"展开为完整请求
- 输出消解后的**结构化上下文**（而非改写后的自然语言），供 Parameter Resolver 直接消费

**9. intent / answer_type 显式化**

- 不引入独立的意图分类 LLM，避免多次 LLM 各说各话
- InputGuard LLM fallback、指代消解、意图解析尽量复用同一次语义解析结果，不拆成三次独立 LLM 调用
- intent 由语义解析步骤给出；执行证据只用于校验和纠偏，不再由第一把工具反推
- answer_type 由最终回答结构决定（有数据 / 无数据 / 澄清 / 降级），不由第一把工具猜

**10. 支持多 tool_call 执行**

- `qwen_client.py` 不再只取第一条，AgentLoop 支持顺序执行一批 tool_calls
- **失败语义约定**（需在实现前明确，按失败类型区分处理）：
  - 参数校验失败 / 工具执行异常 / 数据库错误 → 短路，整体进入 fallback
  - 业务空结果 → 不短路，允许进入自动诊断或后续补充调用；单个子查询无数据不等同于整批失败
  - 所有 tool_calls 共享同一个 max_iterations 计数（不因批量而放大）
  - 每个 tool_call 结果独立写入上下文，合并后再传给 LLM
- 为后续复合查询、对比查询、多实体聚合打基础

**11. 修正排名逻辑的业务偏置**

- 引入统一 `risk_score`，兼容重旱、涝渍、设备故障
- `risk_score` 权重由 `metric_rule` 表定义，不再硬编码
- 排名以风险分为主，记录数/最新时间为辅

**12. 上下文存储改为 token 滑窗 + 摘要压缩**

- 分两步：先做 token 滑窗（简单），再做摘要压缩（复杂）
- 保留最近关键消息 + 工具结果摘要；对过早历史做结构化摘要而非直接丢弃

**13. 会话 TTL 前端可感知**

- 通过 API 响应头标记会话状态（active / expiring / expired）
- 需与现有 `chat API` 响应契约对齐，客户端同步改造，避免只改后端不改前端
- TTL 失效后明确提示"上下文已重置"，避免用户误以为系统还记得前文

---

### P2 — 中期规划：体验与扩展性增强

**14. 新增复合/对比查询工具**
- `query_soil_comparison(entities: list, metric, time_range)`
- 支持多地区、多设备横向对比，避免 LLM 自己拼两个单查询结果

**15. 流式输出**
- FastAPI SSE + 前端流式渲染
- 工具调用阶段展示阶段进度提示，长链路用户感知明显更好

**16. LLM 备用链路**
- 主模型失败自动切换备用模型；增加超时、重试、降级策略

**17. 意图枚举与工具能力解耦**
- 减少新增业务时对 `IntentType` + prompt + tool schema 的同步改造负担

---

## 五、横切关注点

这些不属于单个改动项，但贯穿整个升级周期，需要在排期时显式覆盖。

| 方向 | 要点 |
|------|------|
| **性能与成本预算** | 多 tool_call、额外 LLM 分类、FactCheck 增强都会增加延迟；需设单轮最大工具次数上限、最大解析耗时预算，超出则提前降级 |
| **安全与滥用防护** | Resolver 后仍需对时间范围、limit、批量做硬上限，防止提示词诱导大扫表；硬上限不应由 LLM 参数决定 |
| **数据迁移与校验** | `metric_rule` 若历史数据与代码阈值长期不一致，上线前需跑迁移或校验脚本，确保规则表与历史判定结果对齐 |
| **幂等与重试** | LLM / 工具链路上对重复 tool_call、部分失败重试需有约定，避免双写或双计 |
| **前端契约** | TTL / 会话状态若走响应头，需与现有 chat API 对齐，客户端同步改造；不能只改后端文档 |

---

## 六、落地顺序总览

```
P0（立刻动手）
  1. 规则表接管状态判定（feature flag 双写过渡 + 迁移校验脚本）
  2. Parameter Resolver（RegionAlias 实体标准化，单一收口）← 枢纽，优先最高
  3. 空结果自动诊断
  4. FactCheck 升级为逐项映射（先告警后拦截）
  5. 补全可观测性 / 审计链路
  6. 真实性回归测试补齐（持续投入，CI 强制门）

P1（近期）
  7.  InputGuard 轻规则 + LLM（仅低 confidence 触发，超时降级进主流程）
  8.  显式指代消解（输出结构化上下文）
  9.  intent / answer_type 显式化（复用同一次语义解析，执行证据只做校验纠偏）
  10. 多 tool_call 支持（明确失败短路 vs 业务空结果语义）
  11. 风险评分重构排名（risk_score 来自规则表）
  12. 上下文滑窗 + 摘要（分两步）
  13. TTL 前端感知（与 chat API 契约同步）

P2（中期）
  14. 复合/对比查询工具
  15. 流式输出
  16. LLM 备用链路
  17. 意图枚举与工具能力解耦
```

---

## 七、灰度上线策略

P0 改动不是小修，需要稳妥落地，建议分阶段切换：

| 阶段 | 内容 | 策略 |
|------|------|------|
| **Shadow 观察期** | Parameter Resolver 上线；规则表双写 | 只记录 `resolved_args` 和置信度，不拦截原有链路；对比 raw vs resolved，观察标准化覆盖率和误判率；对比代码阈值与规则表结果差异 |
| **告警期** | FactCheck 逐项映射上线 | 校验失败只写审计日志 + 告警，不拦截回答；观察拦截率和误判分布 |
| **强校验期** | 切换强执行；规则表成为唯一真相 | 置信度低 → 澄清；FactCheck 失败 → fallback；废弃代码阈值路径；确认各项指标稳定后正式上线 |

**回滚触发条件**：出现以下任一情况，暂停推进并回滚至上一阶段：
- `raw_args` → `resolved_args` 不一致率超过预设阈值
- FactCheck 告警中误判率（合法答案被拦截）超过预设阈值
- fallback 率或 P95 延迟相比基线明显恶化

---

## 八、评估指标

升级后的验收基准，按四类维度衡量：

### 真实性
| 指标 | 说明 |
|------|------|
| 事实核验拦截率 | FactCheck 拦截"有证据但细节答错"的比例 |
| 空结果误判率 | 把参数错误误判为"无数据"的比例 |
| 规则表一致性 | 代码判定结果与规则表一致的比例（过渡期监控，目标 100%） |

### 理解能力
| 指标 | 说明 |
|------|------|
| 意图识别准确率 | intent 标注与人工标注一致率 |
| 指代解析准确率 | 多轮对话中实体/时间正确展开的比例 |
| 实体标准化覆盖率 | 用户输入实体被成功规范化的比例 |
| 澄清触发率 | 低置信度触发澄清的比例（过高说明标准化覆盖不足） |

### 对话质量
| 指标 | 说明 |
|------|------|
| 上下文丢失率 | 多轮对话中因窗口截断导致参数填错的比例 |
| TTL 误解投诉数 | 用户反馈"系统不记得之前说的"的数量 |

### 工程稳定性
| 指标 | 说明 |
|------|------|
| tool_call 执行成功率 | 无异常返回的比例（系统层面） |
| tool_call 命中率 | 返回非空业务数据的比例（业务层面，合法空结果不计入失败） |
| 平均工具轮次 | 每次对话平均调用工具次数（过高说明意图不稳） |
| fallback 率 | 触发降级答案的比例（目标持续下降） |
| 单轮 P95 延迟 | 引入多 LLM 调用后的延迟变化监控 |

---

## 九、核心结论

当前 Agent 的主要风险，不只是"有没有查真数据"，而是：

> **LLM 产出的参数、工具执行结果、最终答案三者之间，还没有形成可验证的真实性闭环。**

Parameter Resolver + FactCheck 逐项映射这两个改动是闭合这个环的关键路径。规则表 feature flag 过渡 + 可观测性补全 + 灰度上线是让这条路走稳的保障。

---

## 十、关键文件速查

| 问题 | 涉及文件 |
|------|---------|
| 状态阈值硬编码 | `apps/agent/app/repositories/soil_repository.py` |
| 规则表未使用 | `infra/mysql/init/002_insert_data.sql` + `apps/agent/app/repositories/rule_repository.py` |
| 实体参数无标准化 | `apps/agent/app/services/tool_executor_service.py` |
| 地名别名表定义 | `infra/mysql/init/001_init_tables.sql`（region_alias 表）+ `apps/agent/app/repositories/soil_repository.py` line 392 |
| 时间参数无校验 | `apps/agent/app/llm/prompts/system_prompt.py` + `apps/agent/app/services/tool_executor_service.py` |
| 事实核验偏弱 | `apps/agent/app/services/fact_check_service.py` |
| 只取第一条 tool_call | `apps/agent/app/llm/qwen_client.py` |
| intent 反推不稳定 | `apps/agent/app/flow/nodes/agent_loop.py` line 56 |
| 排名领域偏置 | `apps/agent/app/services/tool_executor_service.py` |
| InputGuard 关键词匹配 | `apps/agent/app/services/input_guard_service.py` |
| 对话历史截断 | `apps/agent/app/repositories/session_context_repository.py` |
| 工具定义集 | `apps/agent/app/llm/tools/soil_tools.py` |
| LLM 客户端 | `apps/agent/app/llm/qwen_client.py` |
| 查询审计日志 | `apps/agent/app/repositories/query_log_repository.py` |
