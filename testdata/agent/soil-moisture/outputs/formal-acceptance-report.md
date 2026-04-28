# 墒情 Agent 30 条正式验收测试报告

## 1. 测试概览
- 测试时间：2026-04-28 04:00:26 
- 分支：`main`
- 提交号：`ec7427a930790107f3708083753ea8348c3b4cfb`
- 执行环境：仓库 `/Users/mac/Desktop/gago-cloud/code/smart-agriculture`；在线 Agent `http://localhost:18010/chat`；MySQL `127.0.0.1:3306/smart_agriculture`
- 正式 case 总数：`30`
- 总体通过率：`16.67%`（5/30）
- 说明：`guidance_answer` 与内部守卫类 case 使用仓库当前代码做受控执行；业务查询类 case 使用本地在线 Agent HTTP 服务，并通过 `agent_query_log` 与数据库回查补齐证据链。

## 2. 正式库自检结果
- 数量检查：`30` 条。
- 分布 `guidance_answer`：期望 `8`，实际 `8`。
- 分布 `soil_summary_answer`：期望 `6`，实际 `6`。
- 分布 `soil_ranking_answer`：期望 `4`，实际 `4`。
- 分布 `soil_detail_answer`：期望 `8`，实际 `8`。
- 分布 `fallback_answer`：期望 `4`，实际 `4`。
- 字段完整性：缺字段 case 数量 `0`。
- 是否符合正式入口要求：`是`。

## 3. 基础测试结果
### Python 测试结果
- 执行命令：`PYTHONPATH=. pytest tests -q`
- 工作目录：`/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent`
- 退出码：`2`
- 标准输出：
```text
==================================== ERRORS ====================================
______________ ERROR collecting tests/test_agent_api_unittest.py _______________
ImportError while importing test module '/Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent/tests/test_agent_api_unittest.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/Users/mac/.pyenv/versions/3.11.10/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_agent_api_unittest.py:5: in <module>
    from fastapi import HTTPException
E   ModuleNotFoundError: No module named 'fastapi'
=========================== short test summary info ============================
ERROR tests/test_agent_api_unittest.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.10s
```

### Node 测试结果
- 执行命令：`node --test apps/web/tests/agent-chat-evidence.test.mjs apps/web/tests/file-contract.test.mjs apps/web/tests/db-schema-contract.test.mjs`
- 工作目录：`/Users/mac/Desktop/gago-cloud/code/smart-agriculture`
- 退出码：`0`
- 标准输出：
```text
✔ analysis context derives region from answer_facts entity_name (0.867334ms)
✔ analysis context falls back to first tool args when facts lack entity_name (0.065541ms)
✔ analysis context stays blank when no region can be derived (0.052708ms)
✔ analysis context handles device queries without region level (0.050125ms)
✔ mysql core tables strictly follow current soil domain contract (0.483791ms)
✔ fact_soil_moisture columns exactly match raw excel contract (0.672917ms)
✔ soil import preview tables keep current job and diff fields (0.489334ms)
✔ region_alias only keeps city and county disambiguation fields (0.156084ms)
✔ warning_template and agent_query_log retain current runtime fields (0.162375ms)
✔ web has route files for chat admin and query logs (0.4385ms)
✔ workspace app uses route state instead of local workspaceView state (0.294708ms)
✔ workspace app redirects authenticated root users to chat (0.074375ms)
✔ workspace app keeps route permission boundaries in one place (0.067917ms)
✔ workspace app renders neutral loading while redirecting guarded routes (0.071625ms)
✔ agent chat route proxies to configured AGENT_BASE_URL (0.352ms)
✔ admin routes for records upload and rules exist (0.122334ms)
✔ workspace routes for auth and chat exist (0.089167ms)
✔ developer workspace can view agent query logs without soil admin access (0.40075ms)
✔ workspace no longer renders the right-side evidence analysis panel (0.114334ms)
✔ workspace header uses a dedicated user menu instead of nav buttons row (0.818ms)
✔ workspace user menu contains route items username and logout entry (0.114791ms)
✔ workspace user menu avoids misleading menu roles and guards current route push (0.06375ms)
✔ globals include workspace dropdown menu styles (0.459417ms)
✔ workspace user menu uses final dropdown class names (0.065333ms)
✔ chat panel no longer renders AI involvement badge in message list (0.192875ms)
✔ developer log filters use selects and keep the table focused on rows (0.247792ms)
✔ query log repository pages ids before loading wide log fields (0.347458ms)
✔ query log page loads wide SQL and result payloads on demand (0.220625ms)
✔ database query log docs include request and routing context fields (0.322166ms)
✔ region alias and acceptance docs live in dedicated non-plan directories (0.460167ms)
✔ system design doc reflects current region alias implementation (0.174292ms)
✔ soil moisture testing docs use testdata case library as the single formal case source (0.75675ms)
✔ agent summary route must surface upstream errors instead of fake fallback data (0.22075ms)
✔ web start script prepares standalone static assets (0.179375ms)
✔ web docker image binds standalone server to all interfaces for healthcheck (0.145084ms)
✔ docker compose uses container network addresses for runtime dependencies (0.226833ms)
ℹ tests 36
ℹ suites 0
ℹ pass 36
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 42.813167
```

## 4. 30 条 case 逐条结果
### SM-CONV-001
- 用户问题：你好
- 上下文：无
- 预期契约：
  - 预期 input_type：`greeting`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`safe_hint`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`greeting`
  - 实际 Tool：`无`
  - 实际 answer_type：`guidance_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`safe_hint`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：你好，我可以帮助查询土壤墒情、分析异常、生成预警模板，并提供保守的管理建议。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：你好，我可以帮你查询墒情概览、风险排名，以及地区或设备的详细情况。你可以直接问“最近 7 天整体墒情怎么样”“南通市当前情况如何”或“SNS00204333 最近有没有异常”。
- 实际回答：你好，我可以帮助查询土壤墒情、分析异常、生成预警模板，并提供保守的管理建议。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`是`
  - 是否符合事实：`是`
  - 失败原因：`无`
  - 修复建议：`保持当前实现或仅做表达优化`
- 备注：基础问候样例

### SM-CONV-002
- 用户问题：你能做什么
- 上下文：无
- 预期契约：
  - 预期 input_type：`capability_question`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`safe_hint`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`capability_question`
  - 实际 Tool：`无`
  - 实际 answer_type：`guidance_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`safe_hint`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：我当前支持墒情概览、地区/设备详情、异常分析、预警判断和模板输出。你可以直接给地区、设备或时间范围来问。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：我主要处理土壤墒情相关问题，可以查整体概况、看风险排名、查某个地区或某台设备的详情，也能在回答里突出异常、预警或建议视角。你只要把地区、设备或时间范围说清楚，我就能给出基于真实数据的结果。
- 实际回答：我当前支持墒情概览、地区/设备详情、异常分析、预警判断和模板输出。你可以直接给地区、设备或时间范围来问。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`是`
  - 是否符合事实：`是`
  - 失败原因：`无`
  - 修复建议：`保持当前实现或仅做表达优化`
- 备注：能力说明样例

### SM-CONV-003
- 用户问题：帮我看一下
- 上下文：无
- 预期契约：
  - 预期 input_type：`ambiguous_low_confidence`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`clarification`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`ambiguous_low_confidence`
  - 实际 Tool：`无`
  - 实际 answer_type：`guidance_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`clarification`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：可以，我先帮你定位问题类型。请补充地区、设备或时间范围，例如：“南通市最近 7 天墒情怎么样”“SNS00204333 最近有没有异常”或“过去 30 天哪些县区最严重”。
- 实际回答：你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`是`
  - 是否符合事实：`是`
  - 失败原因：`无`
  - 修复建议：`保持当前实现或仅做表达优化`
- 备注：直接澄清样例

### SM-CONV-004
- 用户问题：那个情况呢
- 上下文：上一轮没有形成有效业务对象，不能安全继承
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`clarification`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_colloquial`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`tool_missing`
  - 实际 final_answer：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：我还缺少这轮要查询的明确对象。请直接告诉我地区、设备或时间范围，例如：“如东县最近怎么样”“SNS00204333 昨天有没有异常”或“南通市当前最新一期概况如何”。
- 实际回答：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 clarification，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。`
  - 修复建议：`按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason`
- 备注：缺上下文的短口语澄清样例

### SM-CONV-005
- 用户问题：帮我查一下明天天气
- 上下文：无
- 预期契约：
  - 预期 input_type：`out_of_domain`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`boundary`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`out_of_domain`
  - 实际 Tool：`无`
  - 实际 answer_type：`guidance_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`boundary`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议，暂不处理天气、诗歌或股票类问题。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：我当前只处理墒情数据相关问题，不提供天气查询。你可以改问“最近 7 天墒情怎么样”“哪个县区最需要关注”或“某台设备最近有没有异常”。
- 实际回答：我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议，暂不处理天气、诗歌或股票类问题。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`是`
  - 是否符合事实：`是`
  - 失败原因：`无`
  - 修复建议：`保持当前实现或仅做表达优化`
- 备注：能力边界样例

