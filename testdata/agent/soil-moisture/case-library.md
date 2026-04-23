# 墒情 Agent Case Library（130 个正式 Case）

本文件是当前 `soil-moisture` Agent 的唯一正式 Case 主库。后续对正式 Case 的新增、删减、修订，都只改这里。

## 维护边界

- 主库范围：以 `2026-04-22` 商务评审版整理出的 `36` 个 Case 为基础，并补充到 `130` 个正式 Case。
- 分布原则：不按 10 类均分；按业务价值和真实使用频率加权，重点补充墒情概览、排名对比、地区/设备详情、异常分析、预警模板输出，非业务、安全提示、能力边界只保留少量代表性样例。
- 字段来源：
  - 前 `36` 个 Case 的 `一级分类 / 二级分类 / 用户问题 / 当前回答` 以 `outputs/business-review-20260422/smart-agriculture-36问题-商务评审版-2026-04-22.xlsx` 为准。
  - 补充 Case 直接沉淀在本文件中，先标注为“补充待实测”，待下一轮服务复测后回填真实当前回答。
- `docs/testing/agent/soil-moisture/` 只保留测试说明与维护规则，不再维护第二套完整 Case 内容。

## 分类覆盖

| 一级分类 | Case 数 | CaseID |
|---|---:|---|
| A. 非业务 / 安全提示 | 6 | SH-01, SH-02, SH-03, SH-04, SH-05, SH-06 |
| B. 澄清引导 | 8 | CL-01, CL-02, CL-03, CL-04, CL-05, CL-06, CL-07, CL-08 |
| C. 墒情概览 | 15 | SU-01, SU-02, SU-03, SU-04, SU-05, SU-06, SU-07, SU-08, SU-09, SU-10, SU-11, SU-12, SU-13, SU-14, SU-15 |
| D. 排名对比 | 15 | RK-01, RK-02, RK-03, RK-04, RK-05, RK-06, RK-07, RK-08, RK-09, RK-10, RK-11, RK-12, RK-13, RK-14, RK-15 |
| E. 地区 / 设备详情 | 18 | DT-01, DT-02, DT-03, DT-04, DT-05, DT-06, DT-07, DT-08, DT-09, DT-10, DT-11, DT-12, DT-13, DT-14, DT-15, DT-16, DT-17, DT-18 |
| F. 异常分析 | 16 | AN-01, AN-02, AN-03, AN-04, AN-05, AN-06, AN-07, AN-08, AN-09, AN-10, AN-11, AN-12, AN-13, AN-14, AN-15, AN-16 |
| G. 预警模板输出 | 16 | WA-01, WA-02, WA-03, WA-04, WA-05, WA-06, WA-07, WA-08, WA-09, WA-10, WA-11, WA-12, WA-13, WA-14, WA-15, WA-16 |
| H. 指标解释 / 指导建议 | 11 | AD-01, AD-02, AD-03, AD-04, AD-05, AD-06, AD-07, AD-08, AD-09, AD-10, AD-11 |
| I. 无数据 / 找不到 / 兜底 | 10 | FB-01, FB-02, FB-03, FB-04, FB-05, FB-06, FB-07, FB-08, FB-09, FB-10 |
| J. 能力边界 | 5 | BO-01, BO-02, BO-03, BO-04, BO-05 |

## A. 非业务 / 安全提示

### SH-01

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/问候
- `用户问题`：你好
- `当前回答`：你好，我可以帮助查询土壤墒情、分析异常、生成预警模板，并提供保守的管理建议。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`greeting`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；回复能力范围与示例问题
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SH-02

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/能力
- `用户问题`：你能做什么
- `当前回答`：我当前支持墒情概览、地区/设备详情、异常分析、预警判断和模板输出。你可以直接给地区、设备或时间范围来问。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`capability_question`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；列出墒情查询、异常分析、模板输出能力
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SH-03

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/乱问
- `用户问题`：？？？
- `当前回答`：我是墒情智能助手，可以帮你查询墒情概览、地区/设备详情、异常分析和预警模板。你可以问：最近墒情怎么样？如东县最近怎么样？SNS00204333 需要发预警吗？
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`meaningless_input`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；不答非所问
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SH-04

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/身份
- `用户问题`：你是谁
- `当前回答`：待实测回填；期望回答要点：说明自己是墒情智能助手，能做墒情概览、地区/设备详情、异常分析和预警模板，不扩展到无关领域。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`capability_question`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；身份说明必须回到墒情能力范围
- `备注`：补充非业务身份类问法，避免模型自由闲聊。

### SH-05

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/闲聊
- `用户问题`：哈哈哈
- `当前回答`：待实测回填；期望回答要点：简短回应，并引导用户可以询问墒情概览、地区详情、设备异常或预警模板。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`meaningless_input`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；不展开闲聊；回到业务示例
- `备注`：补充轻度闲聊输入。

### SH-06

- `一级分类`：A. 非业务 / 安全提示
- `二级分类`：非业务/在吗
- `用户问题`：在吗
- `当前回答`：待实测回填；期望回答要点：简短确认在线，并引导用户直接提地区、设备或时间范围的墒情问题。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`greeting`
- `预期 intent`：无
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`safe_hint_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；不展开闲聊
- `备注`：补充常见问候类短句。


## B. 澄清引导

### CL-01

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/短句
- `用户问题`：看看
- `当前回答`：你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不查库；给出 4~5 个可选问题方向
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### CL-02

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/泛查
- `用户问题`：帮我查一下
- `当前回答`：你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不默认继承任何隐含意图
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### CL-03

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/无上下文追问
- `用户问题`：那个情况呢
- `当前回答`：你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无有效业务上下文
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：因缺上下文，不能硬继承
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### CL-04

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/只有地区
- `用户问题`：南京
- `当前回答`：待实测回填；期望回答要点：识别到南京市，但询问用户想看概览、异常、排名还是最新详情。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：`city_name=南京市`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：只有地区没有查询动作时，不默认查库；应澄清查询方向
- `备注`：补充“有槽位但意图不足”的问法。

### CL-05

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/泛指数据
- `用户问题`：数据怎么样
- `当前回答`：待实测回填；期望回答要点：提示用户补充地区、设备或时间范围，并给出 2~3 个可选问法。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不得把“数据”默认解释为全省最新概览
- `备注`：补充泛指数据类输入。

### CL-06

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/地区+泛查
- `用户问题`：查一下南京
- `当前回答`：待实测回填；期望回答要点：识别南京市，但询问用户要看概览、异常、排名还是详情。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：`city_name=南京市`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：地区识别可成功，但不能直接查库
- `备注`：补充带地区但意图不足的问法。

### CL-07

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/时间不足
- `用户问题`：帮我看看最近的
- `当前回答`：待实测回填；期望回答要点：提示补充地区、设备或要看的是概览/异常/预警。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：`time=最近`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：只有时间槽位时也不能默认查全局概览
- `备注`：补充只有时间没有对象的输入。

### CL-08

- `一级分类`：B. 澄清引导
- `二级分类`：澄清/结论追问
- `用户问题`：严重吗
- `当前回答`：待实测回填；期望回答要点：提示补充地区、设备或上一轮上下文对象。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无有效业务上下文
- `预期 input_type`：`ambiguous_low_confidence`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：缺对象时不能直接给严重性结论
- `备注`：补充结论型追问。


## C. 墒情概览

### SU-01

- `一级分类`：C. 墒情概览
- `二级分类`：墒情概览
- `用户问题`：最近墒情怎么样
- `当前回答`：当前整体墒情概况：20cm平均相对含水量约 93.77%，当前有 44 个点位需要重点关注。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time=最近7天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：内部以库内最新业务时间为基准，不用系统当前时间；对外默认不展示样本数、最新业务时间、数据来源
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SU-02

- `一级分类`：C. 墒情概览
- `二级分类`：近7天概览
- `用户问题`：最近7天墒情整体情况如何
- `当前回答`：当前整体墒情概况：20cm平均相对含水量约 93.77%，当前有 44 个点位需要重点关注。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time_range=last_7_days`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：按明确时间窗查询，不使用导入批次语义
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SU-03

