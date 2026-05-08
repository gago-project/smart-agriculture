# 墒情 Agent 测试数据目录

本目录存放 `soil-moisture` Agent 的真实对话库与回归样本。

## 快速回归入口（unit tests）

```bash
PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m pytest apps/agent/tests/ -q
```

重点测试文件：
- `apps/agent/tests/test_turn_route_decision_service_unittest.py`
- `apps/agent/tests/test_turn_route_query_shape_matrix_unittest.py`
- `apps/agent/tests/test_query_profile_governance_unittest.py`
- `apps/agent/tests/test_data_answer_service_unittest.py`

## 真实问答资产

- `real-conversations/cases/real-conversation-library.md` — 真实用户问法库
- `real-conversations/analysis-60.md` — 60 条真实问答分析
- `outputs/` — 历次真实问答测试输出结果

## 说明

- 答案质量通过直接看真实问答判断，不依赖自动化 case 对比
- 新增问法变体、路由冲突优先补到 unit test 路由矩阵
- 失败回归样本沉淀到 `real-conversations/regressions/`
