# 墒情 Agent Case Library（30 条正式验收 Case）

> **架构版本**：LLM + Function Calling 5 节点（`InputGuard → AgentLoop → DataFactCheck → AnswerVerify → FallbackGuard`）。
>  
> **唯一正式入口**：本文件是当前 `soil-moisture` Agent 的唯一正式验收库。所有正式 Case 的新增、删减、修订都只改这里。
>
> **测试原则**：
> - 每次验收都全量跑完全部 `30` 条 Case。
> - 每条 Case 都保留完整的 `当前回答` 长文本样例。
> - 每条业务 Case 都必须带 `数据库校验断言` 与 `是否符合事实`。
> - 正式通过的业务 Case，`是否符合事实` 必须为 `是`。

## Case 分布

| 一级 `answer_type` | 数量 | CaseID |
|---|---:|---|
| `guidance_answer` | 8 | `SM-CONV-001 ~ SM-CONV-008` |
| `soil_summary_answer` | 6 | `SM-SUM-001 ~ SM-SUM-006` |
| `soil_ranking_answer` | 4 | `SM-RANK-001 ~ SM-RANK-004` |
| `soil_detail_answer` | 8 | `SM-DETAIL-001 ~ SM-DETAIL-008` |
| `fallback_answer` | 4 | `SM-FB-001 ~ SM-FB-004` |

## Guidance Cases（8）

### SM-CONV-001