- `一级分类`：C. 墒情概览
- `二级分类`：城市概览
- `用户问题`：南通市最近7天墒情怎么样
- `当前回答`：南通市墒情概况：20cm平均相对含水量约 95.39%，当前未发现需要重点关注的异常点位。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=南通市; time=近7天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：回答应突出地区概况与关注点，不暴露样本数、最新业务时间、数据来源等内部统计口径
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SU-04

- `一级分类`：C. 墒情概览
- `二级分类`：最新概览
- `用户问题`：现在的墒情
- `当前回答`：当前整体墒情概况：20cm平均相对含水量约 93.74%，当前有 5 个点位需要重点关注。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time=最新业务时间`
- `预期 query_type / SQL`：`SQL-07 场景4 -> SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：先查库内最新业务时间，再汇总；不能硬查当天；对外不必直接展示该内部基准时间
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### SU-05

- `一级分类`：C. 墒情概览
- `二级分类`：城市简称概览
- `用户问题`：南京最近一个月墒情怎么样
- `当前回答`：待实测回填；期望回答要点：按南京市近 30 天输出概况结论、平均水分和关注点数量，不暴露内部统计口径。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=南京市; time=30天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：`南京` 必须补全为 `南京市`；概览意图不应被改成详情意图
- `备注`：补充地区别名与概览组合。

### SU-06

- `一级分类`：C. 墒情概览
- `二级分类`：县区概览
- `用户问题`：如东县本周整体情况如何
- `当前回答`：待实测回填；期望回答要点：按如东县本周输出整体墒情概况和重点关注点。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=本周`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：县级概览需补齐父级市；不能只落裸 `county_name`
- `备注`：补充县区概览。

### SU-07

- `一级分类`：C. 墒情概览
- `二级分类`：最新城市概览
- `用户问题`：镇江市最新墒情概况
- `当前回答`：待实测回填；期望回答要点：以库内最新业务时间为基准，输出镇江市最新概况。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=镇江市; time=最新业务时间`
- `预期 query_type / SQL`：`SQL-07 场景4 -> SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：“最新”必须使用库内最新业务时间，不使用系统当前日期
- `备注`：补充城市最新概览。

### SU-08

- `一级分类`：C. 墒情概览
- `二级分类`：全局概览
- `用户问题`：全省最近7天墒情概况
- `当前回答`：待实测回填；期望回答要点：输出最近7天整体概况和关注点，不暴露内部统计字段。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time=7天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：全局概览允许，但不能退化成全表明细扫描
- `备注`：补充全局概览问法。

### SU-09

- `一级分类`：C. 墒情概览
- `二级分类`：本周城市概览
- `用户问题`：南通本周整体情况
- `当前回答`：待实测回填；期望回答要点：按南通市本周输出整体概况和关注点。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=南通市; time=本周`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：城市本周概览应落对时间范围和地区
- `备注`：补充城市本周概览。

### SU-10

- `一级分类`：C. 墒情概览
- `二级分类`：本周总览
- `用户问题`：这周墒情总览
- `当前回答`：待实测回填；期望回答要点：给出本周整体概况，并提示重点关注对象数量。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time=本周`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：不能把“这周”解析成系统当前周，要按业务时间周解析
- `备注`：补充周维度概览。

### SU-11

- `一级分类`：C. 墒情概览
- `二级分类`：城市近7天详情
- `用户问题`：南京最近7天墒情情况
- `当前回答`：南京市 最新监测时间为 2026-04-13 23:59:17，位于 南京市高淳区，20cm 相对含水量 130.51%，规则判断为 未达到预警条件。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南京市; time_range=last_7_days`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：城市查询必须按明确时间窗查询，不使用导入批次语义
- `备注`：由原批次语义 Case 改成城市+时间窗详情。

### SU-12

- `一级分类`：C. 墒情概览
- `二级分类`：月度总览
- `用户问题`：最近30天整体情况
- `当前回答`：待实测回填；期望回答要点：给出近30天整体墒情概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time=30天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：月度概览应使用30天窗口，不扩展成排名
- `备注`：补充月度总览。

### SU-13

- `一级分类`：C. 墒情概览
- `二级分类`：县区概览补充
- `用户问题`：如东县最近7天整体墒情
- `当前回答`：待实测回填；期望回答要点：按如东县近7天输出整体概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=7天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：县区概览需要补齐父级市
- `备注`：补充县区概览样本。

### SU-14

- `一级分类`：C. 墒情概览
- `二级分类`：两周城市概览
- `用户问题`：镇江市近两周总体情况
- `当前回答`：待实测回填；期望回答要点：按镇江市近14天输出整体概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=镇江市; time=14天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：两周概览应使用14天窗口
- `备注`：补充两周城市概览。

### SU-15

- `一级分类`：C. 墒情概览
- `二级分类`：近30天总览
- `用户问题`：最近30天整体墒情概览
- `当前回答`：当前整体墒情概况：20cm平均相对含水量约 95.31%，当前有 252 个点位需要重点关注。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`time_range=last_30_days`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：概览必须按明确时间窗查询，不使用导入批次语义
- `备注`：补充近30天总览。


## D. 排名对比

### RK-01

- `一级分类`：D. 排名对比
- `二级分类`：排名/县区
- `用户问题`：过去一个月哪里最严重
- `当前回答`：当前需优先关注的县区如下：1. 金湖县；2. 溧阳市；3. 金坛区；4. 泗洪县；5. 灌南县。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=30天; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：默认按县区排名；对外只给综合风险顺序，不直接暴露 `soil_anomaly_score` 等内部字段名
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### RK-02

- `一级分类`：D. 排名对比
- `二级分类`：排名/设备Top10
- `用户问题`：前10个最严重设备
- `当前回答`：当前需优先关注的设备如下：1. SNS00213900；2. SNS00213936；3. SNS00204927；4. SNS00213842；5. SNS00204610；6. SNS00213809；7. SNS00204938；8. SNS00213891；9. SNS00213858；10. SNS00204659。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`top_n=10; aggregation=device`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：返回设备 Top10，不超过 10 条；不输出“异常分”等内部实现词汇
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### RK-03

- `一级分类`：D. 排名对比
- `二级分类`：排名/市级
- `用户问题`：哪个市最严重
- `当前回答`：当前需优先关注的地市如下：1. 宿迁市；2. 连云港市；3. 淮安市；4. 常州市；5. 泰州市。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`aggregation=city`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：应走市级聚合，不应默认仍按县区返回；对外不暴露内部排序实现细节
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### RK-04

