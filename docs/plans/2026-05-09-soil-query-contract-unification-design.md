# Soil Query Contract Unification Design

**Date:** 2026-05-09

## Goal

统一 Soil Agent 从用户输入到最终回答的单轮合同，消除“同一句话在不同能力、不同上下文下被不同层重复解释”的结构性问题，避免同类问题反复出现。

## Non-Goals

- 本轮不改数据库 schema。
- 不替换现有仓储层与预警规则计算逻辑。
- 不重做前端聊天渲染器。
- 不把全部能力重写成 LLM 路由；仍保持 deterministic 主链路。

## Problem Summary

当前链路里，同一个概念被多层重复定义，且定义不完全一致：

1. “是否结束上一轮话题”
2. “这句是 standalone 还是 follow-up”
3. “问的是墒情全量数据还是预警筛选数据”
4. “本轮真正要比较/统计/展开的指标是什么”
5. “最终文本里该叫记录、墒情记录还是预警记录”

这导致系统虽然有较多回归测试，但仍容易出现 route-specific 修复，表现为：

- 某个能力修好了，另一个能力里同一句式继续出错
- 查询数据是对的，但文本标签错了
- 路由是对的，但 follow-up 继承口径漂了
- 真实页面与单测表现不一致时，需要靠逐条补 case 来兜底

## Current Conflict Map

### 1. Conversation State Ownership Is Split

当前“话题结束 / 澄清中 / 正常承接”的状态至少被以下位置同时理解：

- `InputGuardService`
- `DataAnswerService._reply_impl`
- `FollowUpIntentResolverService`
- `TurnRouteDecisionService`
- `FollowUpActionResolverService`

其中 `DataAnswerService` 已经在入口加了 `closed_context` 拦截，但 `TurnRouteDecisionService` 仍会基于文本重新推断 `contextual_subject`。这类并行判断就是最近“结束后还继承上下文”反复出现的根因。

### 2. Business Subject And Data Focus Are Split

当前“问的是什么能力”和“问的数据口径是什么”被拆成两层：

- `TurnRouteDecisionService` 负责能力路由
- `QueryProfileResolverService` 再次从原始文本推 `data_focus / measure / compare_mode / warning_type / status_focus`

问题在于第二层不是纯消费第一层结果，而是重新解释原始文本并允许继承上一轮 profile，因此容易出现：

- route 是通用 compare
- query profile 却继承成 warning compare

### 3. Output Labels Are Not Backed By One Metric Registry

当前存在多组接近但语义不同的指标名：

- `record_count`
- `warning_record_count`
- `alert_record_count`
- `device_count`
- `alert_device_count`
- `measure`
- `execution_metric`

它们在查询、block、context、文本渲染里不是同一套命名空间，所以文本经常需要靠 helper 临时翻译，容易出现“数字正确但标签不一致”的问题。

### 4. Follow-Up Has Two Parallel Systems

当前 follow-up 至少有两条链：

- 语义承接：`FollowUpIntentResolverService`
- 结果展开：`FollowUpActionResolverService`

两边都在识别：

- `详情`
- `明细`
- `哪些`
- `呢`

如果没有统一的上游 interpretation contract，这两套系统就会在边缘句式上互相打架。

### 5. Fact Check Is Structural, Not Semantic

`FactCheckService` 目前主要检查：

- 数字是否在文本里出现
- 0 条时文本是否声称有结果

它不理解“这 87 条到底是墒情记录还是预警记录”，因此抓不住标签漂移和口径漂移。

## Design Principles

1. 单轮解释只做一次。
2. 状态只定义一次，下游只能消费。
3. 数据口径只定义一次，下游不能再猜。
4. 指标命名要先规范化，再渲染成中文。
5. 路由、查询、渲染、校验使用同一份 interpretation contract。
6. `subset / filter` 是一等 follow-up 合同，不允许被宽松的 standalone 判定吞掉。
7. `TurnInterpretation` 产出后，下游服务不得再基于原始文本做业务语义分支。

## Target Architecture

### 1. Add A Single `TurnInterpretation`

新增一个统一中间对象，例如：

