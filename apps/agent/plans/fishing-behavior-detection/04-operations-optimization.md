# 04. 生产运营、监控告警与持续调优（企业级）

## 1. 全链路监控体系

### 1.1 Prometheus 指标全集

```python
# metrics.py — 捕捞行为识别系统专用指标
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# ═══ 计数器（Counter）═══

frames_processed_total = Counter(
    "fishing_cv_frames_processed_total",
    "处理帧总数",
    ["camera_id", "site_id", "mode"]   # mode: normal/alert/idle
)
persons_detected_total = Counter(
    "fishing_cv_persons_detected_total",
    "检测到的人体总数",
    ["camera_id", "person_class"]  # person / person_with_gear / person_on_boat
)
vessels_detected_total = Counter(
    "fishing_cv_vessels_detected_total",
    "检测到的渔船总数",
    ["camera_id", "vessel_class"]
)
gears_detected_total = Counter(
    "fishing_cv_gears_detected_total",
    "检测到的渔具总数",
    ["camera_id", "gear_class"]    # trawl_net / gill_net / purse_seine ...
)
behaviors_confirmed_total = Counter(
    "fishing_cv_behaviors_confirmed_total",
    "确认捕捞行为总数（CONFIRMED 级别）",
    ["camera_id", "decision_basis"]  # rule_engine / lstm_joint
)
behaviors_suspicious_total = Counter(
    "fishing_cv_behaviors_suspicious_total",
    "疑似捕捞行为总数（SUSPICIOUS）",
    ["camera_id"]
)
crowd_alerts_total = Counter(
    "fishing_cv_crowd_alerts_total",
    "人群聚集预警总数",
    ["camera_id", "alert_level"]   # LEVEL_1 / LEVEL_2 / LEVEL_3
)
false_positive_manual_total = Counter(
    "fishing_cv_false_positive_manual_total",
    "人工标记的误报数（FP）",
    ["camera_id", "behavior_type", "model_version"]
)
false_negative_manual_total = Counter(
    "fishing_cv_false_negative_manual_total",
    "人工标记的漏报数（FN）",
    ["camera_id", "model_version"]
)
alerts_sent_total = Counter(
    "fishing_cv_alerts_sent_total",
    "告警发送总数",
    ["alert_type", "channel", "status"]
)
id_switches_total = Counter(
    "fishing_cv_id_switches_total",
    "跟踪 ID 切换次数（越少越好）",
    ["camera_id"]
)
evidence_saved_total = Counter(
    "fishing_cv_evidence_saved_total",
    "证据文件保存总数（截图+视频片段）",
    ["camera_id", "behavior_type"]
)

# ═══ 直方图（Histogram）— 延迟分布 ═══

pipeline_latency_seconds = Histogram(
    "fishing_cv_pipeline_latency_seconds",
    "六层流水线各阶段推理延迟（Latency）",
    ["stage"],  # L1_detection / L2_tracking / L3_crowd /
                # L4_vessel / L5_gear / L6_behavior / total
    buckets=[0.010, 0.020, 0.050, 0.080, 0.120, 0.150,
             0.200, 0.300, 0.500, 0.700, 1.0, 2.0]
)
crowd_alert_e2e_seconds = Histogram(
    "fishing_cv_crowd_alert_e2e_seconds",
    "聚集预警端到端延迟（从检测到推送）",
    buckets=[5, 10, 15, 20, 30, 45, 60, 90, 120]
)
behavior_alert_e2e_seconds = Histogram(
    "fishing_cv_behavior_alert_e2e_seconds",
    "捕捞行为告警端到端延迟",
    buckets=[5, 10, 20, 30, 60, 120, 300]
)
evidence_upload_seconds = Histogram(
    "fishing_cv_evidence_upload_seconds",
    "证据文件上传延迟（含截图+视频）",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120]
)

# ═══ 仪表盘（Gauge）═══

active_tracks = Gauge(
    "fishing_cv_active_tracks",
    "当前活跃跟踪目标数",
    ["camera_id", "track_class"]
)
crowd_cluster_count = Gauge(
    "fishing_cv_crowd_cluster_count",
    "当前检测到的人群聚集簇数量",
    ["camera_id", "alert_level"]
)
gpu_memory_used_bytes = Gauge("fishing_cv_gpu_memory_used_bytes", "GPU 显存使用量")
gpu_utilization_percent = Gauge("fishing_cv_gpu_utilization_percent", "GPU 利用率（%）")
throughput_fps = Gauge("fishing_cv_throughput_fps", "推理吞吐量（FPS）", ["camera_id"])
fpr_realtime = Gauge("fishing_cv_fpr_realtime", "实时误报率（30min 滑动窗口）")
fnr_realtime = Gauge("fishing_cv_fnr_realtime", "实时漏报率（30min 滑动窗口）")
mota_estimate = Gauge("fishing_cv_mota_estimate", "实时跟踪 MOTA 估算值", ["camera_id"])
annotation_queue_depth = Gauge("fishing_cv_annotation_queue_depth", "Active Learning 标注队列深度")
evidence_queue_pending = Gauge("fishing_cv_evidence_queue_pending", "待上传证据文件数量")
model_version_info = Gauge(
    "fishing_cv_model_version_info", "当前模型版本",
    ["layer", "version", "precision"]
)

start_http_server(8090)
```

### 1.2 Grafana 看板设计（六层专用）