- `一级分类`：D. 排名对比
- `二级分类`：排名/TopN超限
- `用户问题`：给我前100个最严重设备
- `当前回答`：当前最多支持查看前 20 个结果，你可以改问“前 20 个最严重设备”。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`top_n=100`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`clarify`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：命中 `max_top_n=20`；提示是否改查前 20
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### RK-05

- `一级分类`：D. 排名对比
- `二级分类`：排名/大范围阻断
- `用户问题`：全省近三年所有设备排名
- `当前回答`：当前设备排名时间范围过大，请缩小到近一年内，或改查地区级排名。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=3年; aggregation=device`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`block`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：命中时间窗超限 + 大范围扫描限制，不得继续查库
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### RK-06

- `一级分类`：D. 排名对比
- `二级分类`：排名/城市内县区
- `用户问题`：南通市过去一个月哪里最严重
- `当前回答`：待实测回填；期望回答要点：按南通市下属县区给出近 30 天风险顺序，不展示异常分字段名。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`city_name=南通市; time=30天; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：带城市约束时，只在该城市范围内排名
- `备注`：补充区域内排名。

### RK-07

- `一级分类`：D. 排名对比
- `二级分类`：排名/设备Top5
- `用户问题`：最近7天最严重的5个设备
- `当前回答`：待实测回填；期望回答要点：返回设备 Top5，最多 5 条，不输出内部异常分。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=7天; top_n=5; aggregation=device`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：`top_n=5` 必须生效；不得超过 5 条
- `备注`：补充设备 TopN 小样本。

### RK-08

- `一级分类`：D. 排名对比
- `二级分类`：排名/最高风险县区
- `用户问题`：哪个县最近风险最高
- `当前回答`：待实测回填；期望回答要点：默认按县区聚合返回最高风险对象和简短解释。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=最近; top_n=1; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：没有指定层级但出现“县”时，应按县区聚合
- `备注`：补充最高风险单对象排名。

### RK-09

- `一级分类`：D. 排名对比
- `二级分类`：排名/县区Top3
- `用户问题`：最近一个月前3个最严重县区
- `当前回答`：待实测回填；期望回答要点：返回县区Top3和简短排序说明。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=30天; top_n=3; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：Top3必须准确落到县区聚合
- `备注`：补充县区Top3排名。

### RK-10

- `一级分类`：D. 排名对比
- `二级分类`：排名/设备近两周
- `用户问题`：最近两周哪些设备风险最高
- `当前回答`：待实测回填；期望回答要点：输出近14天高风险设备排序。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=14天; aggregation=device`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：时间窗为14天；默认返回受控条数
- `备注`：补充两周设备排名。

### RK-11

- `一级分类`：D. 排名对比
- `二级分类`：排名/市内区县
- `用户问题`：镇江市哪个区最严重
- `当前回答`：待实测回填；期望回答要点：在镇江市范围内返回最高风险区县。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`city_name=镇江市; top_n=1; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：带城市约束时只能在该市内部排序
- `备注`：补充市内区县排名。

### RK-12

- `一级分类`：D. 排名对比
- `二级分类`：排名/县区Top10
- `用户问题`：最近30天最严重的10个县区
- `当前回答`：待实测回填；期望回答要点：返回县区Top10，不暴露内部排序字段。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`time=30天; top_n=10; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：Top10在门禁允许范围内，不应误触发澄清
- `备注`：补充允许范围内的较大TopN。

### RK-13

- `一级分类`：D. 排名对比
- `二级分类`：排名/城市范围
- `用户问题`：南京最近一个月最严重的是哪里
- `当前回答`：待实测回填；期望回答要点：在南京市范围内给出高风险区域顺序。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`city_name=南京市; time=30天; aggregation=county`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：地区范围与时间窗都应命中
- `备注`：补充城市范围排名。

### RK-14

- `一级分类`：D. 排名对比
- `二级分类`：排名/城市设备Top5
- `用户问题`：南通市近7天前5个高风险设备
- `当前回答`：待实测回填；期望回答要点：返回南通市近7天设备Top5。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`city_name=南通市; time=7天; top_n=5; aggregation=device`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：城市范围+设备聚合必须同时生效
- `备注`：补充城市设备TopN。

### RK-15

- `一级分类`：D. 排名对比
- `二级分类`：排名/县区设备Top3
- `用户问题`：如东县最近最需要关注的3个设备
- `当前回答`：待实测回填；期望回答要点：返回如东县范围内最需要关注的3个设备。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_severity_ranking`
- `预期 slots`：`county_name=如东县; city_name=南通市; top_n=3; aggregation=device`
- `预期 query_type / SQL`：`severity_ranking / SQL-02`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_ranking_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：县区约束下设备排名不能扩大到全市
- `备注`：补充区县设备排名。


## E. 地区 / 设备详情

### DT-01

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：地区详情
- `用户问题`：如东县最近怎么样
- `当前回答`：如东县 最新监测时间为 2026-04-13 23:59:17，位于 南通市如东县，20cm 相对含水量 70.09%，规则判断为 未达到预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=如东县; time=最近`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：包含最新记录、20cm 水分、状态判断；不要求对外展示来源文件
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### DT-02

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：设备详情
- `用户问题`：SNS00204333 最近有没有异常
- `当前回答`：SNS00204333 最新监测时间为 2026-04-13 23:59:17，位于 南通市如东县，20cm 相对含水量 92.43%，规则判断为 未达到预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00204333; time=最近`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：能正确给出该设备的最新事实与状态判断，不把规则判断写成自由发挥
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### DT-03

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：多轮继承地区
- `用户问题`：那上周的呢
- `当前回答`：请补充地区、设备或时间范围后再查询。例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：上一轮已确认 `county_name=如东县`
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=继承如东县; time=上周`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：正确继承地区，只重算时间范围
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### DT-04

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：多轮继承设备指标
- `用户问题`：换成20cm看
- `当前回答`：请补充地区、设备或时间范围后再查询。例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：上一轮设备详情上下文有效
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=继承; metric=water20cm`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：只继承白名单槽位，不继承无关输出意图
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### DT-05

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：上下文衰减
- `用户问题`：有没有问题
- `当前回答`：请补充地区、设备或时间范围后再查询。例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：距离上次明确对象已 4~5 轮
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`clarification_needed`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：命中上下文衰减；不能继续强继承旧对象
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### DT-06

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：城市简称详情
- `用户问题`：南京最近一个月的数据
- `当前回答`：待实测回填；期望回答要点：按南京市近 30 天输出地区详情或最新代表性事实，并给出状态判断。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南京市; time=30天`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：`南京` 必须补全为 `南京市`，不能退回默认概览
- `备注`：补充地区别名详情类 Case。

### DT-07

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：县区简称详情
- `用户问题`：如东最近怎么样
- `当前回答`：待实测回填；期望回答要点：按如东县最新或最近范围输出事实与状态判断。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=最近`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：县级简称补全后需补齐父级市
- `备注`：补充县级简称详情。

### DT-08

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：开发区详情
- `用户问题`：镇江经开区最近墒情
- `当前回答`：待实测回填；期望回答要点：按镇江经开区输出最新墒情事实和状态判断。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=镇江经开区; city_name=镇江市; time=最近`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：开发区名称应按有效地区解析，不应误判为无数据
- `备注`：补充非典型行政区名称。