```python
@dataclass(frozen=True)
class TurnInterpretation:
    normalized_text: str
    conversation_state: str  # open / clarify / closed
    follow_up_mode: str      # standalone / inherit / replace_slot / correct_slot / subset / action_expand / blocked
    subject_family: str      # soil / warning / warning_disposal / device_registry / rule / template
    answer_intent: str       # summary / detail / list / group / count / compare / guidance
    entities: dict[str, Any]
    time_window: dict[str, Any]
    data_focus: str          # all_records / warning_only
    measure: str | None
    compare_mode: str | None
    warning_type: str | None
    status_focus: str | None
    list_target: str | None
    group_by: str | None
    blocked_reason: str | None
```

这个对象是单轮真相源。后续 route、query profile、render、fact check 都只能读取它，不再重复从原始文本猜一遍。

### 2. One Resolver Owns Interpretation

新增一层统一解释服务，建议文件：

- `apps/agent/app/services/turn_interpretation_service.py`

它负责串联：

1. 输入标准化
2. conversation state 判定
3. follow-up 判定
4. subject family 判定
5. answer intent 判定
6. data focus / measure / warning type / status focus 判定

现有服务改成 helper：

- `InputGuardService`: 仅边界拦截
- `FollowUpIntentResolverService`: 仅提供 follow-up helper
- `FollowUpActionResolverService`: 仅提供 action-target helper
- `TurnRouteDecisionService`: 仅把 interpretation 映射到 capability
- `QueryProfileResolverService`: 仅把 interpretation 映射到 query profile

### 2.5 No Downstream Re-Parsing

`TurnInterpretation` 一旦生成，后续链路只允许读取它，不允许重新从 `message` 或 `normalized_text` 推断：

- `TurnRouteDecisionService` 不得再根据原始文本猜 `subject_family`
- `QueryProfileResolverService` 不得再根据原始文本猜 `data_focus / measure / warning_type / status_focus`
- `DataAnswerService` 渲染阶段不得为了补文案再临时改写指标语义
- `FactCheckService` 不得基于裸文本猜“这条记录到底是哪类记录”，而应读取结构化 contract

原始文本在 interpretation 之后只允许用于：

- logging
- debug evidence
- 用户可见原文回显

### 3. Make Routing Pure

`TurnRouteDecisionService` 不再直接读取原始 message、context、time evidence 做多轮推断，而是变成纯映射：

```python
route = route_from_interpretation(interpretation)
```

它可以保留少量 capability-specific mapping，但不再拥有独立的上下文继承规则。

### 4. Make Query Profile Pure

`QueryProfileResolverService` 不再从原始文本重新判断：

- `data_focus`
- `measure`
- `compare_mode`
- `warning_type`
- `status_focus`

这些都应由 interpretation 层产出。`QueryProfileResolverService` 只做结构落盘与少量默认值补全。

### 5. Normalize Metrics Before Rendering

统一内部指标命名，不让 `record_count` 跨层变义。

建议 canonical metrics：

- `soil_record_count`
- `warning_record_count`
- `soil_device_count`
- `warning_device_count`
- `region_count`
- `avg_water20cm`
- `latest_create_time`

然后由单一 label registry 负责中文显示：

```python
METRIC_LABELS = {
    "soil_record_count": "墒情记录",
    "warning_record_count": "预警记录",
    "soil_device_count": "墒情仪",
    "warning_device_count": "预警墒情仪",
    "region_count": "地区",
}
```

这样 compare / summary / warning group / warning disposal 的文本不再各自手写标签。

### 6. Separate Execution Metric From Display Metric Explicitly

比较类回答继续允许：

- 默认执行指标是 `soil_record_count`
- 显示层不一定强调该指标

但必须显式区分：

- `requested_measure`
- `execution_measure`

并禁止使用同一个 `measure` 字段同时承载“用户显式请求的指标”和“系统默认补出的执行指标”。

### 7. Upgrade Fact Check To Semantic Contract Check

`FactCheckService` 升级为语义校验，至少覆盖：

- 文本出现 `预警记录` 时，必须对应 `warning_record_count`
- 文本出现 `墒情记录` 时，必须对应 `soil_record_count`
- compare 类 block 中 `requested_measure` 和 `execution_measure` 的显示语义必须一致
- warning-only 回答不得把 warning metric 回退成 soil metric 文案