#### 看板1：捕捞监管总览（管理层，5 分钟刷新）

```
行1：今日核心 KPI（数字卡片）
  确认捕捞事件 N 次 | 疑似事件 N 次 | 聚集预警 N 次
  告警误报率（FPR）X.X% | 告警漏报率（FNR）X.X%

行2：各站点地图（GIS 嵌入）
  绿色：正常运行 | 黄色：延迟高 | 红色：断流/故障
  热力图：今日捕捞行为发生位置分布

行3：24h 行为趋势折线图（按站点分组）
  CONFIRMED / SUSPICIOUS / NORMAL 三线叠加

行4：渔船类型分布饼图 + 渔具类型分布饼图（今日）

行5：未处理告警列表（按时间倒序，执法人员实时查看）
```

#### 看板2：实时算法性能（算法工程师，1 分钟刷新）

```
行1：六层延迟分解热力图（各站点 × 各阶段）
  L1/L2/L3/L4/L5/L6 每层 P50/P95/P99
  目标线：六层合计 P95 ≤ 500ms（红线 700ms）

行2：各摄像头实时 FPS（Throughput）
  目标：≥ 5 FPS（人体跟踪最低要求）

行3：跟踪质量实时指标
  活跃轨迹数 | ID Switch 累计（今日）
  MOTA 估算（每 5 分钟抽样评估）

行4：GPU 显存（目标 ≤ 12GB）/ GPU 利用率（目标 ≥ 80%）

行5：Active Learning 队列深度（> 300 告警：标注资源不足）
```

#### 看板3：模型质量追踪（算法工程师，每日更新）

```
行1：生产 FPR / FNR 趋势（30 天滑动窗口）
  FPR 目标线 3%，警戒线 5%
  FNR 目标线 5%，警戒线 8%

行2：各层 Confusion Matrix 热力图（每日更新）
  L1 人体：TN/TP/FP/FN 分布
  L4 渔船：船型分类 Confusion Matrix
  L6 行为：CONFIRMED/SUSPICIOUS/NORMAL 混淆

行3：各渔具类别 mAP 趋势（关注长尾类别：拖网/围网）

行4：聚集预警准确率（Precision/Recall）趋势

行5：MOTA 趋势（跟踪质量月度变化）
```

#### 看板4：SLA 合规看板（月度，每日更新）

```
行1：系统可用性（月） — 目标 ≥ 99.5%
行2：聚集告警 E2E 延迟 P95 — 目标 ≤ 60s
行3：捕捞告警 E2E 延迟 P95 — 目标 ≤ 120s
行4：证据文件上传成功率 — 目标 ≥ 99.9%
行5：本月 P0/P1/P2 故障数与 MTTR
```

#### 看板5：证据与执法看板（执法人员，实时）

```
行1：今日确认事件列表（表格，带缩略图）
行2：证据文件状态（已上传/上传中/待上传）
行3：执法处理进度（已处理/未处理告警比例）
行4：高频违规区域热力图（按月统计）
行5：渔船 Re-ID 轨迹图（跨摄像头同一渔船的移动轨迹）
```

---

## 2. 告警规则（完整版）

### 2.1 基础设施告警（AlertManager）