### DT-09

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：城市详情
- `用户问题`：南京市最近怎么样
- `当前回答`：待实测回填；期望回答要点：输出南京市最新或最近范围的事实与状态判断。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南京市; time=最近`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：城市详情不应退回概览
- `备注`：补充规范城市名详情。

### DT-10

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：城市周详情
- `用户问题`：南通市这周怎么样
- `当前回答`：待实测回填；期望回答要点：输出南通市本周事实和状态判断。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南通市; time=本周`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：本周范围应按业务时间解析
- `备注`：补充城市时间范围详情。

### DT-11

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：设备详情补充
- `用户问题`：SNS00213807 最近有没有异常
- `当前回答`：待实测回填；期望回答要点：给出设备最新事实和状态判断。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00213807; time=最近`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：设备SN应精确命中，不误判为异常清单问法
- `备注`：补充第二设备详情样本。

### DT-12

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：多轮继承指标40cm
- `用户问题`：再看40cm
- `当前回答`：待实测回填；期望回答要点：在有效上一轮设备详情上下文下，只切换到40cm指标查看。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮设备详情上下文有效
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=继承; metric=water40cm`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：只继承白名单槽位，不改对象
- `备注`：补充多轮指标切换。

### DT-13

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：多轮继承指标10cm
- `用户问题`：再看10cm
- `当前回答`：待实测回填；期望回答要点：在有效上一轮设备详情上下文下，切换到10cm指标查看。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮设备详情上下文有效
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=继承; metric=water10cm`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：继续只继承白名单槽位
- `备注`：补充另一深度指标切换。

### DT-14

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：多轮继承时间
- `用户问题`：南京上周情况呢
- `当前回答`：待实测回填；期望回答要点：若上一轮已确认南京市对象，则只重算上周时间范围。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已确认 city_name=南京市
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=继承南京市; time=上周`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：多轮中只切换时间，不更改地区
- `备注`：补充多轮时间继承。

### DT-15

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：县区日详情
- `用户问题`：如东县昨天怎么样
- `当前回答`：待实测回填；期望回答要点：按如东县昨天范围输出事实与状态。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=昨天`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：昨天应解析成业务时间相关的单日范围
- `备注`：补充单日县区详情。

### DT-16

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：城市月详情
- `用户问题`：镇江市最近一个月数据
- `当前回答`：待实测回填；期望回答要点：按镇江市近30天输出地区详情。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=镇江市; time=30天`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：详情问法不应退回概览
- `备注`：补充城市月度详情。

### DT-17

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：开发区详情补充
- `用户问题`：镇江经开区这周怎么样
- `当前回答`：待实测回填；期望回答要点：按镇江经开区本周输出事实与状态。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=镇江经开区; city_name=镇江市; time=本周`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：开发区名称应按有效地区解析
- `备注`：补充开发区周详情。

### DT-18

- `一级分类`：E. 地区 / 设备详情
- `二级分类`：设备日详情
- `用户问题`：SNS00204333 昨天数据怎么样
- `当前回答`：待实测回填；期望回答要点：给出该设备昨天的数据事实与状态。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00204333; time=昨天`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：设备日详情应命中单设备单日查询语义
- `备注`：补充设备单日详情。


## F. 异常分析

### AN-01

- `一级分类`：F. 异常分析
- `二级分类`：异常分析
- `用户问题`：最近有没有异常
- `当前回答`：当前共识别出 44 个异常点位，重点关注：淮安区（涝渍）；睢宁县（涝渍）；溧阳市（重旱）；昆山市（涝渍）；沛县（涝渍）。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：SQL 只拉候选；最终异常统计以规则复判结果为准，对外不直接展示规则引擎名称
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AN-02

- `一级分类`：F. 异常分析
- `二级分类`：异常关注点
- `用户问题`：哪些地方需要关注
- `当前回答`：当前共识别出 44 个异常点位，重点关注：淮安区（涝渍）；睢宁县（涝渍）；溧阳市（重旱）；昆山市（涝渍）；沛县（涝渍）。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：输出需含异常数量和重点关注对象，不暴露内部规则链路说明
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AN-03

- `一级分类`：F. 异常分析
- `二级分类`：重旱异常
- `用户问题`：有没有重旱
- `当前回答`：当前共识别出 44 个异常点位，重点关注：淮安区（涝渍）；睢宁县（涝渍）；溧阳市（重旱）；昆山市（涝渍）；沛县（涝渍）。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`status_target=heavy_drought`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：“重旱”判断必须来自规则引擎，但对外回答不直接点名内部规则组件
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AN-04

- `一级分类`：F. 异常分析
- `二级分类`：异常时间窗超限
- `用户问题`：查过去5年异常点位
- `当前回答`：异常查询时间范围过大，请缩小到近 180 天内后再查。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=5年`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`clarify`
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：命中异常查询最大时间窗 180 天
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AN-05

- `一级分类`：F. 异常分析
- `二级分类`：城市异常
- `用户问题`：南京最近有没有异常
- `当前回答`：待实测回填；期望回答要点：按南京市最近范围输出异常数量、类型和重点对象；没有异常则明确说明未发现重点异常。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=南京市; time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：异常结论必须以规则复判为准，不只看 SQL 候选
- `备注`：补充地区异常分析。

### AN-06

- `一级分类`：F. 异常分析
- `二级分类`：设备重旱
- `用户问题`：SNS00204333 近7天有没有重旱
- `当前回答`：待实测回填；期望回答要点：围绕该设备近 7 天判断是否出现重旱，并说明依据。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`device_sn=SNS00204333; time=7天; status_target=heavy_drought`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：重旱判断必须来自规则引擎，不能根据单个数值自由发挥
- `备注`：补充设备 + 异常类型组合。

### AN-07

- `一级分类`：F. 异常分析
- `二级分类`：涝渍异常
- `用户问题`：最近有没有涝渍
- `当前回答`：待实测回填；期望回答要点：输出最近是否存在涝渍点位和重点对象；没有则明确说明未发现。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=最近; status_target=waterlogging`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：异常类型筛选应落到 `waterlogging`，不要混成所有异常
- `备注`：补充涝渍异常类型。

### AN-08

- `一级分类`：F. 异常分析
- `二级分类`：城市异常关注
- `用户问题`：南京哪些地方需要关注
- `当前回答`：待实测回填；期望回答要点：输出南京市范围内重点关注对象与异常概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=南京市; time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：带城市范围的异常分析要收敛到该市
- `备注`：补充城市异常关注问法。

### AN-09

- `一级分类`：F. 异常分析
- `二级分类`：城市重旱
- `用户问题`：南通最近有没有重旱
- `当前回答`：待实测回填；期望回答要点：判断南通市最近是否存在重旱异常。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=南通市; time=最近; status_target=heavy_drought`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：异常类型与地区范围必须同时生效
- `备注`：补充地区+异常类型组合。

### AN-10

- `一级分类`：F. 异常分析
- `二级分类`：县区异常
- `用户问题`：如东县最近有异常吗
- `当前回答`：待实测回填；期望回答要点：输出如东县最近异常概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：县区异常分析需补齐父级市
- `备注`：补充县区异常。

### AN-11

- `一级分类`：F. 异常分析
- `二级分类`：异常对象统计
- `用户问题`：最近异常最多的是哪里
- `当前回答`：待实测回填；期望回答要点：按异常数量或关注对象给出重点区域，不暴露内部实现口径。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=最近`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：仍归入异常分析，不误走severity ranking
- `备注`：补充异常统计式问法。