### SM-CONV-006
- 用户问题：帮我写一首诗
- 上下文：无
- 预期契约：
  - 预期 input_type：`out_of_domain`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`boundary`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`tool_missing`
  - 实际 final_answer：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：这个请求超出了我当前的墒情业务范围。我更适合回答土壤墒情概况、风险排名、地区或设备详情，以及异常和预警相关问题。
- 实际回答：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 boundary，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。`
  - 修复建议：`按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason`
- 备注：创作型越界样例

### SM-CONV-007
- 用户问题：谢谢
- 上下文：无
- 预期契约：
  - 预期 input_type：`conversation_closing`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`closing`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`conversation_closing`
  - 实际 Tool：`无`
  - 实际 answer_type：`guidance_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`closing`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：好的，这个话题先结束。有需要时你再继续问我即可。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：不客气。如果你后面还想看某个地区、设备或时间段的墒情情况，直接继续问我就可以。
- 实际回答：好的，这个话题先结束。有需要时你再继续问我即可。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`是`
  - 是否符合事实：`是`
  - 失败原因：`无`
  - 修复建议：`保持当前实现或仅做表达优化`
- 备注：结束语样例

### SM-CONV-008
- 用户问题：好的，先这样
- 上下文：上一轮刚完成一次业务查询
- 预期契约：
  - 预期 input_type：`conversation_closing`
  - 预期 Tool：`无`
  - 预期 answer_type：`guidance_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`closing`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`tool_missing`
  - 实际 final_answer：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 执行方式：`controlled-current-code-guidance`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：好的，这一轮先到这里。后面如果你想继续看南通市、如东县或某台设备的最新数据，直接在当前线程继续问就行。
- 实际回答：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：不适用（非业务，不查库）
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`无`
  - 禁止事实：`无`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 closing，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。`
  - 修复建议：`按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason`
- 备注：带上下文的结束语样例

### SM-SUM-001
- 用户问题：最近 7 天整体墒情怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近7天的土壤墒情整体情况如下：

- 总记录数：3,689 条
- 平均20厘米土层含水量：93.77%
- 状态分布：
  - 未触发预警：3,645 次
  - 渍涝：35 次
  - 重度干旱：8 次
  - 设备故障：1 次
- 预警总数：44 次
- 需重点关注地区（按预警次数降序）：
  1. 睢宁县：9 次
  2. 沛县：8 次
  3. 昆山市：7 次
  4. 淮安区：5 次
  5. 溧阳市：3 次

总体来看，大部分地区的土壤墒情处于正常范围，但有少数地区出现了渍涝和重度干旱的情况。建议对上述预警次数较多的地区加强监测和管理。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`3689`
  - 关键字段：`{"total_records": 3689, "avg_water20cm": 93.77, "alert_count": 44, "top_alert_regions": [{"region": "睢宁县", "alert_count": 9}, {"region": "沛县", "alert_count": 8}, {"region": "昆山市", "alert_count": 7}, {"region": "淮安区", "alert_count": 5}, {"region": "溧阳市", "alert_count": 3}]}`
  - 关键记录样本：`[{"sn": "SNS00213421", "city": "南京市", "county": "栖霞区", "create_time": "2026-04-13 23:59:17", "water20cm": 78.7, "soil_status": null}, {"sn": "SNS00204614", "city": "常州市", "county": "溧阳市", "create_time": "2026-04-13 23:59:17", "water20cm": 95.04, "soil_status": null}, {"sn": "SNS00213465", "city": "宿迁市", "county": "宿豫区", "create_time": "2026-04-13 23:59:17", "water20cm": 111.02, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 3689, "avg_water20cm": 93.77, "alert_count": 44, "status_counts": {"not_triggered": 3645, "waterlogging": 35, "heavy_drought": 8, "device_fault": 1}, "top_alert_regions": [{"region": "睢宁县", "alert_count": 9}, {"region": "沛县", "alert_count": 8}, {"region": "昆山市", "alert_count": 7}, {"region": "淮安区", "alert_count": 5}, {"region": "溧阳市", "alert_count": 3}], "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "entity": "全局", "output_mode": "normal", "alert_records": [{"sn": "SNS00204885", "city": "苏州市", "county": "昆山市", "create_time": "2026-04-13 23:59:17", "water20cm": 151.71, "soil_status": "waterlogging"}, {"sn": "SNS00213276", "city": "徐州市", "county": "沛县", "create_time": "2026-04-13 23:59:17", "water20cm": 150.7, "soil_status": "waterlogging"}, {"sn": "SNS00204413", "city": "淮安市", "county": "淮安区", "create_time": "2026-04-13 23:59:17", "water20cm": 151.3, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 150.94, "soil_status": "waterlogging"}, {"sn": "SNS00204610", "city": "常州市", "county": "溧阳市", "create_time": "2026-04-13 23:59:17", "water20cm": 48.7, "soil_status": "heavy_drought"}]}`
- 当前回答（case 样例）：最近 7 天全省墒情整体平稳，20 厘米平均含水量约为 `93.77%`，共汇总 `3689` 条监测记录。预警相关记录共有 `44` 条，当前需要重点关注的区域主要是 `睢宁县`、`沛县` 和 `昆山市`，其中睢宁县最突出。整体仍以未触发预警为主，但局部存在涝渍点位，也有少量重旱和设备故障记录，建议优先复核上述高风险区域。
- 实际回答：最近7天的土壤墒情整体情况如下：

- 总记录数：3,689 条
- 平均20厘米土层含水量：93.77%
- 状态分布：
  - 未触发预警：3,645 次
  - 渍涝：35 次
  - 重度干旱：8 次
  - 设备故障：1 次
- 预警总数：44 次
- 需重点关注地区（按预警次数降序）：
  1. 睢宁县：9 次
  2. 沛县：8 次
  3. 昆山市：7 次
  4. 淮安区：5 次
  5. 溧阳市：3 次

