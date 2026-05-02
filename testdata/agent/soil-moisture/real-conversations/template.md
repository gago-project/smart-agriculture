# Real Conversation Template

## Metadata

- `CaseID`: `RC-001`
- `bucket`: `single_turn`
- `source`: `manual`
- `status`: `draft`

## Question

- `question`: `最近 7 天整体墒情怎么样`
- `context`: `无`

## Expected

- `expected_input_type`: `business_direct`
- `expected_answer_kind`: `business`
- `expected_capability`: `summary`
- `expected_block_types`:
  - `summary_card`
- `expected_output_mode`: `normal`
- `expected_query_behavior`: `must_query`
- `expected_follow_up_behavior`: `standalone`

## Facts

- `must_have_facts`:
  - `时间窗`
  - `记录数`
  - `是否有预警`
- `must_not_have_facts`:
  - `数据库不存在的派生字段`
- `must_not_show`:
  - `重复回复`
  - `与证据不一致的内容`

## Evidence

- `evidence_requirements`:
  - `可回查真实 SQL`
  - `可回查真实结果`
  - `可追踪到 turn / session`
- `db_assertion`: `按 question 和 context 回查并核对结果`

## Notes

- `notes`: `这里是模板，不是正式样本`
