# Real Conversation Cases

这里存放真实用户问答样本。

## 单条样本建议字段

- `CaseID`
- `bucket`
- `source`
- `question`
- `context`
- `expected_answer_kind`
- `expected_capability`
- `expected_block_types`
- `must_have_facts`
- `must_not_have_facts`
- `notes`

## 写法建议

- 每条样本尽量保留原始口语
- 上下文要写完整，不要只写“同上”
- 如果样本依赖上一轮，明确写出上一轮问了什么
