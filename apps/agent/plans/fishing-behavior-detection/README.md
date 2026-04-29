# 水产养殖区域捕捞行为智能识别系统 — 企业级方案总索引

> 本方案覆盖水产养殖禁捕区的全天候智能监管，通过多模态、多维度算法联动，
> 实现人体识别、人体跟踪、聚集行为预警、渔船与渔具识别、捕捞行为综合研判的完整闭环。

## 文档结构

| 文件 | 内容 | 受众 |
|------|------|------|
| [00-system-architecture.md](./00-system-architecture.md) | 四大模块系统架构、技术选型、KPI 体系 | 架构师、技术负责人 |
| [01-data-pipeline.md](./01-data-pipeline.md) | 多场景数据采集、标注规范、预处理与版本管理 | 数据工程师、标注团队 |
| [02-model-training.md](./02-model-training.md) | 人体检测/跟踪/聚集/渔船/渔具/行为识别全链路训练方案 | 算法工程师 |
| [03-deployment.md](./03-deployment.md) | 企业级 HA 部署、边缘推理、CI/CD、安全设计 | 运维、DevOps |
| [04-operations-optimization.md](./04-operations-optimization.md) | 生产监控、告警规则、持续调优、SLA 与故障响应 | 运维、算法工程师 |

## 四大核心能力 × 六层算法

```
视频监控 / 无人机航飞 / 业务系统数据
              ↓
  ┌───────────────────────────────────────────┐
  │  Layer 1：人体识别（Human Detection）       │  YOLOv8 / Faster R-CNN
  │  Layer 2：人体跟踪（Human Tracking）        │  ByteTrack / DeepSORT
  │  Layer 3：区域聚集预警（Crowd Aggregation） │  CSRNet + DBSCAN
  │  Layer 4：渔船识别（Vessel Detection）     │  YOLOv8 多类别
  │  Layer 5：渔具识别（Gear Detection）       │  YOLOv8 + SAM
  │  Layer 6：捕捞行为综合研判（Behavior）     │  时序规则引擎 + LSTM
  └───────────────────────────────────────────┘
              ↓
   监管平台 / 执法告警 / 可视化大屏
```

## 快速阅读路径

- **决策者**：`00-system-architecture.md` §1-§2 + `03-deployment.md` §7 成本
- **算法工程师**：`01-data-pipeline.md` → `02-model-training.md` → `04` §3 调优
- **运维/DevOps**：`03-deployment.md` → `04-operations-optimization.md`

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-04-29 | 初版，覆盖六层算法完整企业级方案 |