```yaml
# prometheus/alert_rules/fishing_behavior.yml
groups:
  - name: fishing_behavior_infra
    rules:
      # 六层流水线延迟超标
      - alert: PipelineLatencyP95High
        expr: |
          histogram_quantile(0.95,
            rate(fishing_cv_pipeline_latency_seconds_bucket{stage="total"}[5m])
          ) > 0.50
        for: 3m
        labels: {severity: warning, team: ops}
        annotations:
          summary: "【{{ $labels.camera_id }}】六层流水线 P95 延迟 {{ $value | humanizeDuration }}，超 500ms 阈值"

      # P95 严重超标
      - alert: PipelineLatencyP95Critical
        expr: |
          histogram_quantile(0.95,
            rate(fishing_cv_pipeline_latency_seconds_bucket{stage="total"}[5m])
          ) > 0.70
        for: 2m
        labels: {severity: critical, team: ops}

      # 摄像头帧率过低（跟踪质量劣化）
      - alert: ThroughputTooLow
        expr: fishing_cv_throughput_fps < 4.0
        for: 2m
        labels: {severity: warning}
        annotations:
          summary: "【{{ $labels.camera_id }}】推理 FPS {{ $value }} < 4.0，人体跟踪质量可能劣化"

      # 摄像头断流
      - alert: CameraStreamLost
        expr: increase(fishing_cv_frames_processed_total[5m]) == 0
        for: 3m
        labels: {severity: critical, team: ops}
        annotations:
          summary: "【{{ $labels.camera_id }}】摄像头连续 3 分钟无帧，可能断流"

      # GPU 显存接近上限
      - alert: GPUMemoryCritical
        expr: fishing_cv_gpu_memory_used_bytes > 11.5 * 1024 * 1024 * 1024
        for: 2m
        labels: {severity: warning}
        annotations:
          summary: "GPU 显存 {{ $value | humanize1024 }}，接近 12GB 上限，有 OOM 风险"

      # 证据上传积压
      - alert: EvidenceUploadBacklog
        expr: fishing_cv_evidence_queue_pending > 20
        for: 5m
        labels: {severity: warning, team: ops}
        annotations:
          summary: "待上传证据文件 {{ $value }} 个，可能网络故障或 OSS 异常"

      # ID Switch 频率过高（跟踪质量下降）
      - alert: TrackingIDSwitchHigh
        expr: rate(fishing_cv_id_switches_total[1h]) * 3600 > 15
        for: 30m
        labels: {severity: warning, team: algorithm}
        annotations:
          summary: "【{{ $labels.camera_id }}】ID Switch 频率 {{ $value | humanize }} 次/h，超 15 次/h 警戒线，跟踪质量劣化"

  - name: fishing_behavior_model_quality
    rules:
      # 捕捞行为误报率过高（FPR）
      - alert: BehaviorFPRHigh
        expr: fishing_cv_fpr_realtime > 0.05
        for: 20m
        labels: {severity: warning, team: algorithm}
        annotations:
          summary: "捕捞行为误报率（FPR）{{ $value | humanizePercentage }}，超 5% 警戒线"
          description: "连续 20 分钟 FPR > 5%。可能原因：1）当前场景有与捕捞相似的合法作业；2）L6 LSTM 模型退化。建议触发人工抽检"

      # FPR 严重超标
      - alert: BehaviorFPRCritical
        expr: fishing_cv_fpr_realtime > 0.10
        for: 5m
        labels: {severity: critical, team: algorithm}
        annotations:
          summary: "捕捞行为误报率（FPR）{{ $value | humanizePercentage }}，严重异常，评估紧急回滚"

      # 漏报率过高（FNR）
      - alert: BehaviorFNRHigh
        expr: fishing_cv_fnr_realtime > 0.08
        for: 20m
        labels: {severity: warning, team: algorithm}
        annotations:
          summary: "捕捞行为漏报率（FNR）{{ $value | humanizePercentage }}，超 8% 警戒线"

      # 聚集告警延迟过高
      - alert: CrowdAlertLatencyHigh
        expr: |
          histogram_quantile(0.95,
            rate(fishing_cv_crowd_alert_e2e_seconds_bucket[10m])
          ) > 60
        for: 5m
        labels: {severity: warning}
        annotations:
          summary: "聚集告警 E2E 延迟 P95 = {{ $value }}s，超 60s 目标"

      # 标注队列积压过深
      - alert: AnnotationQueueDeep
        expr: fishing_cv_annotation_queue_depth > 300
        for: 30m
        labels: {severity: warning, team: algorithm}
        annotations:
          summary: "Active Learning 标注队列积压 {{ $value }} 条，需增加标注资源"
```

### 2.2 业务告警引擎

```python
# business_alert.py
from enum import Enum
from typing import Optional
import redis

class FishingAlertType(str, Enum):
    CONFIRMED_FISHING    = "confirmed_fishing"     # 确认捕捞
    SUSPICIOUS_FISHING   = "suspicious_fishing"    # 疑似捕捞（平台推送）
    CROWD_LEVEL3         = "crowd_level3"          # 高密度聚集（执法）
    CROWD_LEVEL2         = "crowd_level2"          # 中度聚集（预警）
    VESSEL_INTRUSION     = "vessel_intrusion"      # 渔船进入禁捕区
    ILLEGAL_GEAR         = "illegal_gear"          # 非法渔具（拖网/围网）
    NIGHT_ACTIVITY       = "night_activity"        # 夜间可疑活动
    REPEATED_INTRUSION   = "repeated_intrusion"    # 同一船只重复闯入

class FishingAlertEngine:
    DEDUP_WINDOWS = {
        FishingAlertType.CONFIRMED_FISHING:  300,   # 5 分钟去重
        FishingAlertType.SUSPICIOUS_FISHING: 600,   # 10 分钟去重
        FishingAlertType.CROWD_LEVEL3:       180,   # 3 分钟去重（高频聚集）
        FishingAlertType.VESSEL_INTRUSION:   300,
        FishingAlertType.NIGHT_ACTIVITY:     900,   # 15 分钟去重
    }

    CHANNEL_MATRIX = {
        # alert_type → channels（按告警级别分配渠道）
        FishingAlertType.CONFIRMED_FISHING:   ["wechat", "sms", "platform"],
        FishingAlertType.CROWD_LEVEL3:        ["wechat", "sms", "platform"],
        FishingAlertType.VESSEL_INTRUSION:    ["wechat", "sms", "platform"],
        FishingAlertType.SUSPICIOUS_FISHING:  ["platform", "wechat"],
        FishingAlertType.ILLEGAL_GEAR:        ["wechat", "platform"],
        FishingAlertType.CROWD_LEVEL2:        ["platform"],
        FishingAlertType.NIGHT_ACTIVITY:      ["platform", "wechat"],
        FishingAlertType.REPEATED_INTRUSION:  ["wechat", "sms", "platform"],
    }

    def __init__(self, redis_client: redis.Redis, db_session):
        self.redis = redis_client
        self.db = db_session

    def evaluate_and_send(self, event: dict) -> list[dict]:
        """
        根据事件内容评估需要发送的告警类型（可能触发多个）
        返回：已发送的告警列表
        """
        alerts_to_send = self._evaluate_alert_types(event)
        sent_alerts = []

        for alert_type in alerts_to_send:
            dedup_key = f"alert_dedup:{event['camera_id']}:{alert_type}:{event.get('vessel_id','unknown')}"
            window = self.DEDUP_WINDOWS.get(alert_type, 300)

            if self.redis.exists(dedup_key):
                continue   # 去重（Deduplication），跳过

            channels = self.CHANNEL_MATRIX.get(alert_type, ["platform"])
            success = self._dispatch_alert(event, alert_type, channels)

            if success:
                self.redis.setex(dedup_key, window, "1")
                self._record_to_db(event, alert_type, channels)
                sent_alerts.append({"type": alert_type, "channels": channels})

        return sent_alerts

    def _evaluate_alert_types(self, event: dict) -> list:
        """多维度评估触发的告警类型（可同时触发多种）"""
        types = []
        behavior = event.get("behavior_type")
        crowd_level = event.get("evidence", {}).get("crowd_level", "NORMAL")
        gear_types = event.get("evidence", {}).get("gear_types", [])
        is_night = event.get("is_nighttime", False)
        is_in_prohibited_zone = event.get("in_prohibited_zone", False)

        if behavior == "CONFIRMED":
            types.append(FishingAlertType.CONFIRMED_FISHING)

        elif behavior == "SUSPICIOUS":
            types.append(FishingAlertType.SUSPICIOUS_FISHING)

        if crowd_level == "LEVEL_3":
            types.append(FishingAlertType.CROWD_LEVEL3)
        elif crowd_level == "LEVEL_2":
            types.append(FishingAlertType.CROWD_LEVEL2)

        if is_in_prohibited_zone and event.get("evidence", {}).get("vessel_count", 0) > 0:
            types.append(FishingAlertType.VESSEL_INTRUSION)

        # 高危渔具（拖网/围网 → 生态破坏最严重）
        if any(g in gear_types for g in ["trawl_net", "purse_seine"]):
            types.append(FishingAlertType.ILLEGAL_GEAR)

        if is_night and behavior in ["CONFIRMED", "SUSPICIOUS"]:
            types.append(FishingAlertType.NIGHT_ACTIVITY)

        if self._is_repeated_intrusion(event):
            types.append(FishingAlertType.REPEATED_INTRUSION)

        return list(set(types))   # 去重

    def _is_repeated_intrusion(self, event: dict) -> bool:
        """检测同一渔船在 24h 内的重复闯入（≥ 3 次触发）"""
        vessel_key = f"vessel_intrusion_count:{event['camera_id']}:{event.get('vessel_track_id','unknown')}"
        count = self.redis.incr(vessel_key)
        if count == 1:
            self.redis.expire(vessel_key, 86400)   # 24h 计数窗口
        return count >= 3
```