- `CaseID`：`SM-CONV-001`
- `用户问题`：你好
- `当前回答`：你好，我可以帮你查询墒情概览、风险排名，以及地区或设备的详细情况。你可以直接问“最近 7 天整体墒情怎么样”“南通市当前情况如何”或“SNS00204333 最近有没有异常”。  
- `上下文`：无
- `预期 input_type`：`greeting`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`safe_hint`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；回答能力范围和示例问法；`conversation_closed=false`
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`；`answer_facts={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：基础问候样例

### SM-CONV-002

- `CaseID`：`SM-CONV-002`
- `用户问题`：你能做什么
- `当前回答`：我主要处理土壤墒情相关问题，可以查整体概况、看风险排名、查某个地区或某台设备的详情，也能在回答里突出异常、预警或建议视角。你只要把地区、设备或时间范围说清楚，我就能给出基于真实数据的结果。  
- `上下文`：无
- `预期 input_type`：`capability_question`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`safe_hint`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；必须强调“基于真实数据”
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：能力说明样例

### SM-CONV-003

- `CaseID`：`SM-CONV-003`
- `用户问题`：帮我看一下
- `当前回答`：可以，我先帮你定位问题类型。请补充地区、设备或时间范围，例如：“南通市最近 7 天墒情怎么样”“SNS00204333 最近有没有异常”或“过去 30 天哪些县区最严重”。  
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`clarification`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；明确要求补充关键信息
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：直接澄清样例

### SM-CONV-004

- `CaseID`：`SM-CONV-004`
- `用户问题`：那个情况呢
- `当前回答`：我还缺少这轮要查询的明确对象。请直接告诉我地区、设备或时间范围，例如：“如东县最近怎么样”“SNS00204333 昨天有没有异常”或“南通市当前最新一期概况如何”。  
- `上下文`：上一轮没有形成有效业务对象，不能安全继承
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`clarification`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不能误继承上下文；应要求用户明确对象
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：缺上下文的短口语澄清样例

### SM-CONV-005

- `CaseID`：`SM-CONV-005`
- `用户问题`：帮我查一下明天天气
- `当前回答`：我当前只处理墒情数据相关问题，不提供天气查询。你可以改问“最近 7 天墒情怎么样”“哪个县区最需要关注”或“某台设备最近有没有异常”。  
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`boundary`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；明确边界并给出可问替代
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：能力边界样例

### SM-CONV-006

- `CaseID`：`SM-CONV-006`
- `用户问题`：帮我写一首诗
- `当前回答`：这个请求超出了我当前的墒情业务范围。我更适合回答土壤墒情概况、风险排名、地区或设备详情，以及异常和预警相关问题。  
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`boundary`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；不得产出诗歌内容
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：创作型越界样例

### SM-CONV-007

- `CaseID`：`SM-CONV-007`
- `用户问题`：谢谢
- `当前回答`：不客气。如果你后面还想看某个地区、设备或时间段的墒情情况，直接继续问我就可以。  
- `上下文`：无
- `预期 input_type`：`conversation_closing`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`closing`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；`conversation_closed=true`
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：结束语样例

### SM-CONV-008

- `CaseID`：`SM-CONV-008`
- `用户问题`：好的，先这样
- `当前回答`：好的，这一轮先到这里。后面如果你想继续看南通市、如东县或某台设备的最新数据，直接在当前线程继续问就行。  
- `上下文`：上一轮刚完成一次业务查询
- `预期 input_type`：`conversation_closing`
- `是否域内业务问题`：否
- `是否必须命中 Tool`：否
- `预期 Tool`：`无`
- `预期 answer_type`：`guidance_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`closing`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：否
- `关键断言`：不查库；结束当前话题并清理后端继承上下文
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`
- `数据库校验断言`：不适用（非业务，不查库）
- `是否符合事实`：`是`
- `备注`：带上下文的结束语样例

## Summary Cases（6）

### SM-SUM-001

- `CaseID`：`SM-SUM-001`
- `用户问题`：最近 7 天整体墒情怎么样
- `当前回答`：最近 7 天全省墒情整体平稳，20 厘米平均含水量约为 `93.77%`，共汇总 `3689` 条监测记录。预警相关记录共有 `44` 条，当前需要重点关注的区域主要是 `睢宁县`、`沛县` 和 `昆山市`，其中睢宁县最突出。整体仍以未触发预警为主，但局部存在涝渍点位，也有少量重旱和设备故障记录，建议优先复核上述高风险区域。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：必须命中 summary；不得绕过 Tool；概览结论和重点区域正确
- `结构化证据断言`：`tool_trace[0].tool_name=query_soil_summary`；`answer_facts.total_records=3689`；`answer_facts.alert_count=44`
- `数据库校验断言`：调用 `query_soil_summary(start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=3689`、`avg_water20cm=93.77`、`alert_count=44`，Top3 关注区域依次包含 `睢宁县 / 沛县 / 昆山市`
- `预期实体`：`全局`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`3689 / 93.77 / 44`
- `必含事实`：`睢宁县`、`沛县`、`昆山市`
- `禁止事实`：`无数据`、`全部正常无需关注`
- `是否符合事实`：`是`
- `备注`：全局概览基准样例

### SM-SUM-002

- `CaseID`：`SM-SUM-002`
- `用户问题`：南通市最近 7 天墒情怎么样
- `当前回答`：最近 7 天南通市整体比较平稳，共汇总 `259` 条记录，20 厘米平均含水量约 `95.39%`。这一时间窗内 `alert_count=0`，状态分布全部为 `not_triggered`，说明当前没有明显异常点位。可以把这次结果视为平稳运行状态，继续做日常巡检即可。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：地区范围正确；无异常结论必须被数据支持
- `结构化证据断言`：`answer_facts.total_records=259`；`answer_facts.alert_count=0`
- `数据库校验断言`：调用 `query_soil_summary(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=259`、`avg_water20cm=95.39`、`alert_count=0`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`259 / 95.39 / 0`
- `必含事实`：`南通市`、`259`
- `禁止事实`：`存在明显预警`
- `是否符合事实`：`是`
- `备注`：地区概览正常样例

### SM-SUM-003

- `CaseID`：`SM-SUM-003`
- `用户问题`：现在南通市整体墒情怎么样
- `当前回答`：按当前库内最新业务时间来看，南通市最新一期（`2026-04-13`）共汇总 `37` 条记录，20 厘米平均含水量约 `96.21%`，全部为未触发预警状态，`alert_count=0`。也就是说，当前这一期数据没有发现需要立即升级处置的异常点位。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：“现在/当前”必须以库内最新业务时间为锚点，不得用系统时间
- `结构化证据断言`：`answer_facts.time_window.start_time=2026-04-13 00:00:00`；`answer_facts.total_records=37`
- `数据库校验断言`：调用 `query_soil_summary(city=南通市,start=2026-04-13 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=37`、`avg_water20cm=96.21`、`alert_count=0`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-04-13 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`37 / 96.21 / 0`
- `必含事实`：`2026-04-13`
- `禁止事实`：`系统当前时间`
- `是否符合事实`：`是`
- `备注`：最新业务时间锚点样例

### SM-SUM-004

- `CaseID`：`SM-SUM-004`
- `用户问题`：睢宁县最近一个月有没有异常
- `当前回答`：最近一个月睢宁县需要重点关注。该时间窗共汇总 `210` 条记录，20 厘米平均含水量约 `132.61%`，其中预警相关记录 `39` 条，异常主要集中在 `涝渍`。如果按异常视角看，睢宁县本轮就是本地最值得优先复核的对象，近几条代表性异常记录集中在设备 `SNS00213891`。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`anomaly_focus`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：异常视角必须落在 `output_mode=anomaly_focus`
- `结构化证据断言`：`answer_facts.output_mode=anomaly_focus`；`answer_facts.alert_count=39`；`answer_facts.top_alert_regions[0].region=睢宁县`
- `数据库校验断言`：调用 `query_soil_summary(county=睢宁县,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59,output_mode=anomaly_focus)`；应得到 `total_records=210`、`alert_count=39`，代表异常记录中包含 `SNS00213891`
- `预期实体`：`睢宁县`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`210 / 132.61 / 39`
- `必含事实`：`睢宁县`、`39`、`涝渍`
- `禁止事实`：`完全正常`
- `是否符合事实`：`是`
- `备注`：summary 异常视角样例

### SM-SUM-005

- `CaseID`：`SM-SUM-005`
- `用户问题`：从预警角度看，南通市今年情况怎么样
- `当前回答`：从预警视角看，南通市今年共汇总 `3811` 条记录，预警相关记录 `20` 条，重点区域依次是 `如东县（14）`、`启东市（3）`、`海门区（2）` 和 `如皋市（1）`。代表性预警样例包括 `2026-03-05 23:59:17` 启东市设备 `SNS00214096` 的 `154.31%` 涝渍记录，以及如东县设备 `SNS00204334` 在一月中旬连续出现的重旱记录。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`warning_mode`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：预警视角必须落在 `warning_mode`，并突出预警记录
- `结构化证据断言`：`answer_facts.output_mode=warning_mode`；`answer_facts.alert_count=20`；`answer_facts.top_alert_regions[0].region=如东县`
- `数据库校验断言`：调用 `query_soil_summary(city=南通市,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=warning_mode)`；应得到 `total_records=3811`、`alert_count=20`、Top4 重点区域为 `如东县 / 启东市 / 海门区 / 如皋市`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
- `预期关键指标`：`3811 / 20 / 如东县14`
- `必含事实`：`SNS00214096`、`154.31%`
- `禁止事实`：`全年没有任何预警`
- `是否符合事实`：`是`
- `备注`：summary 预警视角样例

### SM-SUM-006

- `CaseID`：`SM-SUM-006`
- `用户问题`：南通市近 7 天需要注意什么
- `当前回答`：从建议视角看，南通市近 7 天总体平稳，共有 `259` 条记录，20 厘米平均含水量约 `95.39%`，当前没有触发预警的点位。因为这段时间 `alert_count=0`，更适合维持日常巡检和例行监测，不需要额外升级处置，但仍建议按常规频率关注后续最新一期数据。  
- `上下文`：无
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_summary`
- `预期 answer_type`：`soil_summary_answer`
- `预期 output_mode`：`advice_mode`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：建议内容必须建立在真实概况之上，不能凭空扩展风险
- `结构化证据断言`：`answer_facts.output_mode=advice_mode`；`answer_facts.alert_count=0`
- `数据库校验断言`：调用 `query_soil_summary(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59,output_mode=advice_mode)`；应得到 `total_records=259`、`avg_water20cm=95.39`、`alert_count=0`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`259 / 95.39 / 0`
- `必含事实`：`总体平稳`
- `禁止事实`：`建议立即发布预警`
- `是否符合事实`：`是`
- `备注`：summary 建议视角样例

## Ranking Cases（4）

### SM-RANK-001

- `CaseID`：`SM-RANK-001`
- `用户问题`：最近 30 天县区里哪几个最严重
- `当前回答`：最近 30 天如果按县区风险排序，前 3 位分别是 `睢宁县`、`昆山市` 和 `沛县`。其中睢宁县共有 `39` 条预警相关记录，昆山市 `37` 条，沛县 `36` 条，三者都是当前最需要优先关注的县区。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_ranking`
- `预期 answer_type`：`soil_ranking_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：排名顺序必须正确，且已经是聚合后的 TopN
- `结构化证据断言`：`tool_trace[0].tool_name=query_soil_ranking`；`answer_facts.items[0].name=睢宁县`
- `数据库校验断言`：调用 `query_soil_ranking(aggregation=county,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `睢宁县 / 昆山市 / 沛县`
- `预期实体`：`县区排行`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期排序结果`：`睢宁县 > 昆山市 > 沛县`
- `必含事实`：`39 / 37 / 36`
- `禁止事实`：`输出原始 records`
- `是否符合事实`：`是`
- `备注`：县区排行基准样例

### SM-RANK-002

- `CaseID`：`SM-RANK-002`
- `用户问题`：最近 30 天设备里前 5 个风险最高的是哪些
- `当前回答`：最近 30 天设备风险前列主要集中在 `SNS00213276`、`SNS00204885` 和 `SNS00213891`。其中 `SNS00213276` 与 `SNS00204885` 都是整段时间内持续 `waterlogging`，前者位于 `徐州市沛县`，后者位于 `苏州市昆山市`；`SNS00213891` 位于 `徐州市睢宁县`，同样属于需要优先复核的高风险设备。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_ranking`
- `预期 answer_type`：`soil_ranking_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：设备排行必须包含 city/county 上下文
- `结构化证据断言`：`answer_facts.items[0].name=SNS00213276`；`answer_facts.items[0].city=徐州市`
- `数据库校验断言`：调用 `query_soil_ranking(aggregation=device,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `SNS00213276 / SNS00204885 / SNS00213891`
- `预期实体`：`设备排行`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期排序结果`：`SNS00213276 > SNS00204885 > SNS00213891`
- `必含事实`：`徐州市沛县`、`苏州市昆山市`
- `禁止事实`：`只给设备号不给地区`
- `是否符合事实`：`是`
- `备注`：设备排行样例

### SM-RANK-003

- `CaseID`：`SM-RANK-003`
- `用户问题`：最近 30 天市级层面哪里最需要关注
- `当前回答`：按市级风险排序，最近 30 天最需要关注的是 `徐州市`，其后依次是 `淮安市`、`苏州市`、`常州市` 和 `扬州市`。其中徐州市的预警相关记录达到 `87` 条，是当前市级层面最突出的风险来源。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_ranking`
- `预期 answer_type`：`soil_ranking_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：聚合维度必须是 `city`
- `结构化证据断言`：`answer_facts.aggregation=city`；`answer_facts.items[0].name=徐州市`
- `数据库校验断言`：调用 `query_soil_ranking(aggregation=city,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top5 应为 `徐州市 / 淮安市 / 苏州市 / 常州市 / 扬州市`
- `预期实体`：`市级排行`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期排序结果`：`徐州市 > 淮安市 > 苏州市 > 常州市 > 扬州市`
- `必含事实`：`87`
- `禁止事实`：`聚合维度写成县区`
- `是否符合事实`：`是`
- `备注`：市级排行样例

### SM-RANK-004

- `CaseID`：`SM-RANK-004`
- `用户问题`：最近 7 天县区前 3 名是谁
- `当前回答`：如果只看最近 7 天，县区前 3 名分别是 `睢宁县`、`沛县` 和 `昆山市`。对应的预警相关记录分别是 `9`、`8` 和 `7` 条，说明短时间窗口内这三个县区的风险更集中。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_ranking`
- `预期 answer_type`：`soil_ranking_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：短时间窗排行与 30 天排行结果可以不同，但顺序必须真实成立
- `结构化证据断言`：`answer_facts.top_n=3`；`answer_facts.items[0].rank=1`
- `数据库校验断言`：调用 `query_soil_ranking(aggregation=county,top_n=3,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `睢宁县 / 沛县 / 昆山市`
- `预期实体`：`县区排行`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期排序结果`：`睢宁县 > 沛县 > 昆山市`
- `必含事实`：`9 / 8 / 7`
- `禁止事实`：`把 30 天数据混进 7 天排行`
- `是否符合事实`：`是`
- `备注`：时间窗排行样例

## Detail Cases（8）

### SM-DETAIL-001

- `CaseID`：`SM-DETAIL-001`
- `用户问题`：南通市最近 7 天详细情况怎么样
- `当前回答`：最近 7 天南通市共汇总 `259` 条记录，全部为未触发预警状态。最新一条记录来自 `SNS00204333`，时间是 `2026-04-13 23:59:17`，位于 `如东县`，20 厘米含水量 `92.43%`，当前没有发现需要升级处理的异常。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：详情类必须返回单对象 detail，不退化成概览
- `结构化证据断言`：`answer_facts.entity_name=南通市`；`answer_facts.record_count=259`
- `数据库校验断言`：调用 `query_soil_detail(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=259`，latest record 为 `SNS00204333 / 如东县 / 2026-04-13 23:59:17`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`259 / 92.43`
- `必含事实`：`SNS00204333`
- `禁止事实`：`存在明显预警`
- `是否符合事实`：`是`
- `备注`：地区详情样例

### SM-DETAIL-002

- `CaseID`：`SM-DETAIL-002`
- `用户问题`：SNS00204333 最近 7 天怎么样
- `当前回答`：设备 `SNS00204333` 最近 7 天共有 `7` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，位于 `南通市如东县`，20 厘米含水量 `92.43%`，目前没有异常告警。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：设备详情必须识别为 device，而不是 region
- `结构化证据断言`：`answer_facts.entity_type=device`；`answer_facts.entity_name=SNS00204333`
- `数据库校验断言`：调用 `query_soil_detail(sn=SNS00204333,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=7`，latest record `water20cm=92.43`
- `预期实体`：`SNS00204333`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`7 / 92.43`
- `必含事实`：`南通市如东县`
- `禁止事实`：`找不到设备`
- `是否符合事实`：`是`
- `备注`：设备详情基准样例

### SM-DETAIL-003

- `CaseID`：`SM-DETAIL-003`
- `用户问题`：如东最近怎么样
- `当前回答`：如果把“如东”按业务常用说法解析为 `如东县`，最近 7 天如东县共有 `42` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，最新设备是 `SNS00204333`，20 厘米含水量 `92.43%`，当前整体平稳。  
- `上下文`：无
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：地区别名应回到 `如东县`
- `结构化证据断言`：`answer_facts.entity_name=如东县`
- `数据库校验断言`：按标准实体 `如东县` 回查 `query_soil_detail(county=如东县,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=42`
- `预期实体`：`如东县`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`42 / 92.43`
- `必含事实`：`如东县`
- `禁止事实`：`把如东理解成其他地区`
- `是否符合事实`：`是`
- `备注`：地区别名样例

### SM-DETAIL-004

- `CaseID`：`SM-DETAIL-004`
- `用户问题`：那如东县呢
- `当前回答`：沿用上一轮“最近 7 天”的时间框架，如东县最近 7 天共有 `42` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，最新设备 `SNS00204333` 的 20 厘米含水量为 `92.43%`，当前没有异常告警。  
- `上下文`：上一轮已查询“南通市最近 7 天整体情况”
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：多轮继承时间窗，但对象切换为如东县
- `结构化证据断言`：`answer_facts.entity_name=如东县`；`query_result.entries[0].tool_args.county=如东县`
- `数据库校验断言`：调用 `query_soil_detail(county=如东县,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=42`
- `预期实体`：`如东县`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`42 / 92.43`
- `必含事实`：`沿用最近7天`
- `禁止事实`：`重新澄清时间窗`
- `是否符合事实`：`是`
- `备注`：多轮对象切换样例 1

### SM-DETAIL-005

- `CaseID`：`SM-DETAIL-005`
- `用户问题`：那 SNS00204333 呢
- `当前回答`：如果沿用上一轮的最近 30 天框架，设备 `SNS00204333` 在这段时间内有稳定数据，但没有触发预警。它位于 `南通市如东县`，最新记录时间仍是 `2026-04-13 23:59:17`，最新 20 厘米含水量 `92.43%`。  
- `上下文`：上一轮刚做完最近 30 天排行查询
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`normal`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：从 ranking 框架切换为单设备 detail
- `结构化证据断言`：`answer_facts.entity_type=device`；`answer_facts.entity_name=SNS00204333`
- `数据库校验断言`：调用 `query_soil_detail(sn=SNS00204333,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；应存在最新记录 `2026-04-13 23:59:17`
- `预期实体`：`SNS00204333`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`latest_record.water20cm=92.43`
- `必含事实`：`南通市如东县`
- `禁止事实`：`继续输出排行结果`
- `是否符合事实`：`是`
- `备注`：多轮对象切换样例 2

### SM-DETAIL-006

- `CaseID`：`SM-DETAIL-006`
- `用户问题`：睢宁县最近一个月异常情况怎么样
- `当前回答`：如果按异常视角看，睢宁县最近一个月需要重点关注。该时间窗共有 `210` 条记录，其中 `39` 条为预警相关记录，主要异常类型是 `涝渍`。最新一条普通记录虽然未触发预警，但近几条异常代表记录集中在设备 `SNS00213891`，说明局部点位风险较高。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`anomaly_focus`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：detail 异常视角应同时包含 latest_record 与 alert_records
- `结构化证据断言`：`answer_facts.output_mode=anomaly_focus`；`answer_facts.alert_records[0].sn=SNS00213891`
- `数据库校验断言`：调用 `query_soil_detail(county=睢宁县,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59,output_mode=anomaly_focus)`；应得到 `record_count=210`、`status_summary.waterlogging=39`
- `预期实体`：`睢宁县`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期关键指标`：`210 / 39`
- `必含事实`：`SNS00213891`
- `禁止事实`：`没有异常`
- `是否符合事实`：`是`
- `备注`：detail 异常视角样例

### SM-DETAIL-007

- `CaseID`：`SM-DETAIL-007`
- `用户问题`：南通市今年需要发预警吗
- `当前回答`：如果从预警视角看，南通市今年确实有需要重点关注的记录。全年共 `3811` 条记录，预警相关记录 `20` 条，最新代表性预警样例是 `2026-03-05 23:59:17` 启东市设备 `SNS00214096` 的 `154.31%` 涝渍记录；此外如东县还有一组一月中旬的重旱记录。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`warning_mode`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：warning_mode 必须提供 `warning_data`
- `结构化证据断言`：`answer_facts.warning_data.sn=SNS00214096`；`answer_facts.warning_data.water20cm=154.31`
- `数据库校验断言`：调用 `query_soil_detail(city=南通市,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=warning_mode)`；`warning_data` 应对应 `SNS00214096 / 启东市 / 154.31 / 2026-03-05 23:59:17`
- `预期实体`：`南通市`
- `预期时间窗`：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
- `预期关键指标`：`3811 / 20`
- `必含事实`：`SNS00214096`、`154.31`
- `禁止事实`：`全年完全没有预警`
- `是否符合事实`：`是`
- `备注`：detail 预警视角样例

### SM-DETAIL-008

- `CaseID`：`SM-DETAIL-008`
- `用户问题`：SNS00204334 这种情况需要注意什么
- `当前回答`：从建议视角看，设备 `SNS00204334` 当前最新记录已经恢复到未触发预警状态，但在 `2026-01-10` 到 `2026-01-14` 期间曾连续出现重旱记录。也就是说，这台设备近期不需要升级预警，不过仍建议结合一月中旬那段重旱历史，继续关注后续同类时段的水分波动。  
- `上下文`：无
- `预期 input_type`：`business_colloquial`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`soil_detail_answer`
- `预期 output_mode`：`advice_mode`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`无`
- `是否写查询日志`：是
- `关键断言`：建议必须绑定到真实历史异常，不得凭空扩展
- `结构化证据断言`：`answer_facts.output_mode=advice_mode`；`answer_facts.alert_records[0].warning_level=heavy_drought`
- `数据库校验断言`：调用 `query_soil_detail(sn=SNS00204334,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=advice_mode)`；应得到 `record_count=103`，alert records 连续覆盖 `2026-01-10 ~ 2026-01-14`
- `预期实体`：`SNS00204334`
- `预期时间窗`：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
- `预期关键指标`：`103 / heavy_drought 14`
- `必含事实`：`2026-01-10`、`2026-01-14`
- `禁止事实`：`当前仍在重旱`
- `是否符合事实`：`是`
- `备注`：detail 建议视角样例

## Fallback Cases（4）

### SM-FB-001

- `CaseID`：`SM-FB-001`
- `用户问题`：查一下 SNS00204333 在 2025 年 1 月的墒情
- `当前回答`：时间段 `2025-01-01 ~ 2025-01-31` 内没有 `SNS00204333` 的数据，可以扩大时间范围或查询其他时段。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`diagnose_empty_result`
- `预期 answer_type`：`fallback_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`no_data`
- `是否写查询日志`：是
- `关键断言`：必须区分 `no_data` 与 `entity_not_found`
- `结构化证据断言`：`answer_facts.diagnosis=no_data_in_window` 或 `query_result.entries[0].result.diagnosis=no_data_in_window`
- `数据库校验断言`：先查 `query_soil_detail(sn=SNS00204333,start=2025-01-01 00:00:00,end=2025-01-31 23:59:59)` 为空，再调用 `diagnose_empty_result(scenario=period_exists,sn=SNS00204333,...)`；诊断应为 `no_data_in_window`
- `预期实体`：`SNS00204333`
- `预期时间窗`：`2025-01-01 00:00:00 ~ 2025-01-31 23:59:59`
- `预期诊断类别`：`no_data_in_window`
- `必含事实`：`扩大时间范围`
- `禁止事实`：`设备不存在`
- `是否符合事实`：`是`
- `备注`：空时间窗样例

### SM-FB-002

- `CaseID`：`SM-FB-002`
- `用户问题`：查一下 SNS-UNKNOWN 最近一个月的数据
- `当前回答`：设备 `SNS-UNKNOWN` 在系统中不存在，请核对设备编号。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`diagnose_empty_result`
- `预期 answer_type`：`fallback_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`entity_not_found`
- `是否写查询日志`：是
- `关键断言`：对象不存在时不能误写成 no_data
- `结构化证据断言`：`query_result.entries[0].result.diagnosis=entity_not_found`
- `数据库校验断言`：调用 `diagnose_empty_result(scenario=device_exists,sn=SNS-UNKNOWN,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；诊断应为 `entity_not_found`
- `预期实体`：`SNS-UNKNOWN`
- `预期时间窗`：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
- `预期诊断类别`：`entity_not_found`
- `必含事实`：`核对设备编号`
- `禁止事实`：`只是时间窗没数据`
- `是否符合事实`：`是`
- `备注`：不存在对象样例

### SM-FB-003

- `CaseID`：`SM-FB-003`
- `用户问题`：直接告诉我南通市近 7 天有没有异常，不要查库
- `当前回答`：当前业务问题必须查询真实数据后才能回答。系统检测到模型未调用任何查询工具就直接作答，已拦截此回答，请换一种问法重试。  
- `上下文`：无
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`无（应被 P0 拦截）`
- `预期 answer_type`：`fallback_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`tool_missing`
- `是否写查询日志`：否
- `关键断言`：业务问题未命中 Tool 不得直接回答
- `结构化证据断言`：`tool_trace=[]`；`query_result={}`；`fallback_reason=tool_missing`
- `数据库校验断言`：不直接查库；验证拦截逻辑优先于回答生成
- `预期诊断类别`：`tool_missing`
- `必含事实`：`必须查询真实数据`
- `禁止事实`：`南通市近7天很正常` 这类未查库业务结论
- `是否符合事实`：`是`
- `备注`：P0 红线样例

### SM-FB-004

- `CaseID`：`SM-FB-004`
- `用户问题`：SNS00204333 最近有数据吗（模拟模型错误回答“没有数据”）
- `当前回答`：回答声称无数据，但查询结果中存在数据，已安全降级，请重新提问。  
- `上下文`：内部事实核验阶段发现回答与查询结果冲突
- `预期 input_type`：`business_direct`
- `是否域内业务问题`：是
- `是否必须命中 Tool`：是
- `预期 Tool`：`query_soil_detail`
- `预期 answer_type`：`fallback_answer`
- `预期 output_mode`：`无`
- `预期 guidance_reason`：`无`
- `预期 fallback_reason`：`fact_check_failed`
- `是否写查询日志`：是
- `关键断言`：FactCheck 必须能拦截“有数据却回答无数据”的冲突
- `结构化证据断言`：`query_result.entries[0].result.record_count > 0`；`fallback_reason=fact_check_failed`
- `数据库校验断言`：调用 `query_soil_detail(sn=SNS00204333,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；实际 `record_count=7`，因此任何“无数据”回答都应判定为事实不一致并触发 fallback
- `预期实体`：`SNS00204333`
- `预期时间窗`：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
- `预期诊断类别`：`fact_check_failed`
- `必含事实`：`存在真实数据`
- `禁止事实`：`无数据`
- `是否符合事实`：`是`
- `备注`：事实核验失败样例
