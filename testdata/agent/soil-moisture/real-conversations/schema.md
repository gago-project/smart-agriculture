# Real Conversation Schema

## 核心字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `CaseID` | string | 是 | 唯一编号，建议 `RC-001` / `RR-001` |
| `bucket` | enum | 是 | `single_turn / follow_up / boundary / ui / regression` |
| `source` | enum | 是 | `manual / prod / qa / bug / rewrite` |
| `question` | string | 是 | 用户原始问法，尽量保留口语 |
| `context` | string\|array | 否 | 上下文，写清上一轮和当前轮的关系 |
| `expected_input_type` | enum | 否 | 如果需要覆盖输入分类，可写 `business_direct / business_colloquial / greeting / capability_question / conversation_closing` 等 |
| `expected_answer_kind` | enum | 是 | 与运行时返回一致，写 `business / guidance / fallback` |
| `expected_capability` | enum | 是 | `summary / list / group / detail / compare / rule / template / count / field` |
| `expected_block_types` | array[string] | 否 | 例如 `summary_card / list_table / detail_card / compare_card / count_card / field_card` |
| `expected_output_mode` | enum | 否 | 例如 `normal / anomaly_focus / warning_mode / advice_mode` |
| `expected_query_behavior` | enum | 是 | `must_query / may_query / no_query` |
| `expected_follow_up_behavior` | enum | 否 | `standalone / inherit / drill_down / correct / clarify / close` |
| `must_have_facts` | array[string] | 是 | 回答里必须出现的关键事实 |
| `must_not_have_facts` | array[string] | 是 | 回答里不能出现的事实或字段 |
| `must_not_show` | array[string] | 否 | 不该展示的 UI 或多余字段 |
| `evidence_requirements` | array[string] | 否 | 需要核对的证据点 |
| `db_assertion` | string | 是 | 如何回查数据库 |
| `status` | enum | 否 | `draft / verified / blocked / deprecated` |
| `notes` | string | 否 | 额外说明 |

## 分组建议

- `single_turn`: 单轮自然问答
- `follow_up`: 上下文追问、纠错、下钻
- `boundary`: 能力边界、澄清、兜底
- `ui`: 列表分页、证据展示、长结果处理
- `regression`: 已知失败点回归

## 对齐当前运行时的最小口径

- 优先写 `expected_answer_kind + expected_capability + expected_block_types`
- 不再把旧的 `answer_type` 当成真实运行时单一真源
- 如果某条样本是“你好 / 你能做什么 / 结束语”，`expected_query_behavior` 应为 `no_query`
- 如果某条样本依赖上一轮，`expected_follow_up_behavior` 不能省略