---

## 3. 持续调优策略

### 3.1 数据飞轮（六层 Active Learning）

```python
class BehaviorActiveLearningSampler:
    """
    六层流水线的分层 Active Learning 采样策略
    各层独立采样，避免标注资源浪费在已收敛的层
    """

    SAMPLE_RULES = [
        # ─── L1 人体检测困难样本 ───
        {
            "layer": "L1_detection",
            "name": "low_conf_person",
            "condition": lambda e: any(
                0.40 <= p.get("confidence", 1.0) < 0.65
                for p in e.get("persons", [])
            ),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "bbox",
        },
        # ─── L2 跟踪 ID Switch 帧 ───
        {
            "layer": "L2_tracking",
            "name": "id_switch_frame",
            "condition": lambda e: e.get("id_switch_occurred", False),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "tracking",
            "note": "ID Switch 前后 3 帧一并采样",
        },
        # ─── L3 聚集漏报（现场确认聚集但系统未预警）───
        {
            "layer": "L3_crowd",
            "name": "crowd_miss",
            "condition": lambda e: (
                e.get("manual_crowd_report") and
                e.get("crowd_level") == "NORMAL"
            ),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "crowd_density",
        },
        # ─── L4 渔船低置信度 ───
        {
            "layer": "L4_vessel",
            "name": "low_conf_vessel",
            "condition": lambda e: any(
                v.get("confidence", 1.0) < 0.60
                for v in e.get("vessels", [])
            ),
            "priority": "P1",
            "rate": 1.0,
            "annotation_type": "bbox",
        },
        # ─── L5 渔具检测失败（系统未检测到但人工确认有渔具）───
        {
            "layer": "L5_gear",
            "name": "gear_miss",
            "condition": lambda e: (
                e.get("manual_gear_confirmed") and
                not e.get("gear_detected", False)
            ),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "bbox_polygon",
            "note": "渔具漏检是 FNR 的主要来源，优先级最高",
        },
        # ─── L6 行为研判误报（人工确认为正常行为）───
        {
            "layer": "L6_behavior",
            "name": "behavior_fp",
            "condition": lambda e: (
                e.get("behavior_type") == "CONFIRMED" and
                e.get("manual_label") == "NORMAL"
            ),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "behavior_sequence",
            "note": "误报样本用于 LSTM 负样本扩充，降低 FPR",
        },
        # ─── L6 行为漏报（人工确认为捕捞但系统未告警）───
        {
            "layer": "L6_behavior",
            "name": "behavior_fn",
            "condition": lambda e: (
                e.get("behavior_type") == "NORMAL" and
                e.get("manual_label") == "FISHING"
            ),
            "priority": "P0",
            "rate": 1.0,
            "annotation_type": "behavior_sequence",
            "note": "漏报样本用于 LSTM 正样本扩充，降低 FNR",
        },
        # ─── 随机多样性采样 ───
        {
            "layer": "all",
            "name": "random_diversity",
            "condition": lambda e: True,
            "priority": "P3",
            "rate": 0.005,   # 0.5% 随机采样
            "annotation_type": "multi",
        },
    ]
```

