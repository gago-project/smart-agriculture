# 墒情 Agent 测试数据目录

本目录用于存放 `soil-moisture` Agent 的长期测试样例源数据，和 `outputs/` 中的一次性测试结果区分开。

当前唯一正式 Case 主库：

- `testdata/agent/soil-moisture/case-library.md`

当前正式规模为 `130` 个 Case，其中新增多轮话题边界专项 Case 直接并入同一主库。分类覆盖按业务价值加权，不做均分；业务高频场景保留更多样例，非业务和能力边界只保留代表性样例。

## 目录定位

- `testdata/agent/soil-moisture/`：长期维护、可复用、可继续扩展的测试样例源。
- `docs/testing/agent/soil-moisture/`：测试规则、验收口径、评审说明。
- `outputs/`：某次执行导出的 Excel、CSV、截图、临时复测产物。

## 适合放在这里的内容

- 结构化 Case 样例库
- 回归样例标签说明
- 评审用标准输入集
- 专项问题清单与稳定复现样例

## 暂不在这里落的内容

- 一次性复测导出的 Excel
- 临时截图和手工记录
- 仅用于某次群内同步的临时表格

## 后续建议

当前正式 Case 的新增、删减、修订，应优先直接更新 `case-library.md`。

等未来确实需要结构化导出格式时，再考虑在本目录继续补：

- `case-library.csv` 或 `case-library.xlsx`
- `case-library.jsonl`
- `labels.md`
- `fixtures/`

当前先以 Markdown 主库为准，不提前固化第二种源格式。