### AN-12

- `一级分类`：F. 异常分析
- `二级分类`：设备异常清单
- `用户问题`：最近一周有哪些设备异常
- `当前回答`：待实测回填；期望回答要点：输出近一周异常设备对象列表和简述。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=7天; aggregation=device`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：异常清单问法不应直接走severity ranking
- `备注`：补充设备异常清单。

### AN-13

- `一级分类`：F. 异常分析
- `二级分类`：城市涝渍
- `用户问题`：镇江市最近有涝渍吗
- `当前回答`：待实测回填；期望回答要点：判断镇江市最近是否存在涝渍异常。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=镇江市; time=最近; status_target=waterlogging`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：涝渍类型筛选必须生效
- `备注`：补充城市涝渍异常。

### AN-14

- `一级分类`：F. 异常分析
- `二级分类`：月度异常概况
- `用户问题`：南京近30天异常概况
- `当前回答`：待实测回填；期望回答要点：输出南京市近30天异常概况。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=南京市; time=30天`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：月度异常概况不应退成普通概览
- `备注`：补充月度异常分析。

### AN-15

- `一级分类`：F. 异常分析
- `二级分类`：设备异常补充
- `用户问题`：SNS00213807 最近7天有异常吗
- `当前回答`：待实测回填；期望回答要点：判断该设备近7天是否存在异常。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`device_sn=SNS00213807; time=7天`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：设备异常分析应围绕单设备范围
- `备注`：补充设备异常补充样本。

### AN-16

- `一级分类`：F. 异常分析
- `二级分类`：县区关注清单
- `用户问题`：最近哪些县区需要重点关注
- `当前回答`：待实测回填；期望回答要点：输出近期待重点关注的县区对象。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`time=最近; aggregation=county`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：`yes`
- `是否写查询日志`：是
- `关键断言`：异常关注对象可按县区汇总，但仍属于异常链路
- `备注`：补充县区关注清单。


## G. 预警模板输出

### WA-01

- `一级分类`：G. 预警模板输出
- `二级分类`：预警模板
- `用户问题`：生成一条墒情预警
- `当前回答`：2026 年 04 月 13 日 23 时 盐城市 东台市 SN 编号 SNS00206467 土壤墒情仪监测到相对含水量 73.71%，预警等级 未达到预警条件，请大田/设施大棚/林果相关主体关注！ 当前记录未达到正式预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`need_template=true`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：必须先规则判断，再决定是否触发模板输出
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### WA-02

- `一级分类`：G. 预警模板输出
- `二级分类`：设备预警判断
- `用户问题`：SNS00204333 需要发预警吗
- `当前回答`：2026 年 04 月 13 日 23 时 南通市 如东县 SN 编号 SNS00204333 土壤墒情仪监测到相对含水量 92.43%，预警等级 未达到预警条件，请大田/设施大棚/林果相关主体关注！ 当前记录未达到正式预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00204333`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：未触发时内部应为 `soil_status=not_triggered; warning_level=none`
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### WA-03

- `一级分类`：G. 预警模板输出
- `二级分类`：严格模板
- `用户问题`：按模板输出 SNS00213807 最新预警
- `当前回答`：2026 年 04 月 13 日 23 时 镇江市 镇江经开区 SN 编号 SNS00213807 土壤墒情仪监测到相对含水量 116.46%，预警等级 未达到预警条件，请大田/设施大棚/林果相关主体关注！ 当前记录未达到正式预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00213807; render_mode=strict`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：`strict_mode` 只能输出模板正文 + 极少量固定补充
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### WA-04

- `一级分类`：G. 预警模板输出
- `二级分类`：模板+解释
- `用户问题`：按模板输出并解释原因
- `当前回答`：2026 年 04 月 13 日 23 时 盐城市 东台市 SN 编号 SNS00206467 土壤墒情仪监测到相对含水量 73.71%，预警等级 未达到预警条件，请大田/设施大棚/林果相关主体关注！ 当前记录未达到正式预警条件。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`render_mode=plus_explanation`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：模板正文与解释段必须分区输出，不能揉成一段
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### WA-05

- `一级分类`：G. 预警模板输出
- `二级分类`：未触发不生成模板
- `用户问题`：如果 SNS00204333 没达到预警条件，就不要生成模板
- `当前回答`：待实测回填；期望回答要点：先判断是否达到预警条件；未触发时明确说明未达到，不输出正式预警模板正文。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00204333; render_mode=conditional_no_template_if_not_triggered`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：未触发时内部应为 `soil_status=not_triggered; warning_level=none`，不得硬生成模板
- `备注`：补充未触发预警的模板边界。

### WA-06

- `一级分类`：G. 预警模板输出
- `二级分类`：地区预警判断
- `用户问题`：如东县需要发墒情预警吗
- `当前回答`：待实测回填；期望回答要点：按如东县最新事实判断是否触发预警；触发时给等级，未触发时说明未达到条件。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`county_name=如东县; city_name=南通市`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：地区预警判断必须先查事实再跑规则，不能只按地区名判断
- `备注`：补充地区级预警判断。

### WA-07

- `一级分类`：G. 预警模板输出
- `二级分类`：正式口径预警
- `用户问题`：按正式口径输出一条最新墒情预警
- `当前回答`：待实测回填；期望回答要点：若触发预警，使用正式模板正文；若未触发，说明未达到预警条件。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`render_mode=strict; time=最新业务时间`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：`strict_mode` 下模板正文不得被自由改写
- `备注`：补充正式模板口径。

### WA-08

- `一级分类`：G. 预警模板输出
- `二级分类`：设备预警判断补充
- `用户问题`：SNS00213807 需要发预警吗
- `当前回答`：待实测回填；期望回答要点：判断该设备是否达到预警条件；未触发时明确说明未达到。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00213807`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：设备预警判断必须先取最新记录再跑规则
- `备注`：补充第二设备预警判断。

### WA-09

- `一级分类`：G. 预警模板输出
- `二级分类`：地区模板
- `用户问题`：给如东县生成一条墒情预警
- `当前回答`：待实测回填；期望回答要点：按如东县事实与规则结果判断是否触发模板。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`county_name=如东县; city_name=南通市; need_template=true`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：地区对象也必须走规则判断后再决定模板输出
- `备注`：补充地区模板输出。

### WA-10

- `一级分类`：G. 预警模板输出
- `二级分类`：城市模板
- `用户问题`：按模板输出南京最新预警
- `当前回答`：待实测回填；期望回答要点：按南京市最新事实判断是否触发模板。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`city_name=南京市; need_template=true; time=最新业务时间`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：城市模板输出也应先规则判断
- `备注`：补充城市模板输出。

### WA-11

- `一级分类`：G. 预警模板输出
- `二级分类`：设备重旱模板
- `用户问题`：如果 SNS00204333 触发重旱，按模板给我一条
- `当前回答`：待实测回填；期望回答要点：判断是否达到重旱预警；触发才输出模板。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00204333; need_template=true; status_target=heavy_drought`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：异常类型与设备对象都要落到规则判断
- `备注`：补充设备+异常类型模板。

### WA-12