### 3.2 月度模型迭代 SOP（六层联动版）

```
═══ 月度模型迭代标准作业流程（SOP）— 捕捞行为识别系统 ═══

【第1周 Mon】数据汇总与分析
  □ 拉取上月 Active Learning 队列（各层分别统计）
  □ 检查各层困难样本数量：
      L1 人体：目标 ≥ 300 张
      L2 跟踪：目标 ≥ 20 段 ID Switch 视频
      L3 聚集：目标 ≥ 100 张密度图
      L4 渔船：目标 ≥ 200 张
      L5 渔具：目标 ≥ 200 张（重点关注长尾类：拖网/围网）
      L6 行为：目标 ≥ 50 段误报/漏报序列
  □ 分析上月 FPR/FNR 根因（哪层贡献最多）
  □ 确定本月重点优化层（资源集中投入）

【第1周 Tue-Thu】标注完成
  □ 分配标注任务（CVAT：L2跟踪；Label Studio：其余）
  □ 目标：72h 内完成全部标注（P0 样本优先）
  □ 标注 IoU 一致性验证（目标 ≥ 0.85）
  □ 更新 DVC 数据集版本

【第1周 Fri — 第2周 Tue】增量训练（各层独立进行）
  □ L1 人体：Fine-tuning 50 epoch（冻结骨干，lr0=0.0001）
  □ L3 CSRNet：Fine-tuning 80 epoch
  □ L4 渔船：Fine-tuning 60 epoch
  □ L5 渔具：Fine-tuning 80 epoch（渔具长尾，epoch 更多）
  □ L6 LSTM：增量训练 30 epoch（新误报/漏报序列）
  □ 各层通过 Gate 1 离线指标门控

【第2周 Wed-Thu】联合压测 + 量化
  □ 导出各层 TensorRT INT8 / FP16
  □ 六层流水线联合压测（600s，Jetson Orin NX）
  □ 通过 Gate 2 性能门控（P95 ≤ 500ms）

【第2周 Fri — 第3周 Fri】灰度观察（7天）
  □ 试点站点 1:1 对比（新旧模型并行）
  □ 每日统计：FPR / FNR / MOTA / 聚集 Precision / 延迟
  □ 通过 Gate 3 门控

【第4周 Mon】全量发布
  □ 滚动更新所有站点（每批 2 个，间隔 2h）
  □ 更新各层 Model Card
  □ 发布月度迭代报告（W&B 链接）
  □ 清空 Active Learning 队列（已处理样本标记为 done）

【第4周 Tue+】次月计划
  □ 根据本月 FPR/FNR 根因，确定次月重点采集场景
  □ 调整各层 SAMPLE_RULES 采样率（重点层加大采样）
```

### 3.3 针对性困难场景调优

#### 3.3.1 水面强反射（FP 来源之一）

```python
def suppress_water_reflection_fp(detections: list, frame: np.ndarray) -> list:
    """
    水面强反射时，波光可能被误检为人体（False Positive）
    策略：对检测框区域做纹理分析，排除无人体纹理的误报框
    """
    import skimage.feature

    filtered = []
    for det in detections:
        x1, y1, x2, y2 = map(int, det["bbox"])
        roi = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)

        if roi.size == 0:
            continue

        # LBP（局部二值模式）纹理分析
        # 人体区域纹理丰富（服装纹理），水面波光纹理均匀
        lbp = skimage.feature.local_binary_pattern(roi, P=8, R=1, method="uniform")
        lbp_var = lbp.var()

        # 低纹理方差 → 可能是水面反光（FP），降低置信度或过滤
        if lbp_var < 5.0 and det["confidence"] < 0.60:
            continue   # 过滤低置信度 + 低纹理的检测框

        # 宽高比校验（人体通常高 > 宽，波浪通常宽 > 高）
        h = y2 - y1
        w = x2 - x1
        if w > h * 1.5:   # 宽大于高 1.5 倍 → 疑似水面反光
            continue

        filtered.append(det)
    return filtered
```

#### 3.3.2 夜间跟踪质量提升

```python
class NighttimeTrackingEnhancer:
    """
    夜间目标跟踪的专项优化
    问题：夜间低光 → 检测置信度普遍偏低 → ByteTrack 关联失败 → ID Switch 增多
    解决：降低 ByteTrack 的 track_low_thresh，扩大轨迹保持时间
    """
    def __init__(self, tracker):
        self.tracker = tracker
        self.is_nighttime = False

    def adapt_to_nighttime(self, enable: bool):
        if enable == self.is_nighttime:
            return
        self.is_nighttime = enable
        if enable:
            # 夜间配置：更宽松的阈值，防止 ID Switch
            self.tracker.track_high_thresh = 0.45   # 降低（原 0.60）
            self.tracker.track_low_thresh = 0.05    # 降低（原 0.10）
            self.tracker.track_buffer = 50           # 扩大缓冲（原 30）
            self.tracker.match_thresh = 0.70         # 宽松匹配（原 0.80）
        else:
            # 恢复白天配置
            self.tracker.track_high_thresh = 0.60
            self.tracker.track_low_thresh = 0.10
            self.tracker.track_buffer = 30
            self.tracker.match_thresh = 0.80
```

