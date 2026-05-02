# Soil Moisture Real Conversations

这是一套独立于 56 条正式验收 Case 的真实问答资产。

## 目标

- 记录更贴近线上用户的真实问法
- 覆盖自然追问、省略表达、纠错、下钻、列表、规则/模板、UI 证据展示
- 把每次新翻车的问题沉淀成可复用的回归样本

## 和 56 Case 的关系

- `56` 条正式 Case 继续作为硬门禁
- 本目录专门承载“真实对话”和“失败回归”
- 真实问答可以增长，不要求固定总数

## 目录结构

```text
real-conversations/
  README.md
  schema.md
  template.md
  cases/
    README.md
  regressions/
    README.md
```

## 记录规则

- 一个真实问答 = 一个独立样本文件
- 一个样本只描述一条真实对话或一个明确失败点
- 不在这里重复写 56 条正式 Case 的内容
- 新发现的 bug 优先进入 `regressions/`

## 推荐命名

- 真实问答：`RC-001-<short-slug>.md`
- 回归样本：`RR-001-<short-slug>.md`