- `一级分类`：G. 预警模板输出
- `二级分类`：纯正文设备模板
- `用户问题`：只输出 SNS00213807 的预警正文
- `当前回答`：待实测回填；期望回答要点：如触发则仅输出模板正文；未触发则说明未达到条件。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00213807; render_mode=strict`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：strict_mode下模板正文不得被自由改写
- `备注`：补充设备纯正文模板。

### WA-13

- `一级分类`：G. 预警模板输出
- `二级分类`：城市预警判断
- `用户问题`：南通市需要发墒情预警吗
- `当前回答`：待实测回填；期望回答要点：按南通市事实判断是否触发预警。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`city_name=南通市`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：城市级预警判断不能跳过规则
- `备注`：补充城市预警判断。

### WA-14

- `一级分类`：G. 预警模板输出
- `二级分类`：正式口径城市模板
- `用户问题`：给镇江市按正式口径出一条预警
- `当前回答`：待实测回填；期望回答要点：若触发则按正式模板输出；未触发则说明未达到条件。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`city_name=镇江市; render_mode=strict`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：正式口径应保持模板约束
- `备注`：补充正式口径城市模板。

### WA-15

- `一级分类`：G. 预警模板输出
- `二级分类`：未触发直接说明
- `用户问题`：SNS00204333 如果没触发就直接说明
- `当前回答`：待实测回填；期望回答要点：未触发时明确说明未达到条件，不输出正式模板。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`device_sn=SNS00204333; no_template_if_not_triggered=true`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：未触发时内部应为not_triggered/none
- `备注`：补充未触发说明边界。

### WA-16

- `一级分类`：G. 预警模板输出
- `二级分类`：模板+解释地区
- `用户问题`：输出如东县最新预警并解释原因
- `当前回答`：待实测回填；期望回答要点：模板正文与解释分区输出，围绕如东县最新事实。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_warning_generation`
- `预期 slots`：`county_name=如东县; city_name=南通市; render_mode=plus_explanation`
- `预期 query_type / SQL`：`latest_record / SQL-05`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_warning_answer`
- `规则触发`：`yes/no`
- `是否写查询日志`：是
- `关键断言`：模板正文与解释必须分区，不揉成一段
- `备注`：补充地区模板+解释。


## H. 指标解释 / 指导建议

### AD-01

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：指标解释
- `用户问题`：83.18 是什么意思
- `当前回答`：当前最新记录为 2026-04-13 23:59:17，20cm 相对含水量 73.71%，规则判断为 未达到预警条件。 建议先结合地块实况核查墒情，偏旱时优先小水慢灌，偏湿时及时排水降渍。 以上建议仅作管理参考，实际措施还需结合土壤、作物和天气情况综合判断。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：上一轮已有设备详情
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_metric_explanation`
- `预期 slots`：`metric=water20cm`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：先给数据事实，再解释指标含义
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AD-02

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：农户建议
- `用户问题`：这种情况农户要注意什么
- `当前回答`：当前最新记录为 2026-04-13 23:59:17，20cm 相对含水量 73.71%，规则判断为 未达到预警条件。 建议先结合地块实况核查墒情，偏旱时优先小水慢灌，偏湿时及时排水降渍。 以上建议仅作管理参考，实际措施还需结合土壤、作物和天气情况综合判断。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：上一轮已有异常结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=farmer`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：建议必须带不确定性说明
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AD-03

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：大棚建议
- `用户问题`：这种情况大棚怎么处理
- `当前回答`：当前最新记录为 2026-04-13 23:59:17，20cm 相对含水量 94.64%，规则判断为 未达到预警条件。 建议优先检查棚内通风与排灌条件，避免长时间积水或局部失墒。 以上建议仅作管理参考，实际措施还需结合土壤、作物和天气情况综合判断。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：上一轮已有异常结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=greenhouse`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：输出对象应切换为设施大棚主体
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### AD-04

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：重旱处置建议
- `用户问题`：重旱情况下农户该怎么处理
- `当前回答`：待实测回填；期望回答要点：给出保守、可执行的农户侧处置建议，并说明需结合当地农技人员判断。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`status_target=heavy_drought; audience=farmer`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：否
- `关键断言`：通用建议不能编造当前监测事实；必须带不确定性说明
- `备注`：补充无上下文通用建议。

### AD-05

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：站所建议
- `用户问题`：给站所一段处置建议
- `当前回答`：待实测回填；期望回答要点：面向农业站所给出巡查、复核、通知和持续监测建议，不冒充正式预警。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=station`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：否
- `关键断言`：建议类回答不能替代正式预警发布；语气应面向站所
- `备注`：补充不同受众建议。

### AD-06

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：指标解释/20cm
- `用户问题`：20cm 相对含水量是什么意思
- `当前回答`：待实测回填；期望回答要点：解释20cm指标含义，并保持保守表达。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_metric_explanation`
- `预期 slots`：`metric=water20cm`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：否
- `关键断言`：指标解释可不查库，但不能编造当前数值
- `备注`：补充通用指标解释。

### AD-07

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：指标偏低解释
- `用户问题`：这个指标偏低说明什么
- `当前回答`：待实测回填；期望回答要点：解释指标偏低的常见业务含义和注意事项。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已有指标或详情结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_metric_explanation`
- `预期 slots`：无
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：先基于已有事实，再做指标解释
- `备注`：补充低值解释。

### AD-08

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：站所建议
- `用户问题`：这种情况站里要怎么跟进
- `当前回答`：待实测回填；期望回答要点：给站所侧巡查、复核、通知和持续监测建议。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已有异常或详情结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=station`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：建议对象应切换到站所角色
- `备注`：补充管理主体差异。

### AD-09

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：农户灌溉建议
- `用户问题`：农户现在要不要浇水
- `当前回答`：待实测回填；期望回答要点：给出保守建议，并提醒结合现场情况判断。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已有地区或设备详情
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=farmer`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：建议不能装成强结论命令
- `备注`：补充农户灌溉建议。

### AD-10

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：大棚紧急建议
- `用户问题`：大棚里需要马上处理吗
- `当前回答`：待实测回填；期望回答要点：按设施场景给出保守处理建议。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已有异常或详情结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：`audience=greenhouse`
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：对象为大棚主体，不应沿用农户话术
- `备注`：补充设施场景建议。

### AD-11

- `一级分类`：H. 指标解释 / 指导建议
- `二级分类`：一句话建议
- `用户问题`：给我一句保守建议
- `当前回答`：待实测回填；期望回答要点：给出一句谨慎、可执行、不夸张的建议。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：上一轮已有异常或详情结果
- `预期 input_type`：`business_colloquial`
- `预期 intent`：`soil_management_advice`
- `预期 slots`：无
- `预期 query_type / SQL`：`latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_advice_answer`
- `规则触发`：`no`
- `是否写查询日志`：是
- `关键断言`：简短建议也要带不确定性边界
- `备注`：补充一句话建议场景。


## I. 无数据 / 找不到 / 兜底

### FB-01

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：无效地区兜底
- `用户问题`：XX乡镇最近怎么样
- `当前回答`：没有找到 XX乡镇 的有效墒情数据，请核对名称或设备编号后重试。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`town_name=XX乡镇`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：地区不存在时不能编结果，要提示核对名称
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### FB-02

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：指定日期无数据
- `用户问题`：如东县 2026-04-15 有数据吗
- `当前回答`：如东县 在当前查询范围内暂无可用数据。当前库内最新业务时间截至 2026-04-13 23:59:17，请核对名称、时间范围或导入最新数据后再试。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=如东县; time=2026-04-15`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：指定日期无数据时，要提示库内最新业务时间
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### FB-03

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：时间窗内无设备
- `用户问题`：SNS00299999 最近7天有没有数据
- `当前回答`：没有找到 SNS00299999 的有效墒情数据，请核对名称或设备编号后重试。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00299999; time_range=last_7_days`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：设备不存在或明确时间窗内无数据时，不得回答“正常”
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### FB-04

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：不存在地区
- `用户问题`：不存在区最近墒情怎么样
- `当前回答`：待实测回填；期望回答要点：说明未找到该地区数据，建议核对地区名称或提供上级地区。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=不存在区`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：地区不存在时不能编结果，不能默认查全省
- `备注`：补充不存在地区兜底。