#### 3.3.3 渔具长尾类别（拖网/围网）专项数据增强

```python
def augment_rare_gear(dataset_dir: str, target_class: str,
                       target_count: int = 500):
    """
    拖网/围网样本极少，使用 Copy-Paste 合成扩充
    策略：从现有样本中裁剪渔具 Crop，粘贴到水面背景图
    目标：trawl_net / purse_seine 各达到 500 张
    """
    gear_crops = load_gear_crops(dataset_dir, target_class)
    water_backgrounds = load_water_backgrounds(dataset_dir)

    for i in range(target_count):
        bg = random.choice(water_backgrounds).copy()
        crop = random.choice(gear_crops)

        # 随机变换（模拟不同水面状态下的渔具外观）
        scale = random.uniform(0.4, 1.2)
        h, w = int(crop.shape[0]*scale), int(crop.shape[1]*scale)
        crop = cv2.resize(crop, (w, h))

        # 随机位置（确保在水面区域内）
        x = random.randint(0, bg.shape[1] - w)
        y = random.randint(bg.shape[0]//2, bg.shape[0] - h)  # 水面下半部分

        # 泊松融合（边缘自然混合）
        result = poisson_blend(bg, crop, (x, y))

        # 保存及生成对应标注
        save_augmented_sample(result, target_class, [x, y, w, h], i)
```

#### 3.3.4 LSTM 模型防遗忘（Catastrophic Forgetting）

```python
class LSTMContinualTrainer:
    """
    LSTM 增量训练时防止灾难性遗忘（Catastrophic Forgetting）
    策略：EWC（Elastic Weight Consolidation）正则化
    保留重要参数的稳定性，同时学习新样本
    """
    def __init__(self, model, fisher_info: dict, lambda_ewc: float = 1000):
        self.model = model
        self.fisher_info = fisher_info   # Fisher 信息矩阵（衡量参数重要性）
        self.reference_params = {
            name: param.clone().detach()
            for name, param in model.named_parameters()
        }
        self.lambda_ewc = lambda_ewc

    def ewc_loss(self) -> torch.Tensor:
        """EWC 正则化损失：保持重要参数接近历史最优值"""
        ewc_penalty = 0
        for name, param in self.model.named_parameters():
            if name in self.fisher_info:
                fisher = self.fisher_info[name]
                ref_param = self.reference_params[name]
                ewc_penalty += (fisher * (param - ref_param) ** 2).sum()
        return self.lambda_ewc * ewc_penalty

    def compute_fisher_info(self, data_loader) -> dict:
        """计算 Fisher 信息矩阵（衡量各参数对旧任务的重要性）"""
        fisher = {name: torch.zeros_like(param)
                  for name, param in self.model.named_parameters()}
        self.model.eval()
        for sequences, labels in data_loader:
            self.model.zero_grad()
            outputs = self.model(sequences)
            loss = nn.functional.cross_entropy(outputs, labels)
            loss.backward()
            for name, param in self.model.named_parameters():
                if param.grad is not None:
                    fisher[name] += param.grad.data.pow(2)
        n = len(data_loader.dataset)
        return {name: f / n for name, f in fisher.items()}
```

---

## 4. SLA 全量定义与故障响应

### 4.1 完整 SLA 指标表

| 指标 | SLA 目标 | 警戒线 | 统计口径 | 违约响应 |
|------|---------|-------|---------|---------|
| 系统可用性（月） | ≥ 99.5% | 99.0% | 正常帧处理 / 总时间 | P0 处置 |
| 六层 P95 延迟 | ≤ 500ms | 700ms | Prometheus hist | 扩容/优化 |
| 推理 FPS | ≥ 5 FPS/路 | 4 FPS | Gauge 均值 | 告警+优化 |
| 人体检测 FNR | ≤ 5% | 10% | 人工抽检 | 触发 L1 迭代 |
| 人体检测 FPR | ≤ 3% | 6% | 人工抽检 | 调整阈值/迭代 |
| 跟踪 MOTA | ≥ 0.78 | 0.70 | 抽样评估 | 触发 L2 调优 |
| ID Switch | ≤ 5次/h | 15次/h | Counter | 检查遮挡场景 |
| 聚集预警 Precision | ≥ 90% | 85% | 人工核查 | 调整阈值 |
| 聚集预警 Recall | ≥ 95% | 88% | 人工核查 | 降低阈值/迭代 |
| 渔船检测 mAP50 | ≥ 0.93 | 0.87 | 测试集评估 | 触发 L4 迭代 |
| 渔具检测 mAP50 | ≥ 0.88 | 0.80 | 测试集评估 | 触发 L5 迭代 |
| 行为 F1-score | ≥ 0.90 | 0.85 | 测试集评估 | 触发 L6 迭代 |
| 行为 FPR（确认级） | **≤ 5%** | 8% | 人工核查 | 紧急评估 |
| 行为 FNR（确认级） | **≤ 5%** | 8% | 人工核查 | 紧急迭代 |
| 聚集告警 E2E 延迟 | ≤ 60s | 120s | Histogram | 检查推送链路 |
| 捕捞告警 E2E 延迟 | ≤ 120s | 300s | Histogram | — |
| 证据上传成功率 | ≥ 99.9% | 99.5% | Counter | 检查网络/OSS |

