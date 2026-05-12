# 123 条真实问答失败分析

- 日期：2026-05-12
- 基线产物：
  - [live-real-123-api-results-2026-05-12T02-19-48.871Z.json](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/testdata/agent/soil-moisture/outputs/live-real-123-api-results-2026-05-12T02-19-48.871Z.json)
  - [live-real-123-api-summary-2026-05-12T02-19-48.871Z.md](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/testdata/agent/soil-moisture/outputs/live-real-123-api-summary-2026-05-12T02-19-48.871Z.md)
- 测试入口：
  - 本地 API：`http://localhost:3000/api/agent/chat`
  - 外网 smoke：`https://ai.luyaxiang.com/api/agent/chat`
  - 账号：`gago-dev`

## 结论

这轮不是“大面积数据算错”，而是“多轮上下文继承”没有统一打通。

- 自动统计：`123` 条里 `100` 条通过，`23` 条失败
- 人工复核后：
  - 真失败：`19` 条
  - 假失败：`4` 条
  - 有效通过：`104` 条

当前最主要的问题集中在以下几类：

1. `summary/group/count/warning_group` 的 follow-up 下钻和计数，没有继承上轮结果集或时间窗
2. `warning_disposal` 的状态追问，没有继承上轮时间窗
3. `warning_group` 切换到 `warning_disposal / warning_type / warning_count / warning_device_list` 时，没有继承上轮预警上下文
4. 无上下文短追问被错误继承到了旧话题
5. `rule -> warning_type -> warning_group` 的中间语义没有保存
6. `compare` 的 winner/follower 语义没有进入 follow-up 继承链

## 先不要误修的 4 条假失败

这 4 条被自动脚本判成失败，但从真实交互看应算通过，不建议作为 bug 修：

### #54 `SNS00204333最近7天怎么样 → 好的先这样 → 那海安市呢`

- 自动判错原因：第 2 轮 `好的先这样` 是 `guidance`
- 实际判断：应算通过
- 原因：第 2 轮是正常 closing，第 3 轮已经正确开启新话题，并返回 `海安市` 的 `detail`

### #86 `接入了多少台虫情监测设备`

- 自动判错原因：边界文案没有命中脚本里的固定正则
- 实际判断：应算通过
- 原因：系统明确拒答虫情设备统计，并引导回土壤墒情仪口径，属于正确边界

### #121 `土壤墒情仪分布在哪里？ → 好的先这样 → 最近7天整体墒情怎么样`

- 自动判错原因：第 2 轮 closing 被当成失败
- 实际判断：应算通过
- 原因：第 3 轮已经正确切到 `summary`

### #122 `最近30天全省预警处置情况怎么样 → 行，先这样吧 → 那设备分布呢`

- 自动判错原因：第 2 轮 closing 被当成失败
- 实际判断：应算通过
- 原因：第 3 轮已经正确切到 `device_registry_distribution`

## 19 条真失败总表

| 模式 | 数量 | Case |
|---|---:|---|
| follow-up 下钻/计数未继承上轮结果 | 10 | 51, 52, 53, 103, 104, 105, 106, 108, 109, 114 |
| `warning_disposal` 状态追问未继承时间窗 | 3 | 83, 100, 119 |
| `warning_group` follow-up 未继承时间/类型 | 3 | 97, 99, 107 |
| 无上下文短追问误继承旧话题 | 1 | 56 |
| `rule -> warning_type` 切换丢失中间语义 | 1 | 113 |
| `compare` winner follow-up 未继承比较结果 | 1 | 125 |

## 详细分析

### A. follow-up 下钻/计数未继承上轮结果

涉及 case：`51 52 53 103 104 105 106 108 109 114`

共同现象：

- 第一轮已经给出明确业务结果
- 第二轮是非常自然的追问：
  - `点位详情呢`
  - `记录详情呢`
  - `有多少条呢`
  - `哪些设备有预警`
  - `涉及多少个点位`
  - `涉及多少个区县`
  - `地区详情呢`
- 系统没有继承第一轮的 `time_window / result_set / query_profile`
- 返回了澄清或“没有可继承的数据查询上下文”

#### case 明细

##### #51 `南通市最近7天怎么样 → 点位详情呢`

- 期望：`summary -> device_list`
- 实际：
  - turn1：`business / summary`
  - turn2：`guidance / none`
  - 文案：`当前没有可继承的数据查询上下文，请先查询一轮墒情数据，再追问这些墒情仪。`
- 判断：这是明显 bug，因为第一轮就是标准 summary

##### #52 `最近30天按地区汇总墒情数据 → 地区详情呢`

- 期望：`group -> region detail drilldown`
- 实际：
  - turn1：`business / group`
  - turn2：`guidance / none`
  - 文案：`这轮还缺少明确的墒情查询条件...`