### FB-05

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：设备号格式异常
- `用户问题`：SNSABC 最近有没有数据
- `当前回答`：待实测回填；期望回答要点：提示设备号格式或设备信息可能不完整，建议核对完整设备 SN。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNSABC`
- `预期 query_type / SQL`：无
- `ExecutionGate`：`clarify`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：设备号明显不完整时优先提示核对，不直接查库扫描
- `备注`：补充设备号格式异常兜底。

### FB-06

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：指定日期无数据补充
- `用户问题`：南京市 2025-01-01 有数据吗
- `当前回答`：待实测回填；期望回答要点：如无数据，提示该日期暂无数据，并可提示最新业务时间。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南京市; time=2025-01-01`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：指定日期无数据时不得编造成正常结论
- `备注`：补充城市指定日期无数据。

### FB-07

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：时间窗内城市数据检查
- `用户问题`：南京最近7天有数据吗
- `当前回答`：南京市 最新监测时间为 2026-04-13 23:59:17，位于 南京市高淳区，20cm 相对含水量 130.51%，规则判断为 未达到预警条件。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`city_name=南京市; time_range=last_7_days`
- `预期 query_type / SQL`：`region_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：按明确时间窗查询，不使用导入批次语义
- `备注`：补充时间窗内城市数据检查。

### FB-08

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：不存在设备
- `用户问题`：SNS00000000 最近有没有异常
- `当前回答`：待实测回填；期望回答要点：提示设备不存在或无数据，不得回答正常。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00000000; time=最近`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：设备不存在时不能回答“未见异常”
- `备注`：补充不存在设备。

### FB-09

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：未来日期无数据
- `用户问题`：如东县 2030-01-01 最近怎么样
- `当前回答`：待实测回填；期望回答要点：指出日期超出数据范围或无数据，并提示核对时间。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=如东县; city_name=南通市; time=2030-01-01`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：未来日期不得默认回落到最新数据
- `备注`：补充未来日期无数据。

### FB-10

- `一级分类`：I. 无数据 / 找不到 / 兜底
- `二级分类`：未知地区异常
- `用户问题`：某某区最近异常如何
- `当前回答`：待实测回填；期望回答要点：提示未找到地区，建议核对行政区名称。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`business_direct`
- `预期 intent`：`soil_region_query`
- `预期 slots`：`county_name=某某区; time=最近`
- `预期 query_type / SQL`：`fallback / SQL-07`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`fallback_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：是
- `关键断言`：未知地区时不得扩展成模糊全省异常分析
- `备注`：补充未知地区异常问法。


## J. 能力边界

### BO-01

- `一级分类`：J. 能力边界
- `二级分类`：边界/天气
- `用户问题`：查一下明天天气
- `当前回答`：我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议，暂不处理天气、诗歌或股票类问题。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `预期 intent`：`out_of_scope`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`boundary_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：明确只支持墒情业务，不查天气
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### BO-02

- `一级分类`：J. 能力边界
- `二级分类`：边界/写诗
- `用户问题`：帮我写首诗
- `当前回答`：我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议，暂不处理天气、诗歌或股票类问题。
- `样本状态`：已实测（2026-04-22 商务评审版来源）
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `预期 intent`：`out_of_scope`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`boundary_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不转成闲聊，不误走业务链路
- `备注`：当前为正式维护 Case；如需修订，请同步更新对应回答样例与结构化期望。

### BO-03

- `一级分类`：J. 能力边界
- `二级分类`：边界/产量预测
- `用户问题`：帮我预测明年水稻产量
- `当前回答`：待实测回填；期望回答要点：说明当前只支持墒情查询、异常分析和预警模板，不支持产量预测。
- `样本状态`：补充待实测（2026-04-22 新增）
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `预期 intent`：`out_of_scope`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`boundary_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不扩展到产量预测；回到当前墒情能力边界
- `备注`：补充农业相关但超出墒情域的问题。

### BO-04

- `一级分类`：J. 能力边界
- `二级分类`：边界/虫害
- `用户问题`：查一下虫害情况
- `当前回答`：待实测回填；期望回答要点：说明当前只支持墒情业务，不处理虫害查询。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `预期 intent`：`out_of_scope`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`boundary_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不扩展到虫害业务
- `备注`：补充相邻农业域边界。

### BO-05

- `一级分类`：J. 能力边界
- `二级分类`：边界/降雨预测
- `用户问题`：预测下个月降雨
- `当前回答`：待实测回填；期望回答要点：说明当前不支持天气或降雨预测。
- `样本状态`：补充待实测（2026-04-22 扩充）
- `上下文`：无
- `预期 input_type`：`out_of_domain`
- `预期 intent`：`out_of_scope`
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：`pass`
- `预期 answer_type`：`boundary_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：不扩展到气候预测
- `备注`：补充预测类边界。

### MT-01

- `一级分类`：K. 多轮话题边界
- `二级分类`：结束语/清空上下文
- `用户问题`：如东县最近怎么样 -> 谢谢
- `当前回答`：待实测回填；期望第二轮返回简短结束语。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：第一轮已保存 `county_name=如东县` 的业务上下文
- `预期 input_type`：第二轮 `conversation_closing`
- `预期 intent`：无业务 intent
- `预期 slots`：无
- `预期 query_type / SQL`：无
- `ExecutionGate`：不进入
- `预期 answer_type`：`closing_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：纯结束语命中 `closing_end`，后端立即清空该 `session_id` 上下文
- `备注`：前端仍保留同一 `thread_id`，但后端不再继承旧对象。

### MT-02

- `一级分类`：K. 多轮话题边界
- `二级分类`：结束后追问/不继承
- `用户问题`：如东县最近怎么样 -> 谢谢 -> 那上周的呢
- `当前回答`：待实测回填；期望第三轮提示补充地区或设备。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：第二轮已清空上下文
- `预期 input_type`：第三轮 `business_colloquial`
- `预期 intent`：`clarification_needed`
- `预期 slots`：`follow_up=true; time=上周`
- `预期 query_type / SQL`：无
- `ExecutionGate`：不进入
- `预期 answer_type`：`clarification_answer`
- `规则触发`：`n/a`
- `是否写查询日志`：否
- `关键断言`：结束后同线程继续追问也不能继承如东县
- `备注`：覆盖“结束即清空上下文”。

### MT-03