总体来看，大部分地区的土壤墒情处于正常范围，但有少数地区出现了渍涝和重度干旱的情况。建议对上述预警次数较多的地区加强监测和管理。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=3689`、`avg_water20cm=93.77`、`alert_count=44`，Top3 关注区域依次包含 `睢宁县 / 沛县 / 昆山市`
  - 预期实体：`全局`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`3689 / 93.77 / 44`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``睢宁县`、`沛县`、`昆山市``
  - 禁止事实：``无数据`、`全部正常无需关注``
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：全局概览基准样例

### SM-SUM-002
- 用户问题：南通市最近 7 天墒情怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：南通市最近7天的土壤墒情概况如下：

- 总记录数：259条
- 平均20厘米土层含水量：95.39%
- 状态分布：全部为正常状态，没有触发预警

整体来看，南通市近一周内土壤墒情良好，未出现需要特别关注的情况。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`259`
  - 关键字段：`{"total_records": 259, "avg_water20cm": 95.39, "alert_count": 0, "top_alert_regions": []}`
  - 关键记录样本：`[{"sn": "SNS00205026", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 105.84, "soil_status": null}, {"sn": "SNS00205024", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 86.13, "soil_status": null}, {"sn": "SNS00214092", "city": "南通市", "county": "启东市", "create_time": "2026-04-13 23:59:17", "water20cm": 91.96, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 259, "avg_water20cm": 95.39, "alert_count": 0, "status_counts": {"not_triggered": 259}, "top_alert_regions": [], "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "entity": "南通市", "output_mode": "normal", "alert_records": []}`
- 当前回答（case 样例）：最近 7 天南通市整体比较平稳，共汇总 `259` 条记录，20 厘米平均含水量约 `95.39%`。这一时间窗内 `alert_count=0`，状态分布全部为 `not_triggered`，说明当前没有明显异常点位。可以把这次结果视为平稳运行状态，继续做日常巡检即可。
- 实际回答：南通市最近7天的土壤墒情概况如下：

- 总记录数：259条
- 平均20厘米土层含水量：95.39%
- 状态分布：全部为正常状态，没有触发预警

整体来看，南通市近一周内土壤墒情良好，未出现需要特别关注的情况。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=259`、`avg_water20cm=95.39`、`alert_count=0`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`259 / 95.39 / 0`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``南通市`、`259``
  - 禁止事实：`存在明显预警`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：地区概览正常样例

### SM-SUM-003
- 用户问题：现在南通市整体墒情怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：南通市最近7天的土壤墒情整体情况如下：

- 总记录数：259条
- 平均20厘米土层含水量：95.39%
- 各状态分布：
  - 未触发预警：259次
- 预警次数：0次

从数据来看，南通市近期没有出现土壤墒情预警的情况，整体状况良好。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-04-13 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`37`
  - 关键字段：`{"total_records": 37, "avg_water20cm": 96.21, "alert_count": 0, "top_alert_regions": []}`
  - 关键记录样本：`[{"sn": "SNS00213905", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 79.25, "soil_status": null}, {"sn": "SNS00213944", "city": "南通市", "county": "如皋市", "create_time": "2026-04-13 23:59:17", "water20cm": 95.37, "soil_status": null}, {"sn": "SNS00213857", "city": "南通市", "county": "如皋市", "create_time": "2026-04-13 23:59:17", "water20cm": 108.31, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 37, "avg_water20cm": 96.21, "alert_count": 0, "status_counts": {"not_triggered": 37}, "top_alert_regions": [], "time_window": {"start_time": "2026-04-13 00:00:00", "end_time": "2026-04-13 23:59:59"}, "entity": "南通市", "output_mode": "normal", "alert_records": []}`
- 当前回答（case 样例）：按当前库内最新业务时间来看，南通市最新一期（`2026-04-13`）共汇总 `37` 条记录，20 厘米平均含水量约 `96.21%`，全部为未触发预警状态，`alert_count=0`。也就是说，当前这一期数据没有发现需要立即升级处置的异常点位。
- 实际回答：南通市最近7天的土壤墒情整体情况如下：

- 总记录数：259条
- 平均20厘米土层含水量：95.39%
- 各状态分布：
  - 未触发预警：259次
- 预警次数：0次

从数据来看，南通市近期没有出现土壤墒情预警的情况，整体状况良好。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(city=南通市,start=2026-04-13 00:00:00,end=2026-04-13 23:59:59)`；应得到 `total_records=37`、`avg_water20cm=96.21`、`alert_count=0`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-04-13 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`37 / 96.21 / 0`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`2026-04-13`
  - 禁止事实：`系统当前时间`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。；实际回答缺少必含事实：2026-04-13。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：最新业务时间锚点样例

### SM-SUM-004
- 用户问题：睢宁县最近一个月有没有异常
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`anomaly_focus`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE county = '睢宁县' AND create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`210`
  - 关键字段：`{"total_records": 210, "avg_water20cm": 132.61, "alert_count": 39, "top_alert_regions": [{"region": "睢宁县", "alert_count": 39}]}`
  - 关键记录样本：`[{"sn": "SNS00213858", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 147.28, "soil_status": null}, {"sn": "SNS00204660", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 124.28, "soil_status": null}, {"sn": "SNS00213859", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 136.31, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 210, "avg_water20cm": 132.61, "alert_count": 39, "status_counts": {"not_triggered": 171, "waterlogging": 39}, "top_alert_regions": [{"region": "睢宁县", "alert_count": 39}], "time_window": {"start_time": "2026-03-15 00:00:00", "end_time": "2026-04-13 23:59:59"}, "entity": "睢宁县", "output_mode": "anomaly_focus", "alert_records": [{"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 150.94, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-12 23:59:17", "water20cm": 153.37, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-11 23:59:17", "water20cm": 155.81, "soil_status": "waterlogging"}, {"sn": "SNS00213858", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-10 23:59:17", "water20cm": 151.58, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-10 23:59:17", "water20cm": 157.65, "soil_status": "waterlogging"}]}`
- 当前回答（case 样例）：最近一个月睢宁县需要重点关注。该时间窗共汇总 `210` 条记录，20 厘米平均含水量约 `132.61%`，其中预警相关记录 `39` 条，异常主要集中在 `涝渍`。如果按异常视角看，睢宁县本轮就是本地最值得优先复核的对象，近几条代表性异常记录集中在设备 `SNS00213891`。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(county=睢宁县,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59,output_mode=anomaly_focus)`；应得到 `total_records=210`、`alert_count=39`，代表异常记录中包含 `SNS00213891`
  - 预期实体：`睢宁县`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`210 / 132.61 / 39`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``睢宁县`、`39`、`涝渍``
  - 禁止事实：`完全正常`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_summary_answer，实际 fallback_answer。；output_mode 不匹配：期望 anomaly_focus，实际 无/未返回。；实际回答缺少必含事实：睢宁县, 39, 涝渍。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：summary 异常视角样例

### SM-SUM-005
- 用户问题：从预警角度看，南通市今年情况怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`warning_mode`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-01-01 00:00:00' AND create_time <= '2026-12-31 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`3811`
  - 关键字段：`{"total_records": 3811, "avg_water20cm": 92.33, "alert_count": 20, "top_alert_regions": [{"region": "如东县", "alert_count": 14}, {"region": "启东市", "alert_count": 3}, {"region": "海门区", "alert_count": 2}, {"region": "如皋市", "alert_count": 1}]}`
  - 关键记录样本：`[{"sn": "SNS00205070", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 90.11, "soil_status": null}, {"sn": "SNS00213906", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 84.87, "soil_status": null}, {"sn": "SNS00213907", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 121.05, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 3811, "avg_water20cm": 92.33, "alert_count": 20, "status_counts": {"not_triggered": 3791, "waterlogging": 5, "device_fault": 1, "heavy_drought": 14}, "top_alert_regions": [{"region": "如东县", "alert_count": 14}, {"region": "启东市", "alert_count": 3}, {"region": "海门区", "alert_count": 2}, {"region": "如皋市", "alert_count": 1}], "time_window": {"start_time": "2026-01-01 00:00:00", "end_time": "2026-12-31 23:59:59"}, "entity": "南通市", "output_mode": "warning_mode", "alert_records": [{"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-05 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-04 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-03 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00211205", "city": "南通市", "county": "海门区", "create_time": "2026-03-03 23:59:17", "water20cm": 155.68, "soil_status": "waterlogging"}, {"sn": "SNS00211205", "city": "南通市", "county": "海门区", "create_time": "2026-03-02 23:59:17", "water20cm": 154.2, "soil_status": "waterlogging"}]}`
- 当前回答（case 样例）：从预警视角看，南通市今年共汇总 `3811` 条记录，预警相关记录 `20` 条，重点区域依次是 `如东县（14）`、`启东市（3）`、`海门区（2）` 和 `如皋市（1）`。代表性预警样例包括 `2026-03-05 23:59:17` 启东市设备 `SNS00214096` 的 `154.31%` 涝渍记录，以及如东县设备 `SNS00204334` 在一月中旬连续出现的重旱记录。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(city=南通市,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=warning_mode)`；应得到 `total_records=3811`、`alert_count=20`、Top4 重点区域为 `如东县 / 启东市 / 海门区 / 如皋市`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
  - 预期关键指标：`3811 / 20 / 如东县14`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``SNS00214096`、`154.31%``
  - 禁止事实：`全年没有任何预警`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_summary_answer，实际 fallback_answer。；output_mode 不匹配：期望 warning_mode，实际 无/未返回。；实际回答缺少必含事实：SNS00214096, 154.31%。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：summary 预警视角样例

### SM-SUM-006
- 用户问题：南通市近 7 天需要注意什么
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`query_soil_summary`
  - 预期 answer_type：`soil_summary_answer`
  - 预期 output_mode：`advice_mode`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`anomaly_focus`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：近7天内，南通市的土壤墒情整体情况良好，没有触发任何预警。平均20厘米土层含水量为95.39%，所有记录均处于正常状态。

因此，在这段时间内，南通市无需特别关注土壤墒情问题。继续保持监测即可。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_summary`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`259`
  - 关键字段：`{"total_records": 259, "avg_water20cm": 95.39, "alert_count": 0, "top_alert_regions": []}`
  - 关键记录样本：`[{"sn": "SNS00205026", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 105.84, "soil_status": null}, {"sn": "SNS00205024", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 86.13, "soil_status": null}, {"sn": "SNS00214092", "city": "南通市", "county": "启东市", "create_time": "2026-04-13 23:59:17", "water20cm": 91.96, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_summary", "total_records": 259, "avg_water20cm": 95.39, "alert_count": 0, "status_counts": {"not_triggered": 259}, "top_alert_regions": [], "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "entity": "南通市", "output_mode": "advice_mode", "alert_records": []}`
- 当前回答（case 样例）：从建议视角看，南通市近 7 天总体平稳，共有 `259` 条记录，20 厘米平均含水量约 `95.39%`，当前没有触发预警的点位。因为这段时间 `alert_count=0`，更适合维持日常巡检和例行监测，不需要额外升级处置，但仍建议按常规频率关注后续最新一期数据。
- 实际回答：近7天内，南通市的土壤墒情整体情况良好，没有触发任何预警。平均20厘米土层含水量为95.39%，所有记录均处于正常状态。

因此，在这段时间内，南通市无需特别关注土壤墒情问题。继续保持监测即可。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_summary(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59,output_mode=advice_mode)`；应得到 `total_records=259`、`avg_water20cm=95.39`、`alert_count=0`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`259 / 95.39 / 0`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`总体平稳`
  - 禁止事实：`建议立即发布预警`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_summary，实际 无。；output_mode 不匹配：期望 advice_mode，实际 anomaly_focus。；实际回答缺少必含事实：总体平稳。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：summary 建议视角样例

### SM-RANK-001
- 用户问题：最近 30 天县区里哪几个最严重
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_ranking`
  - 预期 answer_type：`soil_ranking_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_ranking_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近30天内，县区级土壤墒情最严重的前五名如下：

1. **睢宁县**（徐州市）
   - 平均20cm含水量：132.61%
   - 预警次数：39次
   
2. **昆山市**（苏州市）
   - 平均20cm含水量：113.89%
   - 预警次数：37次
   
3. **沛县**（徐州市）
   - 平均20cm含水量：112.62%
   - 预警次数：36次
   
4. **溧阳市**（常州市）
   - 平均20cm含水量：105.79%
   - 预警次数：23次
   
5. **清江浦区**（淮安市）
   - 平均20cm含水量：73.78%
   - 预警次数：13次

这些地区在最近一个月里表现出较高的土壤含水量或预警频率，需要特别关注。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_ranking`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`80` 个分组
  - 聚合结果 / 排名结果：`[{"name": "睢宁县", "record_count": 210, "avg_water20cm": 132.61, "alert_count": 39, "status_counts": {"not_triggered": 171, "waterlogging": 39}, "rank": 1}, {"name": "昆山市", "record_count": 210, "avg_water20cm": 113.89, "alert_count": 37, "status_counts": {"not_triggered": 173, "waterlogging": 37}, "rank": 2}, {"name": "沛县", "record_count": 240, "avg_water20cm": 112.62, "alert_count": 36, "status_counts": {"not_triggered": 204, "waterlogging": 36}, "rank": 3}, {"name": "溧阳市", "record_count": 150, "avg_water20cm": 105.79, "alert_count": 23, "status_counts": {"not_triggered": 127, "heavy_drought": 3, "waterlogging": 20}, "rank": 4}, {"name": "清江浦区", "record_count": 150, "avg_water20cm": 73.78, "alert_count": 13, "status_counts": {"not_triggered": 137, "heavy_drought": 2, "device_fault": 11}, "rank": 5}]`
- 当前回答（case 样例）：最近 30 天如果按县区风险排序，前 3 位分别是 `睢宁县`、`昆山市` 和 `沛县`。其中睢宁县共有 `39` 条预警相关记录，昆山市 `37` 条，沛县 `36` 条，三者都是当前最需要优先关注的县区。
- 实际回答：最近30天内，县区级土壤墒情最严重的前五名如下：

1. **睢宁县**（徐州市）
   - 平均20cm含水量：132.61%
   - 预警次数：39次
   
2. **昆山市**（苏州市）
   - 平均20cm含水量：113.89%
   - 预警次数：37次
   
3. **沛县**（徐州市）
   - 平均20cm含水量：112.62%
   - 预警次数：36次
   
4. **溧阳市**（常州市）
   - 平均20cm含水量：105.79%
   - 预警次数：23次
   
5. **清江浦区**（淮安市）
   - 平均20cm含水量：73.78%
   - 预警次数：13次

这些地区在最近一个月里表现出较高的土壤含水量或预警频率，需要特别关注。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_ranking(aggregation=county,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `睢宁县 / 昆山市 / 沛县`
  - 预期实体：`县区排行`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`睢宁县 > 昆山市 > 沛县`
  - 预期诊断类别：`未单列`
  - 必含事实：`39 / 37 / 36`
  - 禁止事实：`输出原始 records`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_ranking，实际 无。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：县区排行基准样例

### SM-RANK-002
- 用户问题：最近 30 天设备里前 5 个风险最高的是哪些
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_ranking`
  - 预期 answer_type：`soil_ranking_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_ranking_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近30天内，风险最高的前5个设备如下：

1. **设备编号：SNS00213276**
   - 所在地：徐州市, 沛县
   - 平均20cm土层含水量：150.70%
   - 预警次数：31次
   - 状态：全部为渍涝

2. **设备编号：SNS00204885**
   - 所在地：苏州市, 昆山市
   - 平均20cm土层含水量：153.19%
   - 预警次数：31次
   - 状态：全部为渍涝

3. **设备编号：SNS00213891**
   - 所在地：徐州市, 睢宁县
   - 平均20cm土层含水量：159.65%
   - 预警次数：27次
   - 状态：主要为渍涝（27次），有4次未触发预警

4. **设备编号：SNS00204413**
   - 所在地：淮安市, 淮安区
   - 平均20cm土层含水量：149.81%
   - 预警次数：13次
   - 状态：部分为渍涝（13次），其余时间未触发预警（18次）

5. **设备编号：SNS00204925**
   - 所在地：淮安市, 清江浦区
   - 平均20cm土层含水量：50.99%
   - 预警次数：12次
   - 状态：主要是设备故障（12次），其余时间未触发预警（19次）

这些设备中，前三个设备的平均含水量都超过了正常范围，并且大部分时间处于渍涝状态。第四个和第五个设备虽然也有一定的风险，但情况相对较好。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_ranking`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`527` 个分组
  - 聚合结果 / 排名结果：`[{"name": "SNS00213276", "record_count": 30, "avg_water20cm": 150.7, "alert_count": 30, "status_counts": {"waterlogging": 30}, "rank": 1}, {"name": "SNS00204885", "record_count": 30, "avg_water20cm": 153.26, "alert_count": 30, "status_counts": {"waterlogging": 30}, "rank": 2}, {"name": "SNS00213891", "record_count": 30, "avg_water20cm": 159.34, "alert_count": 26, "status_counts": {"waterlogging": 26, "not_triggered": 4}, "rank": 3}, {"name": "SNS00204612", "record_count": 30, "avg_water20cm": 145.85, "alert_count": 12, "status_counts": {"not_triggered": 18, "waterlogging": 12}, "rank": 4}, {"name": "SNS00204413", "record_count": 30, "avg_water20cm": 149.8, "alert_count": 12, "status_counts": {"waterlogging": 12, "not_triggered": 18}, "rank": 5}]`
- 当前回答（case 样例）：最近 30 天设备风险前列主要集中在 `SNS00213276`、`SNS00204885` 和 `SNS00213891`。其中 `SNS00213276` 与 `SNS00204885` 都是整段时间内持续 `waterlogging`，前者位于 `徐州市沛县`，后者位于 `苏州市昆山市`；`SNS00213891` 位于 `徐州市睢宁县`，同样属于需要优先复核的高风险设备。
- 实际回答：最近30天内，风险最高的前5个设备如下：

1. **设备编号：SNS00213276**
   - 所在地：徐州市, 沛县
   - 平均20cm土层含水量：150.70%
   - 预警次数：31次
   - 状态：全部为渍涝

2. **设备编号：SNS00204885**
   - 所在地：苏州市, 昆山市
   - 平均20cm土层含水量：153.19%
   - 预警次数：31次
   - 状态：全部为渍涝

3. **设备编号：SNS00213891**
   - 所在地：徐州市, 睢宁县
   - 平均20cm土层含水量：159.65%
   - 预警次数：27次
   - 状态：主要为渍涝（27次），有4次未触发预警

4. **设备编号：SNS00204413**
   - 所在地：淮安市, 淮安区
   - 平均20cm土层含水量：149.81%
   - 预警次数：13次
   - 状态：部分为渍涝（13次），其余时间未触发预警（18次）

5. **设备编号：SNS00204925**
   - 所在地：淮安市, 清江浦区
   - 平均20cm土层含水量：50.99%
   - 预警次数：12次
   - 状态：主要是设备故障（12次），其余时间未触发预警（19次）

这些设备中，前三个设备的平均含水量都超过了正常范围，并且大部分时间处于渍涝状态。第四个和第五个设备虽然也有一定的风险，但情况相对较好。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_ranking(aggregation=device,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `SNS00213276 / SNS00204885 / SNS00213891`
  - 预期实体：`设备排行`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`SNS00213276 > SNS00204885 > SNS00213891`
  - 预期诊断类别：`未单列`
  - 必含事实：``徐州市沛县`、`苏州市昆山市``
  - 禁止事实：`只给设备号不给地区`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_ranking，实际 无。；实际回答缺少必含事实：徐州市沛县, 苏州市昆山市。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：设备排行样例

### SM-RANK-003
- 用户问题：最近 30 天市级层面哪里最需要关注
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_ranking`
  - 预期 answer_type：`soil_ranking_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_ranking_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近30天内，市级层面最需要关注的前5名城市如下：

1. **徐州市**
   - 记录总数：1830
   - 平均20cm土层含水量：106.09%
   - 预警次数：87次
   - 状态分布：未触发预警 1743次、渍涝 80次、重度干旱 5次、设备故障 2次

2. **淮安市**
   - 记录总数：1590
   - 平均20cm土层含水量：99.39%
   - 预警次数：39次
   - 状态分布：未触发预警 1551次、渍涝 26次、重度干旱 2次、设备故障 11次

3. **苏州市**
   - 记录总数：1170
   - 平均20cm土层含水量：103.73%
   - 预警次数：37次
   - 状态分布：未触发预警 1133次、渍涝 37次

4. **常州市**
   - 记录总数：660
   - 平均20cm土层含水量：104.71%
   - 预警次数：35次
   - 状态分布：未触发预警 625次、重度干旱 10次、渍涝 25次

5. **扬州市**
   - 记录总数：1050
   - 平均20cm土层含水量：99.98%
   - 预警次数：17次
   - 状态分布：未触发预警 1033次、渍涝 5次、设备故障 12次

从数据来看，徐州市和淮安市在最近一个月内的土壤墒情问题较为突出，特别是渍涝情况较多。建议对这两个城市的土壤墒情加强监测与管理。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_ranking`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`13` 个分组
  - 聚合结果 / 排名结果：`[{"name": "徐州市", "record_count": 1830, "avg_water20cm": 106.09, "alert_count": 87, "status_counts": {"not_triggered": 1743, "waterlogging": 80, "heavy_drought": 5, "device_fault": 2}, "rank": 1}, {"name": "淮安市", "record_count": 1590, "avg_water20cm": 99.39, "alert_count": 39, "status_counts": {"not_triggered": 1551, "waterlogging": 26, "heavy_drought": 2, "device_fault": 11}, "rank": 2}, {"name": "苏州市", "record_count": 1170, "avg_water20cm": 103.73, "alert_count": 37, "status_counts": {"not_triggered": 1133, "waterlogging": 37}, "rank": 3}, {"name": "常州市", "record_count": 660, "avg_water20cm": 104.71, "alert_count": 35, "status_counts": {"not_triggered": 625, "heavy_drought": 10, "waterlogging": 25}, "rank": 4}, {"name": "扬州市", "record_count": 1050, "avg_water20cm": 99.98, "alert_count": 17, "status_counts": {"not_triggered": 1033, "waterlogging": 5, "device_fault": 12}, "rank": 5}]`
- 当前回答（case 样例）：按市级风险排序，最近 30 天最需要关注的是 `徐州市`，其后依次是 `淮安市`、`苏州市`、`常州市` 和 `扬州市`。其中徐州市的预警相关记录达到 `87` 条，是当前市级层面最突出的风险来源。
- 实际回答：最近30天内，市级层面最需要关注的前5名城市如下：

1. **徐州市**
   - 记录总数：1830
   - 平均20cm土层含水量：106.09%
   - 预警次数：87次
   - 状态分布：未触发预警 1743次、渍涝 80次、重度干旱 5次、设备故障 2次

2. **淮安市**
   - 记录总数：1590
   - 平均20cm土层含水量：99.39%
   - 预警次数：39次
   - 状态分布：未触发预警 1551次、渍涝 26次、重度干旱 2次、设备故障 11次

3. **苏州市**
   - 记录总数：1170
   - 平均20cm土层含水量：103.73%
   - 预警次数：37次
   - 状态分布：未触发预警 1133次、渍涝 37次

4. **常州市**
   - 记录总数：660
   - 平均20cm土层含水量：104.71%
   - 预警次数：35次
   - 状态分布：未触发预警 625次、重度干旱 10次、渍涝 25次

5. **扬州市**
   - 记录总数：1050
   - 平均20cm土层含水量：99.98%
   - 预警次数：17次
   - 状态分布：未触发预警 1033次、渍涝 5次、设备故障 12次

从数据来看，徐州市和淮安市在最近一个月内的土壤墒情问题较为突出，特别是渍涝情况较多。建议对这两个城市的土壤墒情加强监测与管理。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_ranking(aggregation=city,top_n=5,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；Top5 应为 `徐州市 / 淮安市 / 苏州市 / 常州市 / 扬州市`
  - 预期实体：`市级排行`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`徐州市 > 淮安市 > 苏州市 > 常州市 > 扬州市`
  - 预期诊断类别：`未单列`
  - 必含事实：`87`
  - 禁止事实：`聚合维度写成县区`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_ranking，实际 无。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：市级排行样例

### SM-RANK-004
- 用户问题：最近 7 天县区前 3 名是谁
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_ranking`
  - 预期 answer_type：`soil_ranking_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_ranking_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近7天内，县区级土壤墒情排名前3名如下：

1. **睢宁县**（徐州市）
   - 平均20cm土层含水量：129.17%
   - 预警次数：9次
   - 状态：未触发预警
   
2. **沛县**（徐州市）
   - 平均20cm土层含水量：111.14%
   - 预警次数：8次
   - 状态：未触发预警

3. **昆山市**（苏州市）
   - 平均20cm土层含水量：96.68%
   - 预警次数：7次
   - 状态：未触发预警

这些县区在最近一周内的土壤含水量相对较高，但整体上没有达到触发持续性预警的状态。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_ranking`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`80` 个分组
  - 聚合结果 / 排名结果：`[{"name": "睢宁县", "record_count": 49, "avg_water20cm": 129.17, "alert_count": 9, "status_counts": {"not_triggered": 40, "waterlogging": 9}, "rank": 1}, {"name": "沛县", "record_count": 56, "avg_water20cm": 111.14, "alert_count": 8, "status_counts": {"not_triggered": 48, "waterlogging": 8}, "rank": 2}, {"name": "昆山市", "record_count": 49, "avg_water20cm": 96.68, "alert_count": 7, "status_counts": {"waterlogging": 7, "not_triggered": 42}, "rank": 3}]`
- 当前回答（case 样例）：如果只看最近 7 天，县区前 3 名分别是 `睢宁县`、`沛县` 和 `昆山市`。对应的预警相关记录分别是 `9`、`8` 和 `7` 条，说明短时间窗口内这三个县区的风险更集中。
- 实际回答：最近7天内，县区级土壤墒情排名前3名如下：

1. **睢宁县**（徐州市）
   - 平均20cm土层含水量：129.17%
   - 预警次数：9次
   - 状态：未触发预警
   
2. **沛县**（徐州市）
   - 平均20cm土层含水量：111.14%
   - 预警次数：8次
   - 状态：未触发预警

3. **昆山市**（苏州市）
   - 平均20cm土层含水量：96.68%
   - 预警次数：7次
   - 状态：未触发预警

这些县区在最近一周内的土壤含水量相对较高，但整体上没有达到触发持续性预警的状态。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_ranking(aggregation=county,top_n=3,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；Top3 应为 `睢宁县 / 沛县 / 昆山市`
  - 预期实体：`县区排行`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`睢宁县 > 沛县 > 昆山市`
  - 预期诊断类别：`未单列`
  - 必含事实：`9 / 8 / 7`
  - 禁止事实：`把 30 天数据混进 7 天排行`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_ranking，实际 无。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：时间窗排行样例

### SM-DETAIL-001
- 用户问题：南通市最近 7 天详细情况怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`259`
  - 关键字段：`{"entity_name": "南通市", "record_count": 259, "status_summary": {"not_triggered": 259}}`
  - 关键记录样本：`[{"sn": "SNS00205026", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 105.84, "soil_status": null}, {"sn": "SNS00205024", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 86.13, "soil_status": null}, {"sn": "SNS00214092", "city": "南通市", "county": "启东市", "create_time": "2026-04-13 23:59:17", "water20cm": 91.96, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "region", "entity_name": "南通市", "record_count": 259, "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00205026", "city": "南通市", "county": "海安市", "create_time": "2026-04-13 23:59:17", "water20cm": 105.84, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 259}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：最近 7 天南通市共汇总 `259` 条记录，全部为未触发预警状态。最新一条记录来自 `SNS00204333`，时间是 `2026-04-13 23:59:17`，位于 `如东县`，20 厘米含水量 `92.43%`，当前没有发现需要升级处理的异常。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(city=南通市,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=259`，latest record 为 `SNS00204333 / 如东县 / 2026-04-13 23:59:17`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`259 / 92.43`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`SNS00204333`
  - 禁止事实：`存在明显预警`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 normal，实际 无/未返回。；实际回答缺少必含事实：SNS00204333。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：地区详情样例

### SM-DETAIL-002
- 用户问题：SNS00204333 最近 7 天怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`tool_missing`
  - 实际 final_answer：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE sn = 'SNS00204333' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`7`
  - 关键字段：`{"entity_name": "SNS00204333", "record_count": 7, "status_summary": {"not_triggered": 7}}`
  - 关键记录样本：`[{"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-12 23:59:17", "water20cm": 92.45, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-11 23:59:17", "water20cm": 92.74, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "device", "entity_name": "SNS00204333", "record_count": 7, "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 7}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：设备 `SNS00204333` 最近 7 天共有 `7` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，位于 `南通市如东县`，20 厘米含水量 `92.43%`，目前没有异常告警。
- 实际回答：LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(sn=SNS00204333,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=7`，latest record `water20cm=92.43`
  - 预期实体：`SNS00204333`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`7 / 92.43`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`南通市如东县`
  - 禁止事实：`找不到设备`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；fallback_reason 不匹配：期望 无，实际 tool_missing。；实际回答缺少必含事实：南通市如东县。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：设备详情基准样例

### SM-DETAIL-003
- 用户问题：如东最近怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：最近7天内，如东县的土壤墒情概况如下：

- 总记录数：48条
- 平均20厘米土层含水量：76.46%
- 状态分布：全部为未触发预警状态
- 预警次数：0次

整体来看，如东县最近一周没有出现土壤墒情预警情况，土壤湿度处于正常范围。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE county = '如东县' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`42`
  - 关键字段：`{"entity_name": "如东县", "record_count": 42, "status_summary": {"not_triggered": 42}}`
  - 关键记录样本：`[{"sn": "SNS00204336", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 70.09, "soil_status": null}, {"sn": "SNS00204337", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 74.62, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "region", "entity_name": "如东县", "record_count": 42, "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00204336", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 70.09, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 42}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：如果把“如东”按业务常用说法解析为 `如东县`，最近 7 天如东县共有 `42` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，最新设备是 `SNS00204333`，20 厘米含水量 `92.43%`，当前整体平稳。
- 实际回答：最近7天内，如东县的土壤墒情概况如下：

- 总记录数：48条
- 平均20厘米土层含水量：76.46%
- 状态分布：全部为未触发预警状态
- 预警次数：0次

整体来看，如东县最近一周没有出现土壤墒情预警情况，土壤湿度处于正常范围。
- 一致性结论：`结论基本一致，措辞不同`
- 数据库事实校验：
  - 数据库校验断言：按标准实体 `如东县` 回查 `query_soil_detail(county=如东县,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=42`
  - 预期实体：`如东县`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`42 / 92.43`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`如东县`
  - 禁止事实：`把如东理解成其他地区`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 soil_summary_answer。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason`
- 备注：地区别名样例

### SM-DETAIL-004
- 用户问题：那如东县呢
- 上下文：上一轮已查询“南通市最近 7 天整体情况”
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_colloquial`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_summary_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：如东县最近7天的土壤墒情整体情况如下：

- 总记录数：42条
- 平均20厘米土层含水量：76.08%
- 状态分布：所有记录均未触发预警

在这段时间内，如东县没有出现需要特别关注的土壤墒情问题。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE county = '如东县' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`42`
  - 关键字段：`{"entity_name": "如东县", "record_count": 42, "status_summary": {"not_triggered": 42}}`
  - 关键记录样本：`[{"sn": "SNS00204336", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 70.09, "soil_status": null}, {"sn": "SNS00204337", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 74.62, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "region", "entity_name": "如东县", "record_count": 42, "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00204336", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 70.09, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 42}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：沿用上一轮“最近 7 天”的时间框架，如东县最近 7 天共有 `42` 条记录，全部为未触发预警状态。最新记录时间是 `2026-04-13 23:59:17`，最新设备 `SNS00204333` 的 20 厘米含水量为 `92.43%`，当前没有异常告警。
- 实际回答：如东县最近7天的土壤墒情整体情况如下：

- 总记录数：42条
- 平均20厘米土层含水量：76.08%
- 状态分布：所有记录均未触发预警

在这段时间内，如东县没有出现需要特别关注的土壤墒情问题。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(county=如东县,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；应得到 `record_count=42`
  - 预期实体：`如东县`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`42 / 92.43`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`沿用最近7天`
  - 禁止事实：`重新澄清时间窗`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 soil_summary_answer。；case 当前回答缺少必含事实：沿用最近7天。；实际回答缺少必含事实：沿用最近7天。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：多轮对象切换样例 1

### SM-DETAIL-005
- 用户问题：那 SNS00204333 呢
- 上下文：上一轮刚做完最近 30 天排行查询
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`normal`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_colloquial`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE sn = 'SNS00204333' AND create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`30`
  - 关键字段：`{"entity_name": "SNS00204333", "record_count": 30, "status_summary": {"not_triggered": 30}}`
  - 关键记录样本：`[{"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-12 23:59:17", "water20cm": 92.45, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-11 23:59:17", "water20cm": 92.74, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "device", "entity_name": "SNS00204333", "record_count": 30, "time_window": {"start_time": "2026-03-15 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 30}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：如果沿用上一轮的最近 30 天框架，设备 `SNS00204333` 在这段时间内有稳定数据，但没有触发预警。它位于 `南通市如东县`，最新记录时间仍是 `2026-04-13 23:59:17`，最新 20 厘米含水量 `92.43%`。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(sn=SNS00204333,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；应存在最新记录 `2026-04-13 23:59:17`
  - 预期实体：`SNS00204333`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`latest_record.water20cm=92.43`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`南通市如东县`
  - 禁止事实：`继续输出排行结果`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 normal，实际 无/未返回。；实际回答缺少必含事实：南通市如东县。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：多轮对象切换样例 2

### SM-DETAIL-006
- 用户问题：睢宁县最近一个月异常情况怎么样
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`anomaly_focus`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE county = '睢宁县' AND create_time >= '2026-03-15 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`210`
  - 关键字段：`{"entity_name": "睢宁县", "record_count": 210, "status_summary": {"not_triggered": 171, "waterlogging": 39}}`
  - 关键记录样本：`[{"sn": "SNS00213858", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 147.28, "soil_status": null}, {"sn": "SNS00204660", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 124.28, "soil_status": null}, {"sn": "SNS00213859", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 136.31, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "region", "entity_name": "睢宁县", "record_count": 210, "time_window": {"start_time": "2026-03-15 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00213858", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 147.28, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 171, "waterlogging": 39}, "alert_records": [{"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-13 23:59:17", "water20cm": 150.94, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-12 23:59:17", "water20cm": 153.37, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-11 23:59:17", "water20cm": 155.81, "soil_status": "waterlogging"}, {"sn": "SNS00213858", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-10 23:59:17", "water20cm": 151.58, "soil_status": "waterlogging"}, {"sn": "SNS00213891", "city": "徐州市", "county": "睢宁县", "create_time": "2026-04-10 23:59:17", "water20cm": 157.65, "soil_status": "waterlogging"}], "output_mode": "anomaly_focus"}`
- 当前回答（case 样例）：如果按异常视角看，睢宁县最近一个月需要重点关注。该时间窗共有 `210` 条记录，其中 `39` 条为预警相关记录，主要异常类型是 `涝渍`。最新一条普通记录虽然未触发预警，但近几条异常代表记录集中在设备 `SNS00213891`，说明局部点位风险较高。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(county=睢宁县,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59,output_mode=anomaly_focus)`；应得到 `record_count=210`、`status_summary.waterlogging=39`
  - 预期实体：`睢宁县`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`210 / 39`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：`SNS00213891`
  - 禁止事实：`没有异常`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 anomaly_focus，实际 无/未返回。；实际回答缺少必含事实：SNS00213891。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：detail 异常视角样例

### SM-DETAIL-007
- 用户问题：南通市今年需要发预警吗
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`warning_mode`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE city = '南通市' AND create_time >= '2026-01-01 00:00:00' AND create_time <= '2026-12-31 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`3811`
  - 关键字段：`{"entity_name": "南通市", "record_count": 3811, "status_summary": {"not_triggered": 3791, "waterlogging": 5, "device_fault": 1, "heavy_drought": 14}}`
  - 关键记录样本：`[{"sn": "SNS00205070", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 90.11, "soil_status": null}, {"sn": "SNS00213906", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 84.87, "soil_status": null}, {"sn": "SNS00213907", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 121.05, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "region", "entity_name": "南通市", "record_count": 3811, "time_window": {"start_time": "2026-01-01 00:00:00", "end_time": "2026-12-31 23:59:59"}, "latest_record": {"sn": "SNS00205070", "city": "南通市", "county": "通州区", "create_time": "2026-04-13 23:59:17", "water20cm": 90.11, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 3791, "waterlogging": 5, "device_fault": 1, "heavy_drought": 14}, "alert_records": [{"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-05 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-04 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-03 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}, {"sn": "SNS00211205", "city": "南通市", "county": "海门区", "create_time": "2026-03-03 23:59:17", "water20cm": 155.68, "soil_status": "waterlogging"}, {"sn": "SNS00211205", "city": "南通市", "county": "海门区", "create_time": "2026-03-02 23:59:17", "water20cm": 154.2, "soil_status": "waterlogging"}], "output_mode": "warning_mode", "warning_data": {"sn": "SNS00214096", "city": "南通市", "county": "启东市", "create_time": "2026-03-05 23:59:17", "water20cm": 154.31, "soil_status": "waterlogging"}}`
- 当前回答（case 样例）：如果从预警视角看，南通市今年确实有需要重点关注的记录。全年共 `3811` 条记录，预警相关记录 `20` 条，最新代表性预警样例是 `2026-03-05 23:59:17` 启东市设备 `SNS00214096` 的 `154.31%` 涝渍记录；此外如东县还有一组一月中旬的重旱记录。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(city=南通市,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=warning_mode)`；`warning_data` 应对应 `SNS00214096 / 启东市 / 154.31 / 2026-03-05 23:59:17`
  - 预期实体：`南通市`
  - 预期时间窗：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
  - 预期关键指标：`3811 / 20`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``SNS00214096`、`154.31``
  - 禁止事实：`全年完全没有预警`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 warning_mode，实际 无/未返回。；实际回答缺少必含事实：SNS00214096, 154.31。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：detail 预警视角样例

### SM-DETAIL-008
- 用户问题：SNS00204334 这种情况需要注意什么
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_colloquial`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`soil_detail_answer`
  - 预期 output_mode：`advice_mode`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`无`
- 实际契约：
  - 实际 input_type：`business_colloquial`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`无/未返回`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE sn = 'SNS00204334' AND create_time >= '2026-01-01 00:00:00' AND create_time <= '2026-12-31 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`103`
  - 关键字段：`{"entity_name": "SNS00204334", "record_count": 103, "status_summary": {"not_triggered": 89, "heavy_drought": 14}}`
  - 关键记录样本：`[{"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 84.0, "soil_status": null}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-04-12 23:59:17", "water20cm": 81.8, "soil_status": null}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-04-11 23:59:17", "water20cm": 82.7, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "device", "entity_name": "SNS00204334", "record_count": 103, "time_window": {"start_time": "2026-01-01 00:00:00", "end_time": "2026-12-31 23:59:59"}, "latest_record": {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 84.0, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 89, "heavy_drought": 14}, "alert_records": [{"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-01-14 23:59:17", "water20cm": 46.99, "soil_status": "heavy_drought"}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-01-13 23:59:17", "water20cm": 47.19, "soil_status": "heavy_drought"}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-01-12 23:59:17", "water20cm": 46.99, "soil_status": "heavy_drought"}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-01-11 23:59:17", "water20cm": 46.74, "soil_status": "heavy_drought"}, {"sn": "SNS00204334", "city": "南通市", "county": "如东县", "create_time": "2026-01-10 23:59:17", "water20cm": 46.84, "soil_status": "heavy_drought"}], "output_mode": "advice_mode"}`
- 当前回答（case 样例）：从建议视角看，设备 `SNS00204334` 当前最新记录已经恢复到未触发预警状态，但在 `2026-01-10` 到 `2026-01-14` 期间曾连续出现重旱记录。也就是说，这台设备近期不需要升级预警，不过仍建议结合一月中旬那段重旱历史，继续关注后续同类时段的水分波动。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(sn=SNS00204334,start=2026-01-01 00:00:00,end=2026-12-31 23:59:59,output_mode=advice_mode)`；应得到 `record_count=103`，alert records 连续覆盖 `2026-01-10 ~ 2026-01-14`
  - 预期实体：`SNS00204334`
  - 预期时间窗：`2026-01-01 00:00:00 ~ 2026-12-31 23:59:59`
  - 预期关键指标：`103 / heavy_drought 14`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`未单列`
  - 必含事实：``2026-01-10`、`2026-01-14``
  - 禁止事实：`当前仍在重旱`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 advice_mode，实际 无/未返回。；实际回答缺少必含事实：2026-01-10, 2026-01-14。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：detail 建议视角样例

### SM-FB-001
- 用户问题：查一下 SNS00204333 在 2025 年 1 月的墒情
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`diagnose_empty_result`
  - 预期 answer_type：`fallback_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`no_data`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_detail_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`no_data`
  - 实际 final_answer：对于设备 SNS00204333，在 2025 年 1 月期间没有找到任何土壤墒情记录。可能是该时间段内没有数据上报或设备未运行。

如果您需要查询其他时间段或其他设备的信息，请告诉我。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE sn = 'SNS00204333' AND create_time >= '2025-01-01 00:00:00' AND create_time <= '2025-01-31 23:59:59'
ORDER BY create_time DESC;
```
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`diagnose_empty_result`
```sql
SELECT COUNT(*) AS record_count_in_window FROM fact_soil_moisture WHERE 1=1 AND sn = 'SNS00204333' ;
```
- SQL 结果：
  - 结果总量：`315`
  - 诊断结果：`{"scenario": "period_exists", "diagnosis": "data_exists", "entity_type": "device", "entity_name": "SNS00204333", "record_count_all_time": null, "record_count_in_window": 315}`
- 当前回答（case 样例）：时间段 `2025-01-01 ~ 2025-01-31` 内没有 `SNS00204333` 的数据，可以扩大时间范围或查询其他时段。
- 实际回答：对于设备 SNS00204333，在 2025 年 1 月期间没有找到任何土壤墒情记录。可能是该时间段内没有数据上报或设备未运行。

如果您需要查询其他时间段或其他设备的信息，请告诉我。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：先查 `query_soil_detail(sn=SNS00204333,start=2025-01-01 00:00:00,end=2025-01-31 23:59:59)` 为空，再调用 `diagnose_empty_result(scenario=period_exists,sn=SNS00204333,...)`；诊断应为 `no_data_in_window`
  - 预期实体：`SNS00204333`
  - 预期时间窗：`2025-01-01 00:00:00 ~ 2025-01-31 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`no_data_in_window`
  - 必含事实：`扩大时间范围`
  - 禁止事实：`设备不存在`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`是`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`是`
  - 失败原因：`Tool 不匹配：期望 diagnose_empty_result，实际 无。；answer_type 不匹配：期望 fallback_answer，实际 soil_detail_answer。；output_mode 不匹配：期望 无，实际 normal。；实际回答缺少必含事实：扩大时间范围。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：空时间窗样例

### SM-FB-002
- 用户问题：查一下 SNS-UNKNOWN 最近一个月的数据
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`diagnose_empty_result`
  - 预期 answer_type：`fallback_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`entity_not_found`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`soil_detail_answer`
  - 实际 output_mode：`normal`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`no_data`
  - 实际 final_answer：对于设备编号 SNS-UNKNOWN，在 2026-03-14 到 2026-04-13 这一时间段内没有找到任何土壤墒情记录。可能是该设备不存在，或者在这段时间内没有上传数据。如果您确认设备是存在的，请检查设备是否正常工作或联系技术支持进一步排查问题。
- 执行方式：`live-http-agent`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`diagnose_empty_result`
```sql
SELECT COUNT(*) AS record_count_all_time FROM fact_soil_moisture WHERE sn = 'SNS-UNKNOWN';
```
- SQL 结果：
  - 结果总量：`0`
  - 诊断结果：`{"scenario": "device_exists", "diagnosis": "entity_not_found", "entity_type": "device", "entity_name": "SNS-UNKNOWN", "record_count_all_time": 0, "record_count_in_window": null}`
- 当前回答（case 样例）：设备 `SNS-UNKNOWN` 在系统中不存在，请核对设备编号。
- 实际回答：对于设备编号 SNS-UNKNOWN，在 2026-03-14 到 2026-04-13 这一时间段内没有找到任何土壤墒情记录。可能是该设备不存在，或者在这段时间内没有上传数据。如果您确认设备是存在的，请检查设备是否正常工作或联系技术支持进一步排查问题。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `diagnose_empty_result(scenario=device_exists,sn=SNS-UNKNOWN,start=2026-03-15 00:00:00,end=2026-04-13 23:59:59)`；诊断应为 `entity_not_found`
  - 预期实体：`SNS-UNKNOWN`
  - 预期时间窗：`2026-03-15 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`entity_not_found`
  - 必含事实：`核对设备编号`
  - 禁止事实：`只是时间窗没数据`
  - Case 当前回答是否符合事实：`是`
  - 实际回答是否符合事实：`否`
  - 实际回答事实冲突：`数据库诊断为 entity_not_found，但回答更像 no_data_in_window。`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`否`
  - 失败原因：`Tool 不匹配：期望 diagnose_empty_result，实际 无。；answer_type 不匹配：期望 fallback_answer，实际 soil_detail_answer。；output_mode 不匹配：期望 无，实际 normal。；fallback_reason 不匹配：期望 entity_not_found，实际 no_data。；实际回答与数据库事实不一致。；实际回答缺少必含事实：核对设备编号。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：不存在对象样例

### SM-FB-003
- 用户问题：直接告诉我南通市近 7 天有没有异常，不要查库
- 上下文：无
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`无（应被 P0 拦截）`
  - 预期 answer_type：`fallback_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`tool_missing`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`tool_missing`
  - 实际 final_answer：当前业务问题必须查询真实数据后才能回答。系统检测到模型未调用任何查询工具就直接作答，已拦截此回答，请换一种问法重试。
- 执行方式：`controlled-current-code-p0-tool-missing`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - 不适用（非业务 guidance case，不查库）。
- SQL 结果：
  - 不适用（非业务 guidance case，不查库）。
- 当前回答（case 样例）：当前业务问题必须查询真实数据后才能回答。系统检测到模型未调用任何查询工具就直接作答，已拦截此回答，请换一种问法重试。
- 实际回答：当前业务问题必须查询真实数据后才能回答。系统检测到模型未调用任何查询工具就直接作答，已拦截此回答，请换一种问法重试。
- 一致性结论：`结论一致`
- 数据库事实校验：
  - 数据库校验断言：不直接查库；验证拦截逻辑优先于回答生成
  - 预期实体：`未单列`
  - 预期时间窗：`未单列`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`tool_missing`
  - 必含事实：`必须查询真实数据`
  - 禁止事实：``南通市近7天很正常` 这类未查库业务结论`
  - Case 当前回答是否符合事实：`待校验`
  - 实际回答是否符合事实：`待校验`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`待校验`
  - 失败原因：`业务 case 未命中 Tool。；数据库回查阻塞：数据库校验断言中没有可解析的 tool 调用。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志`
- 备注：P0 红线样例

### SM-FB-004
- 用户问题：SNS00204333 最近有数据吗（模拟模型错误回答“没有数据”）
- 上下文：内部事实核验阶段发现回答与查询结果冲突
- 预期契约：
  - 预期 input_type：`business_direct`
  - 预期 Tool：`query_soil_detail`
  - 预期 answer_type：`fallback_answer`
  - 预期 output_mode：`无`
  - 预期 guidance_reason：`无`
  - 预期 fallback_reason：`fact_check_failed`
- 实际契约：
  - 实际 input_type：`business_direct`
  - 实际 Tool：`无`
  - 实际 answer_type：`fallback_answer`
  - 实际 output_mode：`无/未返回`
  - 实际 guidance_reason：`无/未返回`
  - 实际 fallback_reason：`fact_check_failed`
  - 实际 final_answer：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 执行方式：`controlled-current-code-fact-check-injection`
- Tool 调用：
  - 是否命中 Tool：`否`
  - 实际命中的 Tool 名称：`无`
  - Tool 调用参数：`无`
  - Tool trace：`[]`
  - query_result：`{}`
  - answer_facts：`{}`
  - query_log_entries：`[]`
- SQL / 等效 SQL：
  - SQL 类型：`等效 SQL（由数据库校验断言重建）`
  - 对应 Tool：`query_soil_detail`
```sql
SELECT id, sn, city, county,
       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
       source_file, source_sheet, source_row
FROM fact_soil_moisture
WHERE sn = 'SNS00204333' AND create_time >= '2026-04-07 00:00:00' AND create_time <= '2026-04-13 23:59:59'
ORDER BY create_time DESC;
```
- SQL 结果：
  - 结果总量：`7`
  - 关键字段：`{"entity_name": "SNS00204333", "record_count": 7, "status_summary": {"not_triggered": 7}}`
  - 关键记录样本：`[{"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-12 23:59:17", "water20cm": 92.45, "soil_status": null}, {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-11 23:59:17", "water20cm": 92.74, "soil_status": null}]`
  - 聚合结果 / 详情结果：`{"tool": "query_soil_detail", "entity_type": "device", "entity_name": "SNS00204333", "record_count": 7, "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}, "latest_record": {"sn": "SNS00204333", "city": "南通市", "county": "如东县", "create_time": "2026-04-13 23:59:17", "water20cm": 92.43, "soil_status": "not_triggered"}, "status_summary": {"not_triggered": 7}, "alert_records": [], "output_mode": "normal"}`
- 当前回答（case 样例）：回答声称无数据，但查询结果中存在数据，已安全降级，请重新提问。
- 实际回答：当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。
- 一致性结论：`结论不一致`
- 数据库事实校验：
  - 数据库校验断言：调用 `query_soil_detail(sn=SNS00204333,start=2026-04-07 00:00:00,end=2026-04-13 23:59:59)`；实际 `record_count=7`，因此任何“无数据”回答都应判定为事实不一致并触发 fallback
  - 预期实体：`SNS00204333`
  - 预期时间窗：`2026-04-07 00:00:00 ~ 2026-04-13 23:59:59`
  - 预期关键指标：`未单列`
  - 预期排序结果：`未单列`
  - 预期诊断类别：`fact_check_failed`
  - 必含事实：`存在真实数据`
  - 禁止事实：`无数据`
  - Case 当前回答是否符合事实：`否`
  - 实际回答是否符合事实：`是`
  - Case 当前回答事实冲突：`数据库存在数据，但回答声称无数据/不存在。`
- 最终判定：
  - 是否通过：`否`
  - 是否符合事实：`否`
  - 失败原因：`Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；case 当前回答与数据库事实不一致。；case 当前回答缺少必含事实：存在真实数据。；实际回答缺少必含事实：存在真实数据。；case 当前回答命中禁止事实：无数据。；当前回答与实际回答结论不一致。`
  - 修复建议：`将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志；修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实；把正式 case 规定的关键实体、时间窗和指标写进最终回答`
- 备注：事实核验失败样例


## 5. 汇总统计
- 通过条数：`5`
- 失败条数：`25`
- 各 answer_type 通过情况：
  - `guidance_answer`：`5/8`
  - `soil_summary_answer`：`0/6`
  - `soil_ranking_answer`：`0/4`
  - `soil_detail_answer`：`0/8`
  - `fallback_answer`：`0/4`
- 各 output_mode 通过情况：
  - `无`：`5/12`
  - `normal`：`0/12`
  - `anomaly_focus`：`0/2`
  - `warning_mode`：`0/2`
  - `advice_mode`：`0/2`
- 各 fallback_reason 通过情况：
  - `无`：`5/26`
  - `no_data`：`0/1`
  - `entity_not_found`：`0/1`
  - `tool_missing`：`0/1`
  - `fact_check_failed`：`0/1`

## 6. 失败 case 清单
- `SM-CONV-004`：answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 clarification，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。
- `SM-CONV-006`：answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 boundary，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。
- `SM-CONV-008`：answer_type 不匹配：期望 guidance_answer，实际 fallback_answer。；guidance_reason 不匹配：期望 closing，实际 无/未返回。；fallback_reason 不匹配：期望 无，实际 tool_missing。
- `SM-SUM-001`：Tool 不匹配：期望 query_soil_summary，实际 无。
- `SM-SUM-002`：Tool 不匹配：期望 query_soil_summary，实际 无。
- `SM-SUM-003`：Tool 不匹配：期望 query_soil_summary，实际 无。；实际回答缺少必含事实：2026-04-13。；当前回答与实际回答结论不一致。
- `SM-SUM-004`：Tool 不匹配：期望 query_soil_summary，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_summary_answer，实际 fallback_answer。；output_mode 不匹配：期望 anomaly_focus，实际 无/未返回。；实际回答缺少必含事实：睢宁县, 39, 涝渍。；当前回答与实际回答结论不一致。
- `SM-SUM-005`：Tool 不匹配：期望 query_soil_summary，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_summary_answer，实际 fallback_answer。；output_mode 不匹配：期望 warning_mode，实际 无/未返回。；实际回答缺少必含事实：SNS00214096, 154.31%。；当前回答与实际回答结论不一致。
- `SM-SUM-006`：Tool 不匹配：期望 query_soil_summary，实际 无。；output_mode 不匹配：期望 advice_mode，实际 anomaly_focus。；实际回答缺少必含事实：总体平稳。；当前回答与实际回答结论不一致。
- `SM-RANK-001`：Tool 不匹配：期望 query_soil_ranking，实际 无。
- `SM-RANK-002`：Tool 不匹配：期望 query_soil_ranking，实际 无。；实际回答缺少必含事实：徐州市沛县, 苏州市昆山市。；当前回答与实际回答结论不一致。
- `SM-RANK-003`：Tool 不匹配：期望 query_soil_ranking，实际 无。
- `SM-RANK-004`：Tool 不匹配：期望 query_soil_ranking，实际 无。
- `SM-DETAIL-001`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 normal，实际 无/未返回。；实际回答缺少必含事实：SNS00204333。；当前回答与实际回答结论不一致。
- `SM-DETAIL-002`：Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；fallback_reason 不匹配：期望 无，实际 tool_missing。；实际回答缺少必含事实：南通市如东县。；当前回答与实际回答结论不一致。
- `SM-DETAIL-003`：Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 soil_summary_answer。
- `SM-DETAIL-004`：Tool 不匹配：期望 query_soil_detail，实际 无。；answer_type 不匹配：期望 soil_detail_answer，实际 soil_summary_answer。；case 当前回答缺少必含事实：沿用最近7天。；实际回答缺少必含事实：沿用最近7天。；当前回答与实际回答结论不一致。
- `SM-DETAIL-005`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 normal，实际 无/未返回。；实际回答缺少必含事实：南通市如东县。；当前回答与实际回答结论不一致。
- `SM-DETAIL-006`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 anomaly_focus，实际 无/未返回。；实际回答缺少必含事实：SNS00213891。；当前回答与实际回答结论不一致。
- `SM-DETAIL-007`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 warning_mode，实际 无/未返回。；实际回答缺少必含事实：SNS00214096, 154.31。；当前回答与实际回答结论不一致。
- `SM-DETAIL-008`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；answer_type 不匹配：期望 soil_detail_answer，实际 fallback_answer。；output_mode 不匹配：期望 advice_mode，实际 无/未返回。；实际回答缺少必含事实：2026-01-10, 2026-01-14。；当前回答与实际回答结论不一致。
- `SM-FB-001`：Tool 不匹配：期望 diagnose_empty_result，实际 无。；answer_type 不匹配：期望 fallback_answer，实际 soil_detail_answer。；output_mode 不匹配：期望 无，实际 normal。；实际回答缺少必含事实：扩大时间范围。；当前回答与实际回答结论不一致。
- `SM-FB-002`：Tool 不匹配：期望 diagnose_empty_result，实际 无。；answer_type 不匹配：期望 fallback_answer，实际 soil_detail_answer。；output_mode 不匹配：期望 无，实际 normal。；fallback_reason 不匹配：期望 entity_not_found，实际 no_data。；实际回答与数据库事实不一致。；实际回答缺少必含事实：核对设备编号。；当前回答与实际回答结论不一致。
- `SM-FB-003`：业务 case 未命中 Tool。；数据库回查阻塞：数据库校验断言中没有可解析的 tool 调用。
- `SM-FB-004`：Tool 不匹配：期望 query_soil_detail，实际 无。；业务 case 未命中 Tool。；case 当前回答与数据库事实不一致。；case 当前回答缺少必含事实：存在真实数据。；实际回答缺少必含事实：存在真实数据。；case 当前回答命中禁止事实：无数据。；当前回答与实际回答结论不一致。

## 7. 最终结论
- 最终结论：`不通过`
- 是否还存在“未调 Tool 直接回答业务问题”的路径：`是`
- 是否所有业务 case 都能被数据库支撑：`否`
- 哪些 case 的 `是否符合事实` 需要更新：`SM-FB-003, SM-FB-002, SM-FB-004`
- 阻塞项：`Python 基础测试失败`