- 判断：group 结果没有形成可追问 target

##### #53 `3月20号全省出现墒情预警信息的点位有多少个 → 点位详情呢`

- 期望：`warning_count(device) -> warning_device_list`
- 实际：
  - turn1：`business / count`
  - turn2：`guidance / none`
- 判断：count 结果没有沉淀成后续 list 可用 target

##### #103 `最近7天哪些区域出现了预警信息？ → 点位详情呢`

- 期望：`warning_group -> warning_device_list`
- 实际：`guidance / none`

##### #104 `最近7天哪些区域出现了预警信息？ → 记录详情呢`

- 期望：`warning_group -> warning_record_list`
- 实际：`guidance / none`

##### #105 `最近7天哪些区域出现了预警信息？ → 有多少条呢`

- 期望：`warning_group -> warning_count`
- 实际：
  - 返回时间澄清：`你想查看的时间段是？`
- 判断：时间窗本来就在上一轮里，说明 follow-up 没把上一轮时间继承下来

##### #106 `最近7天哪些区域出现了预警信息？ → 哪些设备有预警`

- 期望：`warning_group -> warning_device_list`
- 实际：时间澄清

##### #108 `最近30天按地区汇总墒情数据 → 涉及多少个区县`

- 期望：`group -> count(region)`
- 实际：时间澄清

##### #109 `最近30天按地区汇总墒情数据 → 点位详情呢`

- 期望：`group -> device_list`
- 实际：`没有可继承的数据查询上下文`

##### #114 `最近7天全省整体墒情怎么样 → 涉及多少个点位`

- 期望：`summary -> count(device)`
- 实际：时间澄清

#### 根因判断

大概率不是单个 if 漏了，而是“上一轮结果能不能继续追问”的 contract 还没统一：

- 有些能力保存了 `time_window`，但没保存 `action_target`
- 有些能力保存了 `action_target`，但 follow-up route 不认
- 有些 follow-up route 能识别动作，但参数解析又重新要求显式时间

#### 建议修法

优先看这几处：

- [data_answer_service.py](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent/app/services/data_answer_service.py)
- [turn_route_decision_service.py](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent/app/services/turn_route_decision_service.py)
- [follow_up_intent_resolver_service.py](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent/app/services/follow_up_intent_resolver_service.py)
- [turn_interpretation_service.py](/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent/app/services/turn_interpretation_service.py)

建议目标不是单独补 case，而是统一定义：

- `summary/group/count/warning_group/warning_count/warning_disposal/compare`
  都必须产出统一的 follow-up target
- target 至少要稳定保存：
  - `capability`
  - `time_window`
  - `slots`
  - `source_snapshot_id`
  - `subject_kind`
  - `group_by`
  - `warning_type`
  - `status_focus`
- follow-up 的 `点位详情 / 记录详情 / 有多少条 / 哪些设备 / 涉及多少个区县`
  不应该重新走“缺少时间”的硬澄清，而应该先继承上一轮 target

### B. `warning_disposal` 状态追问未继承时间窗

涉及 case：`83 100 119`

#### #83 `最近30天全省预警处置情况怎么样 → 那已处理多少条呢`

- 期望：继承 `最近30天全省`，只把 `status_focus` 收窄到 `processed`
- 实际：时间澄清

#### #100 `最近30天全省预警处置情况怎么样 → 那待处理多少条呢`

- 期望：继承时间窗，收窄到 `pending`
- 实际：时间澄清

#### #119 `最近30天全省预警处置情况怎么样 → 不是待处理，是已处理`

- 期望：基于上一轮或假定追问语义做状态纠错
- 实际：时间澄清

#### 根因判断

`warning_disposal` 自己能做单轮，但 follow-up 时没有把：

- `time_window`
- `region scope`
- `status_focus`

作为同一个 query contract 延续下去。

#### 建议修法

- 给 `warning_disposal` 建立和 `summary/group` 同级的 follow-up target
- 把 `已处理 / 待处理 / 超时已处理 / 超时待处理`
  统一视为 `status_focus` 的 slot 更新，而不是新 query
- 对 `不是 X，是 Y` 这类纠错，要优先命中 slot correction，而不是掉回时间澄清

### C. `warning_group` follow-up 未继承时间/类型

涉及 case：`97 99 107`

#### #97 `最近7天哪些区域出现了预警信息？ → 那这些预警处置情况呢`

- 期望：继承 `最近7天`，切到 `warning_disposal`
- 实际：时间澄清

#### #99 `最近7天哪些区域出现了预警信息？ → 那设备故障呢`