- `一级分类`：K. 多轮话题边界
- `二级分类`：非纯结束语/继续业务
- `用户问题`：谢谢，南京呢？
- `当前回答`：待实测回填；期望按南京业务问题处理。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：可有可无
- `预期 input_type`：`business_colloquial` 或 `business_direct`
- `预期 intent`：按上下文框架或独立南京查询解析
- `预期 slots`：`city_name=南京市`
- `预期 query_type / SQL`：视上下文而定；不得因“谢谢”直接结束
- `ExecutionGate`：按业务请求判断
- `预期 answer_type`：不得为 `closing_answer`
- `规则触发`：按业务请求判断
- `是否写查询日志`：若查库则是
- `关键断言`：结束词旁边有地区业务信号时，不触发 `closing_end`
- `备注`：纯结束检测不能做简单关键词匹配。

### MT-04

- `一级分类`：K. 多轮话题边界
- `二级分类`：对象切换/继承异常框架
- `用户问题`：南京最近30天异常概况 -> 徐州呢？
- `当前回答`：待实测回填；期望第二轮输出徐州异常概况。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：上一轮 `city_name=南京市; query_family=anomaly; start_time/end_time=最近30天`
- `预期 input_type`：第二轮 `business_colloquial` 或 `business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=徐州市; time=继承上一轮绝对 start_time/end_time`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：异常规则
- `是否写查询日志`：是
- `关键断言`：显式地区覆盖历史地区，查询框架和时间窗继承；`inheritance_mode=carry_frame`
- `备注`：避免把“徐州呢？”误判为全新无时间问题。

### MT-05

- `一级分类`：K. 多轮话题边界
- `二级分类`：多槽位覆盖/继承框架
- `用户问题`：南京最近30天异常概况 -> 盐城昨天20cm呢？
- `当前回答`：待实测回填；期望第二轮按盐城、昨天、20cm 输出异常相关结果。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：上一轮 `query_family=anomaly`
- `预期 input_type`：`business_colloquial` 或 `business_direct`
- `预期 intent`：`soil_anomaly_query`
- `预期 slots`：`city_name=盐城市; time=昨天; metric=water20cm`
- `预期 query_type / SQL`：`anomaly_list / SQL-04`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_anomaly_answer`
- `规则触发`：异常规则
- `是否写查询日志`：是
- `关键断言`：地区、时间、指标同时覆盖；未显式改变的异常框架继续继承
- `备注`：覆盖多显式槽位覆盖历史槽位。

### MT-06

- `一级分类`：K. 多轮话题边界
- `二级分类`：排名转对象详情
- `用户问题`：哪个县最严重 -> SNS00204333呢？
- `当前回答`：待实测回填；期望第二轮输出设备详情，而不是继续排名。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：上一轮 `query_family=ranking`
- `预期 input_type`：`business_colloquial` 或 `business_direct`
- `预期 intent`：`soil_device_query`
- `预期 slots`：`device_sn=SNS00204333; time=继承上一轮时间窗`
- `预期 query_type / SQL`：`device_detail / SQL-03`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_detail_answer`
- `规则触发`：详情规则
- `是否写查询日志`：是
- `关键断言`：`inheritance_mode=convert_frame`，从 ranking 转成设备详情
- `备注`：排名框架不适合直接延续到单设备。

### MT-07

- `一级分类`：K. 多轮话题边界
- `二级分类`：建议 overlay 不粘连
- `用户问题`：最近有没有异常 -> 这种情况农户要注意什么 -> 徐州呢？
- `当前回答`：待实测回填；期望第三轮回到异常/详情类数据框架，而不是继续输出农户建议。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：第一轮 `base_query_family=anomaly`，第二轮 `answer_type=soil_advice_answer`
- `预期 input_type`：第三轮 `business_colloquial` 或 `business_direct`
- `预期 intent`：`soil_anomaly_query` 或最近兼容的数据查询 intent
- `预期 slots`：`city_name=徐州市; time=继承可用窗口`
- `预期 query_type / SQL`：不得固定为 advice 的 `latest_record / SQL-06`
- `ExecutionGate`：`pass`
- `预期 answer_type`：不得继续为 `soil_advice_answer`
- `规则触发`：按数据查询框架判断
- `是否写查询日志`：是
- `关键断言`：`warning/advice` 是输出层 overlay，不作为下一轮默认框架
- `备注`：覆盖“建议后对象切换”。

### MT-08

- `一级分类`：K. 多轮话题边界
- `二级分类`：省略追问/继承当前对象
- `用户问题`：如东县最近怎么样 -> 那个情况呢
- `当前回答`：待实测回填；期望第二轮继承如东县，而不是 InputGuard 直接澄清。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：上一轮 `county_name=如东县`
- `预期 input_type`：第二轮 `business_colloquial`
- `预期 intent`：继承上一轮兼容 intent
- `预期 slots`：`county_name=继承如东县`
- `预期 query_type / SQL`：按继承框架查询
- `ExecutionGate`：`pass`
- `预期 answer_type`：不得因 `InputGuard` 提前变成 `clarification_answer`
- `规则触发`：按继承框架判断
- `是否写查询日志`：是
- `关键断言`：`那个情况呢` 这类上下文依赖短句必须进入 `ConversationBoundary`
- `备注`：无上下文时仍应澄清。

### MT-09

- `一级分类`：K. 多轮话题边界
- `二级分类`：完整新问题/重置框架
- `用户问题`：如东县最近怎么样 -> 南京最近15天墒情怎么样
- `当前回答`：待实测回填；期望第二轮作为完整新问题处理。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：上一轮 `county_name=如东县`
- `预期 input_type`：第二轮 `business_direct`
- `预期 intent`：`soil_recent_summary`
- `预期 slots`：`city_name=南京市; time=最近15天`
- `预期 query_type / SQL`：`recent_summary / SQL-01`
- `ExecutionGate`：`pass`
- `预期 answer_type`：`soil_summary_answer`
- `规则触发`：概览统计
- `是否写查询日志`：是
- `关键断言`：当前轮信息完整时 `inheritance_mode=reset_frame`，不继承如东县
- `备注`：避免过度继承。

### MT-10

- `一级分类`：K. 多轮话题边界
- `二级分类`：衰减对照/显式新对象不阻断
- `用户问题`：如东县最近怎么样 -> 最近墒情怎么样 -> 哪个市最严重 -> 最近有没有异常 -> 生成一条墒情预警 -> 南京呢？
- `当前回答`：待实测回填；期望最后一轮能按南京显式对象处理，不因旧上下文衰减而直接拒绝。
- `样本状态`：补充待实测（2026-04-23 多轮边界增强）
- `上下文`：距离上次明确如东县对象已 4~5 轮，但当前轮显式给出南京
- `预期 input_type`：最后一轮 `business_colloquial` 或 `business_direct`
- `预期 intent`：按最近可兼容数据框架处理
- `预期 slots`：`city_name=南京市`
- `预期 query_type / SQL`：若框架可兼容则查库
- `ExecutionGate`：按业务请求判断
- `预期 answer_type`：不得仅因衰减返回 `clarification_answer`
- `规则触发`：按业务请求判断
- `是否写查询日志`：若查库则是
- `关键断言`：上下文衰减只阻断纯省略追问；显式新对象不受衰减阻断
- `备注`：与“有没有问题”这类纯省略衰减澄清形成对照。
