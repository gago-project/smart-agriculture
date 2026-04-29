# 水产运输车辆智能识别系统 — 企业级方案总索引

> 本目录包含从数据采集到生产运营的完整技术方案，面向企业落地场景，覆盖算法训练、部署、运维与调优全生命周期。

## 文档结构

| 文件 | 内容 | 受众 |
|------|------|------|
| [00-system-architecture.md](./00-system-architecture.md) | 系统架构与技术选型总览 | 架构师、技术负责人 |
| [01-data-pipeline.md](./01-data-pipeline.md) | 数据采集、标注与预处理流水线 | 数据工程师、标注团队 |
| [02-model-training.md](./02-model-training.md) | 四大算法模型训练方案（目标识别、车辆分类、车牌识别、OCR） | 算法工程师 |
| [03-deployment.md](./03-deployment.md) | 企业级部署方案（边缘+云端+混合） | 运维、DevOps |
| [04-operations-optimization.md](./04-operations-optimization.md) | 生产运营、监控告警与持续调优 | 运维、算法工程师 |

## 四大核心能力

```
视频监控 / 无人机 / 业务系统
         ↓
  ┌─────────────────────────────┐
  │  1. 目标识别（Vehicle Detection）   │
  │  2. 车辆分类（Classification）     │
  │  3. 车牌识别（LPR）               │
  │  4. 车身文字提取（OCR）           │
  └─────────────────────────────┘
         ↓
   监管平台 / 告警推送 / 报表
```

## 快速阅读路径

- **决策者**：先读 `00-system-architecture.md` → `03-deployment.md` 的成本估算部分
- **算法工程师**：`01-data-pipeline.md` → `02-model-training.md` → `04-operations-optimization.md`
- **运维/DevOps**：`03-deployment.md` → `04-operations-optimization.md`

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-04-29 | 初版，覆盖完整四阶段方案 |