## Test Strategy

不再只按真实问答 case 补洞，而是补“合同矩阵”测试。

### 1. Interpretation Contract Tests

新增或强化以下单测：

- `test_turn_interpretation_closing_blocks_contextual_restart`
- `test_turn_interpretation_closed_context_allows_explicit_restart`
- `test_turn_interpretation_warning_only_does_not_leak_into_generic_compare`
- `test_turn_interpretation_city_short_follow_up_inherits_time_without_becoming_standalone`
- `test_turn_interpretation_subset_follow_up_keeps_subset_instead_of_standalone`

### 2. Route Mapping Tests

验证 interpretation 到 capability 的纯映射，不再同时测试文本猜测。

### 3. Query Profile Governance Tests

验证：

- `data_focus`
- `requested_measure`
- `execution_measure`
- `warning_type`
- `status_focus`

只能从 interpretation 来，不能被隐式继承污染。

### 3.5 Repository Contract Tests

新增一类“仓储真值”测试，不只校验文本格式，还直接校验结构化结果与仓储聚合是否一致，至少覆盖：

- summary 的 `soil_record_count`
- warning-only summary/group 的 `warning_record_count`
- compare 的 `requested_measure / execution_measure`
- 重点关注地区这类 preview 回答中，“前 N 个地区的预警记录之和”不应被误写成全局总数

目标是把“数据对不对”从页面抽查前移到可重复的自动化验证。

### 3.6 Live Data Truth Audits

仅有 support-repository 或 seeded-repository 级测试还不够，它们只能证明合同和代码路径一致，不能证明当前本地 MySQL 中的真实数据一定正确。

因此还需要新增一层 live-data truth audit，至少覆盖：

- 使用当前 `MYSQL_*` 环境连接本地真实库
- 对 canonical prompts 的 `executed_result` 与 live repository aggregate 做逐项比对
- 验证 soil summary / soil warning / warning disposal 三类回答不会串表
- 明确验证土壤墒情相关回答不会把其他类型预警或 `warning_disposal_record` 混入 soil warning 统计

目标是把“当前真实数据 100% 正确”的信心来源，从页面观察升级为可重复的 live-db 验证。

### 4. Rendering Contract Tests

验证所有主回答类型：

- summary
- group
- compare
- warning_disposal

都使用统一指标标签，不出现 `记录` 这种歧义词。

## Migration Strategy

### Phase 1

先加 interpretation contract 测试，锁定当前目标行为。

### Phase 2

引入 `TurnInterpretation`，先接管：

- `closed_context`
- `follow_up_mode`
- `subset / filter`
- `data_focus`
- `compare_mode`
- `measure`

### Phase 3

让 `TurnRouteDecisionService` 和 `QueryProfileResolverService` 只消费 interpretation。

### Phase 4

统一 metric registry 和 renderer label helpers。

### Phase 5

升级 fact check，补全真实问答矩阵。

### Phase 6

补一层 repository-backed truth checks，确认回答中的核心数字与仓储查询口径一致。

### Phase 7

补 live-db truth audits，确认当前本地真实数据中的 soil-only 统计口径没有混入其他预警数据。

## Success Criteria

- 同一句式在不同能力下不会再出现不同的“standalone / follow-up / blocked”结论。
- `warning_only` 不会再通过 compare、count、group、summary 这些分支隐式串味。
- 文本层不再出现 `记录` 这种模糊标签，统一明确为 `墒情记录` 或 `预警记录`。
- 关闭话题、显式重开、上下文继承这三类行为有统一合同和专门测试。
- `subset / filter` 不会再被误判成 standalone，也不会因为放宽显式重开规则而回归。
- route、query profile、render、fact check 在 interpretation 之后不再各自二次猜文本。
- 至少一组 repository contract tests 会直接验证 `墒情记录 / 预警记录 / 预警墒情仪 / 地区数` 的结构化口径。
- 至少一组 live-data truth audits 会直接验证 soil-only 回答没有混入其他预警数据。
- 后续新增真实问答 case 时，应主要补 interpretation/contract 测试，而不是继续堆 route-specific 补丁。