### 4.2 故障响应级别

| 级别 | 定义 | 响应 | 处置要点 |
|------|------|------|---------|
| **P0** | ≥ 2 站点完全断流 / 行为告警全部失效 | 30min 内 | 现场运维+备用节点接管；通知执法部门人工巡查 |
| **P1** | 单站点断流 > 30min / FPR 或 FNR > 15% | 2h 内 | 远程重启；超阈值触发紧急模型回滚 |
| **P2** | 跟踪 MOTA < 0.70 / 聚集预警 Recall < 0.80 | 24h 内 | 算法分析；调整超参数或触发专项迭代 |
| **P3** | 单层延迟偶发超标 / 个别渔具类别漏检增多 | 72h 内 | 记录工单；下次迭代修复 |

### 4.3 快速故障诊断手册

```bash
# ─── 诊断1：六层流水线延迟高 ───
# 定位延迟最高的层
curl -s http://localhost:8090/metrics | grep pipeline_latency | grep _sum
# 对比各层 _sum / _count 得到平均延迟

# 检查 GPU 状态
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu \
  --format=csv,nounits,noheader

# 检查帧队列积压
redis-cli XLEN frame_queue_l1_detection

# ─── 诊断2：MOTA 下降 / ID Switch 增多 ───
# 导出最近 30 分钟的跟踪日志（包含 ID Switch 帧）
python scripts/export_tracking_issues.py \
  --camera cam_shuiku_01 \
  --start "$(date -d '30 min ago' '+%Y-%m-%d %H:%M:%S')" \
  --output /tmp/tracking_debug/

# 分析 ID Switch 发生场景（是遮挡还是检测抖动）
python scripts/analyze_id_switches.py --input /tmp/tracking_debug/

# ─── 诊断3：渔具漏检率上升 ───
# 导出低置信度渔具样本
python scripts/export_low_conf.py \
  --layer L5_gear --threshold 0.50 \
  --output /tmp/gear_issues/

# 检查是否特定渔具类型（拖网/围网 长尾问题）
python scripts/analyze_gear_distribution.py --input /tmp/gear_issues/

# ─── 诊断4：行为误报率高（FPR > 5%）───
# 提取近期误报事件
python scripts/export_fp_events.py \
  --since "$(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S')" \
  --output /tmp/fp_events/

# 分析误报共同特征（特定时段/天气/场景）
python scripts/analyze_fp_pattern.py --input /tmp/fp_events/
# 常见原因：养殖工人集体作业（外观与捕捞相似）
#            → 临时提高 L6 LSTM 阈值 0.85（降低 FPR）

# ─── 模型快速回滚（< 5 分钟）───
# 查看可回滚版本（各层独立版本）
cat /opt/fishing-behavior/config/model_versions.yaml

# 执行指定层回滚
./scripts/rollback_layer.sh --layer L6_behavior --version v1.1
# 脚本：停 inference_worker → 切软链接 → 重启 → 健康检查

# 全层回滚（紧急）
./scripts/rollback_all.sh --version behavior-model-v1.1 --confirm
```

---

## 5. 专业词汇速查表（本系统全量）