- 期望：继承 `最近7天`，把 `warning_type` 收窄到 `device_fault`
- 实际：时间澄清

#### #107 `3月20号全省出现墒情预警信息的记录有多少条 → 哪些区域出现了预警信息`

- 期望：继承 `2026-03-20`，从 `warning_count` 切到 `warning_group`
- 实际：时间澄清

#### 根因判断

`warning_group` 与 `warning_count`、`warning_disposal`、`warning_type` 之间的 capability switch 还是断的。

#### 建议修法

- 把 `warning_*` 视为同一主题族
- 允许这些能力之间只切 capability，不丢时间窗和范围：
  - `warning_group -> warning_disposal`
  - `warning_group -> warning_device_list`
  - `warning_group -> warning_record_list`
  - `warning_group -> warning_count`
  - `warning_count -> warning_group`
  - `warning_group -> warning_type refine`

### D. 无上下文短追问误继承旧话题

涉及 case：`56`

#### #56 `徐州呢`

- 期望：应澄清
- 实际：直接回答成 `device_registry_distribution`
- 问题点：短追问在没有可靠上下文时，被错误继承到了之前的“设备分布”主题

#### 建议修法

- 对极短输入如：
  - `徐州呢`
  - `那南京呢`
  - `南通呢`
- 必须增加一个保护条件：
  - 只有当上一轮 target 明确可继承，且主题未 closing，且 follow-up shape 足够强，才允许继承
- 否则应该优先澄清，而不是猜到旧话题

### E. `rule -> warning_type` 切换丢失中间语义

涉及 case：`113`

#### #113 `目前预警规则是什么 → 那设备故障预警呢？ → 最近7天哪些区域有这种预警`

- 期望：
  - turn1：规则总览
  - turn2：设备故障预警条款说明
  - turn3：带着 `warning_type=device_fault` 去查最近7天哪些区域有这种预警
- 实际：
  - turn2：时间澄清
  - turn3：虽然回到了 `warning_group`，但看结果仍是泛化预警分布，不是设备故障预警分布

#### 建议修法

- 规则类问答不能只当成静态文案回答
- 若 turn2 命中 `设备故障预警呢`，要把 `warning_type=device_fault` 存入上下文
- 后续 `这种预警` 应优先指向这个 `warning_type`，而不是退化成“普通预警”

### F. `compare` winner follow-up 未继承比较结果

涉及 case：`125`

#### #125 `徐州和南通最近30天对比一下 → 那更差那边有多少条预警记录`

- 期望：
  - turn1 比较后应有 winner/loser 语义
  - turn2 `更差那边` 应绑定到比较结果中的某一方
- 实际：
  - turn2 直接掉回时间澄清

#### 建议修法

- compare 结果除了返回文本，还要保存：
  - compare entities
  - compare metric
  - compare winner / loser
  - compare reason
- follow-up resolver 对：
  - `更差那边`
  - `更好那边`
  - `赢家`
  - `输的那个`
  应该能映射到 compare target 的 entity

## 建议 CC 的修复优先级

### P0：先修统一继承 contract

先修这一层，能一把带动大部分失败：

- `summary/group/count/warning_group/warning_count/warning_disposal/compare`
  输出统一 target
- follow-up 时优先继承：
  - `time_window`
  - `slots`
  - `warning_type`
  - `status_focus`
  - `group_by`
  - `source_snapshot_id`

预估可直接覆盖：

- `51 52 53 83 97 99 100 103 104 105 106 107 108 109 114 119 125`

### P1：修无上下文短追问保护

- case：`56`
- 目标：没有足够强的上文时，宁可澄清，不要误继承

### P1：修 `rule -> warning_type -> warning_group`

- case：`113`
- 目标：把“这种预警”的指代链补全

## 建议补的单测/集测

至少把以下 case 直接固化成测试，不要只靠人工回归：

- `#51` summary -> device_list
- `#52` group -> region detail
- `#53` warning_count(device) -> warning_device_list
- `#83` warning_disposal -> processed count
- `#97` warning_group -> warning_disposal
- `#99` warning_group -> warning_type refine(device_fault)
- `#103` warning_group -> warning_device_list
- `#105` warning_group -> warning_count
- `#108` group -> region count
- `#114` summary -> device_count
- `#119` warning_disposal status correction
- `#125` compare -> winner count follow-up
- `#56` no-context short follow-up should clarify

## 给 CC 的一句话版本

这轮真实问答的主要问题不是单轮能力，也不是大面积数据口径错误，而是“多轮 follow-up 的统一继承 contract 没打通”。请优先统一 `summary/group/count/warning_group/warning_count/warning_disposal/compare` 的 follow-up target 和 slot/time_window 继承逻辑，不要继续按单 case 打补丁。