| 中文 | 英文 / 缩写 | 本系统具体含义与指标 |
|------|-----------|-------------------|
| 数据集 | Dataset | 六套：人体检测/跟踪/聚集/渔船/渔具/行为序列 |
| 训练集 | Training Set | 70%，梯度更新 |
| 验证集 | Validation Set | 15%，超参调整依据（不用于测试） |
| 测试集 | Test Set | 15%，封存，仅用于最终报告 |
| 标注 | Annotation | BBox（L1/L4/L5）/ 跟踪ID（L2）/ 密度图（L3）/ 序列标签（L6）|
| 标签 | Label | L6 三类：NORMAL / SUSPICIOUS / CONFIRMED |
| 检测框 | Bounding Box | YOLO 格式，person/vessel/gear 各类别 |
| 掩码 | Mask | SAM 生成的渔具精细轮廓（证据存证用）|
| 多边形标注 | Polygon | 渔具精细标注（LabelMe），导出 COCO 格式 |
| 关键点 | Keypoint | 预留（未来：渔具入水/出水关键动作点）|
| 数据清洗 | Data Cleaning | Cleanlab 检测 Label Noise + 训练损失监控 |
| 数据增强 | Data Augmentation | 水面专项：波光/雨纹/水雾 + Copy-Paste 聚集合成 |
| 数据分布 | Data Distribution | JS 散度验证各 Split 的行为类别分布一致性 |
| 长尾数据 | Long-tail Data | 拖网/围网/FISHING 样本极少；使用 Copy-Paste 扩充 |
| 类别不平衡 | Class Imbalance | 捕捞:正常 ≈ 1:4；Focal Loss + WeightedSampler 处理 |
| 标签噪声 | Label Noise | Cleanlab + EWC 双重防控 |
| 预训练模型 | Pretrained Model | L1/L4/L5：COCO；L3 CSRNet：ImageNet；L6：随机初始化 |
| 微调 | Fine-tuning | 月度增量：冻结骨干，lr0×0.1，50-80 epoch |
| 迁移学习 | Transfer Learning | COCO→水面场景；三段式（冻结→解冻后段→全网络）|
| 训练轮数 | Epoch | L1:200 / L3:400 / L4:200 / L5:250 / L6:100 |
| 批大小 | Batch Size | 检测 16-32 / CSRNet 8 / LSTM 32 |
| 学习率 | Learning Rate | AdamW，余弦退火；CSRNet 专用 1e-5 |
| 优化器 | Optimizer | 统一 AdamW（L2 正则化权重 5e-4）|
| 损失函数 | Loss Function | 检测：CIoU+BCE+DFL；CSRNet：MSE；LSTM：Focal Loss+EWC |
| 反向传播 | Backpropagation | PyTorch autograd |
| 检查点 | Checkpoint | 每 10 epoch；best.pt 基于 val mAP/MAE/F1 |
| 过拟合 | Overfitting | 防控：Dropout(0.3)/正则化/数据增强/早停/EWC |
| 欠拟合 | Underfitting | 信号：train loss 不降；处置：加大模型/更多 epoch |
| 正则化 | Regularization | L2（weight_decay=5e-4）+ Dropout + EWC |
| 超参数调优 | Hyperparameter Tuning | Optuna，各层独立 40-50 次试验 |
| 图像分类 | Classification | L1 分类：person / person_with_gear；L4 船型分类 |
| 目标检测 | Object Detection | L1 YOLOv8m / L4 YOLOv8l / L5 YOLOv8m |
| 语义分割 | Semantic Segmentation | 预留（水域/禁捕区域精确划分）|
| 实例分割 | Instance Segmentation | 预留（多渔具同帧区分）|
| OCR | OCR | 预留（船名/船号识别辅助 Re-ID）|
| 目标跟踪 | Tracking | L2 ByteTrack，目标 MOTA ≥ 0.78 |
| 行为识别 | Action Recognition | L6 LSTM 时序识别，F1 ≥ 0.90 |
| 轨迹分析 | Trajectory Analysis | 船只/人体运动模式判断（stationary/meandering/directional）|
| 多目标跟踪 | Multi-object Tracking | ByteTrack，同时跟踪全场所有人体和船只 |
| 重识别 | Re-identification / ReID | StrongSORT + OSNet；跨摄像头同一渔船/人员关联 |
| 准确率 | Accuracy | 船型分类准确率目标 ≥ 90% |
| 精确率 | Precision | 聚集预警 ≥ 90%；行为研判 ≥ 0.90 |
| 召回率 | Recall | 聚集预警 ≥ 95%；行为研判 ≥ 0.90 |
| F1 分数 | F1-score | 捕捞行为目标 ≥ 0.90 |
| 平均精度均值 | mAP | L1 ≥ 0.92 / L4 ≥ 0.93 / L5 ≥ 0.88 |
| 交并比 | IoU | 标注一致性 ≥ 0.85；检测阈值 0.50 |
| 多目标跟踪精度 | MOTA | 目标 ≥ 0.78；警戒 0.70 |
| 平均绝对误差 | MAE | L3 CSRNet 人数计数，目标 ≤ 2 人 |
| 混淆矩阵 | Confusion Matrix | 每层每日更新，Grafana 热力图展示 |
| 误报 | False Positive (FP) | 非捕捞误判为捕捞；行为 FPR 目标 ≤ 5% |
| 漏报 | False Negative (FN) | 捕捞未被识别；行为 FNR 目标 ≤ 5% |
| 正确检出 | True Positive (TP) | 捕捞行为正确识别 |
| 正确排除 | True Negative (TN) | 正常行为正确排除 |
| 每秒帧数 | FPS (Throughput) | 人体跟踪最低需要 5 FPS；目标 ≥ 15 FPS |
| 延迟 | Latency | 六层 P95 ≤ 500ms；聚集告警 E2E ≤ 60s |
| 吞吐量 | Throughput | 单节点六层并行，最大并发处理能力 |
| ONNX | ONNX | L2 ByteTrack / L6 LSTM 导出，CPU 部署 |
| TensorRT | TensorRT | L1/L3/L4/L5 INT8/FP16 加速 |
| 量化 | Quantization | L1/L4/L5 INT8（3.6× 加速），L3 FP16 |
| 剪枝 | Pruning | L4 渔船 YOLOv8l 剪枝 20%（大模型减负）|
| 知识蒸馏 | Knowledge Distillation | L4：Teacher YOLOv8l → Student YOLOv8s；Feature-level KD |
| FP32 | FP32 | 训练基准，不用于边缘推理 |
| FP16 | FP16 | L3 CSRNet 云端推理；L4 渔船云端精细化 |
| INT8 | INT8 | L1/L4/L5 边缘主力；mAP 损失控制 ≤ 1.5% |
| 模型压缩 | Model Compression | 剪枝20% + Feature KD + INT8，三阶段联合 |
| 推理 | Inference | 边缘 TRT INT8（L1/L4/L5）+ ONNX CPU（L2/L6）|
| 边缘部署 | Edge Deployment | Jetson Orin NX，六层 docker compose，断网 72h 保障 |
| 实时推理 | Real-time Inference | 六层 P95 ≤ 500ms，≥ 5 FPS，满足执法实时响应需求 |
| 灾难性遗忘 | Catastrophic Forgetting | L6 LSTM 增量训练用 EWC 正则化防止 |
| 弹性权重巩固 | EWC | Fisher 信息矩阵衡量参数重要性，λ=1000 |
| 注意力机制 | Attention | L6 LSTM 后加 Multi-head Attention，增强时序关键帧权重 |
