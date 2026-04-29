# 04. 生产运营、监控告警与持续调优（企业级）

## 1. 全链路监控体系

### 1.1 监控架构（Prometheus + Grafana + Loki）

```
边缘节点                            云端监控中心
┌────────────────────┐            ┌──────────────────────────────────┐
│  推理服务           │            │  Prometheus（指标采集+存储）      │
│  /metrics:8088     │──Scrape──▶│  Grafana（多看板可视化）          │
│                    │            │  AlertManager（多渠道告警路由）   │
│  Fluentd 日志采集  │──Push───▶ │  Loki（日志聚合+查询）           │
│  node-exporter     │            │  Jaeger（全链路 Trace）          │
└────────────────────┘            └──────────────────────────────────┘
```

### 1.2 完整 Prometheus 指标定义

```python
# metrics.py — 推理服务暴露的所有 Prometheus 指标
from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server

# ═══ 计数器（Counter）— 只增不减 ═══

frames_processed_total = Counter(
    "aquatic_cv_frames_processed_total",
    "处理帧总数",
    ["camera_id", "site_id", "resolution"]
)
vehicles_detected_total = Counter(
    "aquatic_cv_vehicles_detected_total",
    "检测到的车辆数",
    ["camera_id", "is_aquatic", "cls_method"]   # cls_method: single/ensemble/temporal
)
plates_recognized_total = Counter(
    "aquatic_cv_plates_recognized_total",
    "车牌识别成功数（置信度 ≥ 阈值）",
    ["camera_id", "province"]                    # 按省份统计
)
plates_low_conf_total = Counter(
    "aquatic_cv_plates_low_conf_total",
    "低置信度车牌数（< 0.80，进入 Active Learning 队列）",
    ["camera_id"]
)
ocr_key_hits_total = Counter(
    "aquatic_cv_ocr_key_hits_total",
    "OCR 关键词命中次数（'渔''水产'等）",
    ["camera_id", "keyword_category"]
)
false_positive_manual_total = Counter(
    "aquatic_cv_false_positive_manual_total",
    "人工标记的误报总数（False Positive）",
    ["camera_id", "model_version"]
)
false_negative_manual_total = Counter(
    "aquatic_cv_false_negative_manual_total",
    "人工标记的漏报总数（False Negative）",
    ["camera_id", "model_version"]
)
alerts_sent_total = Counter(
    "aquatic_cv_alerts_sent_total",
    "告警发送总数",
    ["alert_type", "channel", "status"]
)
stream_reconnect_total = Counter(
    "aquatic_cv_stream_reconnect_total",
    "摄像头重连次数",
    ["camera_id"]
)

# ═══ 直方图（Histogram）— 延迟分布 ═══

inference_latency_seconds = Histogram(
    "aquatic_cv_inference_latency_seconds",
    "各阶段推理延迟（Latency）分布",
    ["stage"],   # preprocess / detection / classification / lpr / ocr / total
    buckets=[0.005, 0.010, 0.020, 0.050, 0.080, 0.100, 0.150, 0.200, 0.300, 0.500, 1.0]
    # 关键桶：0.150（P95目标）、0.200（P99目标）
)
alert_latency_seconds = Histogram(
    "aquatic_cv_alert_latency_seconds",
    "从识别到告警推送的端到端延迟",
    buckets=[5, 10, 15, 20, 30, 60, 120]
)
upload_latency_seconds = Histogram(
    "aquatic_cv_upload_latency_seconds",
    "截图上传 OSS 延迟",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# ═══ 仪表盘（Gauge）— 当前状态 ═══

frame_queue_depth = Gauge(
    "aquatic_cv_frame_queue_depth",
    "待推理帧队列深度（积压监控）",
    ["camera_id"]
)
gpu_memory_used_bytes = Gauge(
    "aquatic_cv_gpu_memory_used_bytes",
    "GPU 显存使用量"
)
gpu_utilization_percent = Gauge(
    "aquatic_cv_gpu_utilization_percent",
    "GPU 计算利用率（%）"
)
active_camera_count = Gauge(
    "aquatic_cv_active_cameras",
    "当前正常工作的摄像头数量",
    ["site_id"]
)
model_version_info = Gauge(
    "aquatic_cv_model_version_info",
    "当前运行的模型版本信息",
    ["model_type", "version", "precision"]   # precision: INT8/FP16
)
annotation_queue_depth = Gauge(
    "aquatic_cv_annotation_queue_depth",
    "Active Learning 标注队列深度（待人工复核）"
)
# ─── 实时业务指标（每5分钟重置）───
fpr_realtime = Gauge(
    "aquatic_cv_fpr_realtime",
    "实时误报率（False Positive Rate）— 5分钟滑动窗口"
)
throughput_fps = Gauge(
    "aquatic_cv_throughput_fps",
    "当前推理吞吐量（Throughput，FPS）",
    ["camera_id"]
)

# ═══ Summary — 精确分位数计算 ═══

inference_summary = Summary(
    "aquatic_cv_inference_summary",
    "推理延迟精确分位数（避免 Histogram 精度损失）",
    ["stage"]
)

# 启动指标服务
start_http_server(8088)
```

### 1.3 Grafana 看板设计（5 个看板）

#### 看板1：运营概览（管理层，5分钟刷新）

```
行1：核心 KPI 数字卡
     今日过车总数 | 水产车识别数 | 已告警数 | 告警误报率（FPR）

行2：各路口状态地图（绿=正常 / 黄=延迟高 / 红=断流）

行3：过去 24h 水产车通行量折线图（按路口分组）

行4：车牌识别成功率趋势（7天滚动均线）
     目标线：98%，警戒线：96%

行5：告警类型分布饼图（unknown_aquatic / plate_mismatch / etc.）
```

#### 看板2：实时性能（运维，1分钟刷新）

```
行1：各节点推理延迟（P50/P95/P99 热力图）
     ████ P95 ≤ 150ms（绿色目标线）
     ████ P99 ≤ 200ms（黄色警戒线）

行2：各路口 Throughput（FPS）实时折线图
     目标：≥ 8 FPS/路

行3：队列积压深度（frame_queue_depth）— > 50 时告警

行4：GPU 显存使用（目标：≤ 8GB）/ GPU 利用率（目标：≥ 80%）

行5：摄像头在线状态矩阵（在线/离线/重连中）
```

#### 看板3：模型质量（算法工程师，1小时刷新）

```
行1：生产 FPR / FNR 实时趋势（30天）
     FPR 目标线：≤ 3%，警戒线：5%
     FNR 目标线：≤ 4%，警戒线：7%

行2：低置信度车牌占比趋势（指示模型退化）
     > 5% 则提示模型需更新

行3：各类别 Confusion Matrix 热力图（每日更新）

行4：Active Learning 标注队列深度趋势
     （积压过多 → 标注资源不足预警）

行5：各省份车牌识别准确率对比（柱状图）
     重点关注粤/闽/桂（核心区域）
```

#### 看板4：SLA 看板（月度，每日更新）

```
行1：系统可用性（月滑动）— 目标 99.5%
     可用性 = 正常处理时间 / 总时间

行2：告警延迟分布（P50/P95/P99）— 目标 P95 ≤ 30s

行3：数据上报延迟分布 — 目标 P95 ≤ 5s

行4：模型版本分布（各版本在各节点的占比）

行5：本月 P0/P1/P2/P3 故障统计与 MTTR
```

#### 看板5：数据飞轮（每周更新）

```
行1：本周新增标注样本数 / 本月累计
行2：各类困难样本分布（低置信度分类/车牌/OCR）
行3：模型迭代历史（版本 × mAP 折线图，含 FPR/FNR）
行4：训练集各类别数量变化趋势（数据增长曲线）
```

---

## 2. 告警规则（完整版）

### 2.1 基础设施告警

```yaml
# prometheus/alert_rules/infrastructure.yml
groups:
  - name: infrastructure
    rules:
      # 推理延迟 P95 超阈值（核心告警）
      - alert: InferenceLatencyP95High
        expr: |
          histogram_quantile(0.95,
            rate(aquatic_cv_inference_latency_seconds_bucket{stage="total"}[5m])
          ) > 0.15
        for: 3m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "【{{ $labels.camera_id }}】推理延迟 P95 = {{ $value | humanizeDuration }}，超过 150ms 阈值"
          description: "检查 GPU 利用率（目标 ≥80%）和队列积压（frame_queue_depth）"

      # 推理延迟 P95 严重超阈值
      - alert: InferenceLatencyP95Critical
        expr: |
          histogram_quantile(0.95,
            rate(aquatic_cv_inference_latency_seconds_bucket{stage="total"}[5m])
          ) > 0.25
        for: 2m
        labels:
          severity: critical
          team: ops
        annotations:
          summary: "【{{ $labels.camera_id }}】推理延迟 P95 = {{ $value | humanizeDuration }}，严重超标！"

      # 摄像头断流
      - alert: CameraStreamLost
        expr: increase(aquatic_cv_frames_processed_total[5m]) == 0
        for: 3m
        labels:
          severity: critical
          team: ops
        annotations:
          summary: "【{{ $labels.camera_id }}】摄像头连续 3 分钟无帧处理，可能断流"

      # GPU 显存超阈值
      - alert: GPUMemoryHigh
        expr: aquatic_cv_gpu_memory_used_bytes > 7.5 * 1024 * 1024 * 1024
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "GPU 显存使用 {{ $value | humanize1024 }}，接近 8GB 上限"

      # 帧队列积压
      - alert: FrameQueueBacklog
        expr: aquatic_cv_frame_queue_depth > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "【{{ $labels.camera_id }}】帧队列积压 {{ $value }} 帧，推理能力不足"

      # 节点离线
      - alert: EdgeNodeDown
        expr: up{job="edge_node"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "边缘节点 {{ $labels.instance }} 离线"

      # Active Learning 队列过深（标注资源不足预警）
      - alert: AnnotationQueueDeep
        expr: aquatic_cv_annotation_queue_depth > 500
        for: 10m
        labels:
          severity: warning
          team: algorithm
        annotations:
          summary: "标注队列积压 {{ $value }} 条，需增加标注资源"
```

### 2.2 模型质量告警

```yaml
# prometheus/alert_rules/model_quality.yml
groups:
  - name: model_quality
    rules:
      # 实时 FPR 超 5% 警戒线
      - alert: FalsePositiveRateHigh
        expr: aquatic_cv_fpr_realtime > 0.05
        for: 15m
        labels:
          severity: warning
          team: algorithm
        annotations:
          summary: "水产车误报率（FPR）= {{ $value | humanizePercentage }}，超过 5% 警戒线"
          description: "连续 15 分钟 FPR > 5%，可能原因：1）当前路口有外形相似的油罐车；2）模型退化。触发人工抽检。"

      # FPR 超 10%（严重，可能模型损坏）
      - alert: FalsePositiveRateCritical
        expr: aquatic_cv_fpr_realtime > 0.10
        for: 5m
        labels:
          severity: critical
          team: algorithm
        annotations:
          summary: "水产车误报率（FPR）= {{ $value | humanizePercentage }}，严重异常，触发紧急回滚评估"

      # 低置信度车牌占比升高（模型退化早期预警）
      - alert: LicensePlateQualityDegraded
        expr: |
          rate(aquatic_cv_plates_low_conf_total[1h])
          / rate(aquatic_cv_plates_recognized_total[1h]) > 0.08
        for: 30m
        labels:
          severity: warning
          team: algorithm
        annotations:
          summary: "低置信度车牌占比 {{ $value | humanizePercentage }} > 8%，模型可能退化"
          description: "可能原因：夜间/雨天场景增多，当前模型在此场景训练不足"

      # 吞吐量下降（Throughput 低于目标）
      - alert: ThroughputLow
        expr: aquatic_cv_throughput_fps < 6
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "【{{ $labels.camera_id }}】推理吞吐量 {{ $value }} FPS < 6 FPS 警戒线（目标 8 FPS）"
```

### 2.3 业务告警规则

```python
# alert_engine.py — 业务告警引擎
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import redis
import json
import time

class AlertType(str, Enum):
    UNKNOWN_AQUATIC  = "unknown_aquatic"   # 水产车但车牌不在白名单
    PLATE_MISMATCH   = "plate_mismatch"    # 车牌与预期不符
    NO_PERMIT        = "no_permit"         # 无捕捞许可证
    PERMIT_EXPIRED   = "permit_expired"    # 证件过期
    FREQUENT_ENTRY   = "frequent_entry"    # 24h 内同一车牌过车 > 阈值
    SUSPICIOUS_TEXT  = "suspicious_text"   # 车身文字可疑（黑名单关键词）

@dataclass
class AlertDecision:
    should_alert: bool
    alert_type: Optional[AlertType]
    severity: str  # high / medium / low
    channels: list[str]
    reason: str

class BusinessAlertEngine:
    def __init__(self, redis_client: redis.Redis, db_session):
        self.redis = redis_client
        self.db = db_session

        # 告警策略配置
        self.FREQUENT_ENTRY_THRESHOLD = 8     # 24h 内同一车牌过车 > 8 次则告警
        self.DEDUP_COOLDOWN_SECONDS = 300      # 5 分钟内同类告警去重

    def evaluate(self, event: dict) -> AlertDecision:
        plate = event.get("license_plate")
        is_aquatic = event.get("is_aquatic_vehicle", False)
        key_texts = event.get("key_texts", [])

        if not is_aquatic:
            return AlertDecision(False, None, "", [], "非水产车，无需告警")

        # ─── 规则1：车牌不在白名单（最高优先级）───
        if plate and not self._is_in_whitelist(plate, event["camera_id"]):
            return AlertDecision(
                should_alert=True,
                alert_type=AlertType.UNKNOWN_AQUATIC,
                severity="high",
                channels=["wechat", "sms"],
                reason=f"水产车牌 {plate} 不在合规白名单中"
            )

        # ─── 规则2：白名单车辆但证件过期 ───
        if plate:
            permit_status = self._check_permit(plate)
            if permit_status == "expired":
                return AlertDecision(True, AlertType.PERMIT_EXPIRED, "medium",
                                     ["platform", "wechat"], "证件已过期")
            elif permit_status == "no_permit":
                return AlertDecision(True, AlertType.NO_PERMIT, "high",
                                     ["wechat", "sms"], "无捕捞许可证")

        # ─── 规则3：过车频次异常 ───
        entry_count = self._get_entry_count_24h(plate, event["camera_id"])
        if entry_count > self.FREQUENT_ENTRY_THRESHOLD:
            return AlertDecision(True, AlertType.FREQUENT_ENTRY, "medium",
                                 ["platform"], f"24h 内过车 {entry_count} 次（阈值 {self.FREQUENT_ENTRY_THRESHOLD}）")

        # ─── 规则4：车身可疑文字（黑名单） ───
        BLACKLIST_KEYWORDS = ["禁止运输", "非法", "无证"]
        for text_item in key_texts:
            if any(kw in text_item["text"] for kw in BLACKLIST_KEYWORDS):
                return AlertDecision(True, AlertType.SUSPICIOUS_TEXT, "high",
                                     ["wechat", "sms"], f"车身发现可疑文字: {text_item['text']}")

        return AlertDecision(False, None, "", [], "合规车辆，无需告警")

    def send_alert(self, event: dict, decision: AlertDecision) -> bool:
        """发送告警，内置去重（Deduplication）"""
        dedup_key = f"alert_dedup:{event['camera_id']}:{event.get('license_plate','unknown')}:{decision.alert_type}"
        if self.redis.exists(dedup_key):
            return False  # 5 分钟内已发过，跳过

        success = self._dispatch(event, decision)
        if success:
            self.redis.setex(dedup_key, self.DEDUP_COOLDOWN_SECONDS, "1")
            self._record_alert(event, decision)

        return success

    def _dispatch(self, event: dict, decision: AlertDecision) -> bool:
        """多渠道分发"""
        results = []
        for channel in decision.channels:
            try:
                if channel == "wechat":
                    results.append(self._send_wechat(event, decision))
                elif channel == "sms":
                    results.append(self._send_sms(event, decision))
                elif channel == "platform":
                    results.append(self._send_platform(event, decision))
            except Exception as e:
                # 单渠道失败不影响其他渠道
                results.append(False)
        return any(results)  # 至少一个渠道成功即为已发送
```

---

## 3. 持续调优策略

### 3.1 数据飞轮（Active Learning 完整流程）

```
生产推理
  ↓
低置信度样本筛选
  ↓ （每日定时任务）
标注队列（Label Studio）
  ↓ （人工复核，目标：48h 完成）
新增训练数据（DVC 版本化）
  ↓ （每月首周触发）
增量 Fine-tuning（冻结骨干层）
  ↓
三层 Gate 门控
  ↓
模型版本发布
  ↓ 回到生产推理（闭环）
```

```python
# active_learning_sampler.py
class ActiveLearningSampler:
    """从推理结果中采样困难样本，推送到标注队列"""

    # 采样规则（按优先级排序）
    SAMPLE_RULES = [
        {
            "name": "low_conf_classification",   # 分类不确定（FP/FN 主要来源）
            "condition": lambda e: 0.50 <= e.get("cls_confidence", 1.0) < 0.75,
            "priority": "P0",
            "sample_rate": 1.0,  # 100% 采样
        },
        {
            "name": "low_conf_lpr",               # 低置信度车牌
            "condition": lambda e: (e.get("lp_confidence") or 1.0) < 0.80,
            "priority": "P1",
            "sample_rate": 1.0,
        },
        {
            "name": "aquatic_without_mark",        # 被分类为水产车但无关键文字
            "condition": lambda e: e.get("is_aquatic_vehicle") and not e.get("has_aquatic_mark"),
            "priority": "P1",
            "sample_rate": 0.8,
        },
        {
            "name": "nighttime_aquatic",           # 夜间水产车（困难场景）
            "condition": lambda e: e.get("is_nighttime") and e.get("is_aquatic_vehicle"),
            "priority": "P2",
            "sample_rate": 0.5,
        },
        {
            "name": "random_diversity",            # 随机采样保持数据多样性
            "condition": lambda e: True,
            "priority": "P3",
            "sample_rate": 0.01,  # 1% 随机采样
        },
    ]

    def evaluate(self, event: dict) -> tuple[bool, str, str]:
        """返回 (should_sample, priority, rule_name)"""
        import random
        for rule in self.SAMPLE_RULES:
            if rule["condition"](event):
                if random.random() < rule["sample_rate"]:
                    return True, rule["priority"], rule["name"]
        return False, "", ""

    def push_to_label_studio(self, event: dict, priority: str, rule_name: str):
        """推送到 Label Studio 标注队列"""
        task = {
            "data": {
                "image": event["snapshot_url"],
                "meta": {
                    "camera_id": event["camera_id"],
                    "timestamp": event["timestamp"],
                    "cls_confidence": event.get("cls_confidence"),
                    "lp_confidence": event.get("lp_confidence"),
                    "sample_rule": rule_name,
                    "priority": priority,
                }
            }
        }
        # 调用 Label Studio API
        self._label_studio_import(task, project_id=self._get_project_id(rule_name))
```

### 3.2 月度模型迭代 SOP

```
═══ 月度模型迭代标准作业流程（SOP）═══

【第1周 Mon-Tue】数据汇总
  □ 统计上月 Active Learning 采样数量（目标 ≥ 500 张困难样本）
  □ 导出低置信度样本（Priority P0/P1）至标注工具
  □ 人工复核并完成标注（目标：48h 内完成）
  □ 更新 DVC 数据集版本（v{month}.{minor}）
  □ 运行数据分布验证（JS 散度 < 0.05）

【第1周 Wed-Thu】增量训练
  □ 触发 Fine-tuning（冻结骨干前10层，lr0=0.0001）
  □ 训练 60 个 Epoch（早停 patience=15）
  □ 与上版本模型对比 mAP / FPR / FNR
  □ 通过 Gate 1 门控

【第1周 Fri】性能压测
  □ 导出 TensorRT INT8
  □ Jetson 压测 600s
  □ 通过 Gate 2 门控

【第2周 Mon-Sun】灰度观察
  □ 在试点路口 1:1 对比运行（新旧模型并行）
  □ 每日统计：FPR / FNR / 延迟 / 可用性
  □ 通过 Gate 3 门控（连续 7 天达标）

【第3周 Mon】全量发布
  □ 滚动更新所有边缘节点（每批 3 个，间隔 30min）
  □ 更新模型卡（Model Card）
  □ 发布月度训练报告（W&B 共享链接）
  □ 更新 Grafana 模型版本看板

【第3周 Tue+】下月数据采集
  □ 根据本月 FPR/FNR 分析，确定下月重点采集场景
  □ 更新 SAMPLE_RULES 中各规则的采样率
```

### 3.3 针对性困难场景调优

#### 3.3.1 夜间识别优化

```python
def enhance_nighttime_frame(frame: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    自动检测夜间图像并增强，提升暗光下的 Recall
    目标：夜间场景 vehicle_aquatic Recall ≥ 0.90（目前约 0.87）
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = gray.mean()

    if mean_brightness >= 60:
        return frame, False  # 非夜间，不处理

    # CLAHE 对比度自适应增强
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    clip_limit = max(2.0, 8.0 - mean_brightness / 10)  # 越暗 clip_limit 越大
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # 非局部均值去噪（NLM，针对低光噪声）
    h_luminance = max(5, int(15 - mean_brightness / 6))  # 亮度越低去噪力度越强
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, h_luminance, h_luminance, 7, 21)

    return denoised, True

# 训练时也需要对应的夜间增强 Augmentation（让模型学会 CLAHE 前后的图像）
nighttime_aug = A.Compose([
    A.RandomBrightnessContrast(brightness_limit=(-0.5, -0.2), p=1.0),  # 模拟低光
    A.GaussNoise(var_limit=(20, 80), p=0.8),    # 模拟传感器噪声
    A.CLAHE(clip_limit=4.0, p=0.5),             # 模拟增强后效果（数据增强）
])
```

#### 3.3.2 油罐车 False Positive 抑制

油罐车是最主要的 False Positive 来源（外形圆柱与水产车相似）：

```python
# 专项抑制策略：在分类器后加形状分析模块
class TankerSuppressor:
    """
    油罐车特征检测：圆柱形但有"梯形扶梯"和"管道接口"特征
    通过简单的几何分析辅助降低 FPR
    """
    TANKER_INDICATORS = [
        "危险品",  "危化品", "易燃", "LPG", "LNG",
        "石油", "柴油", "化工",
    ]

    def is_likely_tanker(self, cls_conf: float, ocr_texts: list) -> bool:
        """基于 OCR 文字辅助判断是否为油罐车（False Positive）"""
        for text_item in ocr_texts:
            if any(kw in text_item["text"] for kw in self.TANKER_INDICATORS):
                return True
        return False

    def adjust_confidence(self, cls_conf: float, is_likely_tanker: bool) -> float:
        """调整置信度（降低疑似油罐车的得分）"""
        if is_likely_tanker:
            return cls_conf * 0.4  # 大幅降低，通常会降至阈值以下
        return cls_conf
```

#### 3.3.3 低分辨率车牌超分辨率

```python
import onnxruntime as ort

class PlateEnhancer:
    """
    2× 超分辨率（ESRGAN-lite，ONNX Runtime），针对：
    - 远距离摄像头（车牌宽 < 80px）
    - 夜间低光低对比度车牌
    目标：将低分辨率车牌的 Character Accuracy 从 88% 提升至 ≥ 95%
    """
    MIN_PLATE_WIDTH = 80   # 低于此宽度触发超分

    def __init__(self, model_path: str = "models/esrgan_lite.onnx"):
        self.session = ort.InferenceSession(
            model_path,
            providers=["TensorrtExecutionProvider", "CUDAExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    def enhance(self, plate_crop: np.ndarray) -> np.ndarray:
        h, w = plate_crop.shape[:2]
        if w >= self.MIN_PLATE_WIDTH:
            return plate_crop

        # 归一化 + 推理
        input_tensor = plate_crop.astype(np.float32) / 255.0
        input_tensor = input_tensor.transpose(2, 0, 1)[np.newaxis]
        output = self.session.run(None, {self.input_name: input_tensor})[0]

        # 反归一化
        enhanced = (output[0].transpose(1, 2, 0) * 255).clip(0, 255).astype(np.uint8)
        return enhanced
```

#### 3.3.4 俯视角（无人机）车牌矫正

```python
def rectify_overhead_plate(plate_crop: np.ndarray, pitch_angle: float) -> np.ndarray:
    """
    无人机俯视角透视矫正
    pitch_angle: 无人机俯仰角（度），正值为俯视
    目标：将俯视变形的车牌矫正为近似正视图，提升 Plate Accuracy 15%
    """
    if abs(pitch_angle) < 10:
        return plate_crop  # 角度小，不需矫正

    h, w = plate_crop.shape[:2]

    # 梯形透视矫正（俯视时近端变宽）
    shrink = min(0.4, pitch_angle / 90 * 0.6)
    src_pts = np.float32([
        [w * shrink, 0],          # 左上（收缩）
        [w * (1-shrink), 0],      # 右上
        [w, h],                    # 右下（正常）
        [0, h],                    # 左下
    ])
    dst_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(plate_crop, M, (w, h), flags=cv2.INTER_CUBIC)
```

---

## 4. SLA 全量定义与故障响应

### 4.1 完整 SLA 指标

| 指标 | SLA 目标 | 警戒线 | 统计方式 | 违约响应 |
|------|---------|-------|---------|---------|
| 系统可用性（月） | ≥ 99.5% | 99.0% | 正常帧处理时间 / 总时间 | 触发 P0 处置 |
| 推理延迟 P95 | ≤ 150ms | 200ms | Prometheus histogram | 自动告警 + 扩容评估 |
| 推理延迟 P99 | ≤ 200ms | 300ms | Prometheus histogram | 自动告警 |
| 推理吞吐量（FPS） | ≥ 8 FPS/路 | 6 FPS | Gauge | 告警 + 队列优化 |
| 水产车 FPR | ≤ 3%（月） | 5% | 人工抽检统计 | 触发模型复查 |
| 水产车 FNR | ≤ 4%（月） | 7% | 人工抽检统计 | 触发紧急迭代 |
| 车牌识别准确率 | ≥ 98%（月） | 96% | 人工抽检统计 | 触发专项调优 |
| OCR 关键字召回率 | ≥ 90%（月） | 85% | 测试集评估 | 触发数据补充 |
| 告警推送延迟 P95 | ≤ 30s | 60s | Prometheus histogram | 检查推送渠道 |
| 数据上报延迟 P95 | ≤ 5s | 10s | Kafka lag 监控 | 扩容消费者 |
| 断网数据丢失率 | 0% (72h 内恢复) | — | 断点续传验证 | 扩大本地缓存 |

### 4.2 故障响应级别

| 级别 | 定义 | 响应时间 | 处置方式 |
|------|------|---------|---------|
| **P0（致命）** | ≥ 2 个路口全断流 或 云端 API 全不可用 | 30 分钟内响应 | 现场运维 + 远程协助；启动备用方案 |
| **P1（严重）** | 单路口断流 > 30 分钟 或 告警系统失效 | 2 小时内响应 | 远程诊断；自动重启失败时人工干预 |
| **P2（一般）** | 识别准确率下降 > 5% 或 延迟持续超标 | 24 小时内 | 算法工程师分析；触发数据采样与模型评估 |
| **P3（轻微）** | 延迟偶发升高 或 单摄像头质量下降 | 72 小时内 | 下次迭代修复；记录工单 |

### 4.3 故障快速诊断手册

```bash
# ─── 诊断1：推理延迟高 ───
# 检查 GPU 利用率和显存
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free \
  --format=csv,nounits,noheader

# 检查队列积压
redis-cli XLEN frame_queue

# 检查推理 Worker 日志（过去 5 分钟）
docker logs inference_worker --since 5m | grep -E "ERROR|WARN|latency"

# ─── 诊断2：摄像头断流 ───
# 测试 RTSP 连通性
ffprobe -v quiet -print_format json -show_streams \
  "rtsp://admin:pass@192.168.10.100:554/stream1"

# 检查 ZLMediaKit 活跃流
curl http://localhost:8080/index/api/getMediaList

# 重启拉流服务
docker restart stream_puller && sleep 10
./scripts/health_check.sh

# ─── 诊断3：车牌识别率突降 ───
# 导出过去 1h 低置信度样本（用于快速分析原因）
python scripts/export_low_conf.py \
  --type lpr \
  --start "$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')" \
  --threshold 0.80 \
  --output /tmp/debug_lpr_$(date +%Y%m%d%H%M)/

# 快速分析：看是特定角度/天气导致还是全局性问题
python scripts/analyze_failure_patterns.py \
  --input /tmp/debug_lpr_*/

# ─── 模型回滚（< 5 分钟）───
# 列出可回滚版本
ls -lt /opt/aquatic-cv/models/ | head -5

# 执行回滚
./scripts/rollback.sh --version v1.1 --confirm
# 脚本执行：停服务 → 切换软链接 → 启服务 → 健康检查

# ─── 验证恢复 ───
./scripts/health_check.sh --full
```

---

## 5. 数据治理与模型卡规范

### 5.1 数据生命周期策略

| 数据类型 | 边缘存储 | 云端存储 | 归档 | 删除 |
|---------|---------|---------|------|------|
| 原始视频流 | 3天（循环覆盖） | 不上传 | — | 自动 |
| 事件截图（含车辆）| 24h（传云后删）| 1年（OSS标准）| 1-3年冷归档 | 3年后删除 |
| 结构化事件记录 | SQLite缓存72h | 永久（加密）| — | 永不删除 |
| 标注数据集 | — | 永久（DVC版本化）| — | 永不删除 |
| 模型权重 | 最新2版本 | 永久 | — | 永不删除 |
| 推理日志 | 7天 | 30天（Loki）| — | 自动清理 |

### 5.2 Model Card 模板（每版生产模型必填）

```markdown
## 模型卡 — 水产运输车检测分类 v{版本号}

### 基本信息
- 模型类型: {YOLOv8m Detection + YOLOv8m-cls}
- 训练数据版本: {datasets/v1.2_20260601}
- 训练日期: {2026-06-05}
- 训练工程师: {姓名}

### 离线性能（封存 Test Set，一次性评估）

| 指标 | 值 | 目标 | 通过 |
|------|-----|------|------|
| mAP50（检测，全类）| 0.894 | ≥ 0.87 | ✅ |
| mAP50（vehicle_aquatic）| 0.921 | ≥ 0.90 | ✅ |
| FPR（分类，测试集） | 0.028 | ≤ 0.05 | ✅ |
| FNR（分类，测试集） | 0.041 | ≤ 0.07 | ✅ |
| F1-score（分类） | 0.963 | ≥ 0.915 | ✅ |
| 车牌完整准确率 | 0.983 | ≥ 0.96 | ✅ |
| OCR 关键字召回率 | 0.912 | ≥ 0.85 | ✅ |

### 推理性能（Jetson Orin NX 16GB，INT8）

| 阶段 | P50 | P95 | P99 |
|------|-----|-----|-----|
| 目标检测 | 42ms | 51ms | 62ms |
| 车辆分类 | 18ms | 24ms | 31ms |
| 车牌识别 | 21ms | 28ms | 35ms |
| 车身 OCR | 31ms | 42ms | 55ms |
| **端到端合计** | **115ms** | **148ms** | **189ms** |

### 已知局限与风险

| 场景 | 已知问题 | 风险等级 |
|------|---------|---------|
| 夜间无补光（亮度 < 30） | vehicle_aquatic Recall ≈ 0.87（低于目标 0.93） | 中 |
| 油罐车（外形相似） | FPR 在油罐车密集路口升至约 0.08 | 中 |
| 俯视角 > 60°（无人机高空） | 检测率下降约 18% | 高 |
| 暴雨/大雾 | 所有模型性能大幅下降，不建议依赖自动识别 | 高 |
| 车牌宽 < 60px（远景）| 字符准确率约 0.85，需超分辨率辅助 | 中 |

### 适用声明
本模型适用于：固定路口摄像头，货车类型，1080P 及以上分辨率，
正常天气（非暴雨/大雾），补光有效的夜间。
不适用于上述已知局限场景，使用时请结合人工审核。

### 灰度 Gate 3 结果（7天）
- FPR 均值: 0.024 ✅（目标 ≤ 0.05）
- FNR 均值: 0.038 ✅（目标 ≤ 0.07）
- P95 延迟: 142ms ✅（目标 ≤ 150ms）
- 可用性: 99.72% ✅（目标 ≥ 99.5%）
- P0 故障: 0 ✅

**结论：通过全量发布审核**
```

### 5.3 专业词汇速查表（本方案涉及的所有术语）

| 中文 | 英文 / 缩写 | 本方案中的具体含义 |
|------|-----------|----------------|
| 数据集 | Dataset | 按任务分：检测/分类/LPR/OCR 四套 |
| 训练集 | Training Set | 70%，用于梯度更新 |
| 验证集 | Validation Set | 15%，超参调整依据，不参与训练 |
| 测试集 | Test Set | 15%，封存，只用于最终性能报告 |
| 标注 | Annotation | BBox 标注（Label Studio）或 OCR 文字标注（PaddleLabel） |
| 标签 | Label | 类别 ID（0-5）或字符串（车牌号/车身文字） |
| 检测框 | Bounding Box | YOLO 格式：(cx,cy,w,h)，归一化坐标 |
| 掩码 | Mask | 语义分割使用，本方案目前未用（预留） |
| 多边形标注 | Polygon | OCR 文字区域用四边形 Polygon 标注 |
| 关键点 | Keypoint | 未启用（未来可用于车辆姿态估计） |
| 数据清洗 | Data Cleaning | 用 Cleanlab 检测 Label Noise，人工复核 |
| 数据增强 | Data Augmentation | Mosaic/Mixup/Copy-Paste/夜间增强等 19 种 |
| 数据分布 | Data Distribution | JS 散度验证 Train/Val/Test 分布一致性 |
| 长尾数据 | Long-tail Data | 特殊型号水产车极少，油罐车作为困难负样本 |
| 类别不平衡 | Class Imbalance | 正负样本比 2:3，使用 WeightedSampler 处理 |
| 标签噪声 | Label Noise | Cleanlab + 训练损失监控双重检测 |
| 预训练模型 | Pretrained Model | COCO 预训练 YOLOv8m，ImageNet 预训练分类器 |
| 微调 | Fine-tuning | 月度增量数据触发，冻结骨干10层，lr×0.1 |
| 迁移学习 | Transfer Learning | 三段式：冻结骨干→解冻后段→全网络 |
| 训练轮数 | Epoch | 检测 200ep / 分类 100ep / OCR 100ep |
| 批大小 | Batch Size | 检测 32 / 分类 64 / OCR 检测 8 / OCR 识别 128 |
| 学习率 | Learning Rate | AdamW，初始 0.001，余弦退火至 0.00001 |
| 优化器 | Optimizer | AdamW（主力），SGD（YOLOv8 默认可选） |
| 损失函数 | Loss Function | 检测：CIoU+BCE+DFL；OCR：CTC+SAR；蒸馏：KL散度 |
| 反向传播 | Backpropagation | PyTorch autograd 自动计算 |
| 检查点 | Checkpoint | 每 10 epoch 保存；best.pt 基于 val mAP |
| 过拟合 | Overfitting | 防控：Dropout/正则化/数据增强/早停 |
| 欠拟合 | Underfitting | 防控：增大模型容量/更多 epoch/减少正则 |
| 正则化 | Regularization | L2（weight_decay=0.0005）+ Dropout(0.2) |
| 超参数调优 | Hyperparameter Tuning | Optuna，50次试验，优化 vehicle_aquatic Recall |
| 图像分类 | Classification | YOLOv8m-cls 二分类（水产车/非水产车） |
| 目标检测 | Object Detection | YOLOv8m，6类 BBox 检测 |
| 语义分割 | Semantic Segmentation | 预留（未来车辆区域精确分割） |
| 实例分割 | Instance Segmentation | 预留 |
| 光学字符识别 | OCR | PaddleOCR PP-OCRv4（DB++ + SVTR） |
| 目标跟踪 | Tracking | ByteTrack（时序滤波辅助，5帧滑动窗口） |
| 行为识别 | Action Recognition | 预留（未来异常停车/徘徊检测） |
| 轨迹分析 | Trajectory Analysis | 无人机数据的车辆行驶路径分析 |
| 多目标跟踪 | Multi-object Tracking | ByteTrack，同时跟踪多辆水产车 |
| 重识别 | Re-identification / ReID | 基于车牌和车身特征的跨摄像头车辆关联 |
| 准确率 | Accuracy | 分类模型整体正确率（含 TP+TN）|
| 精确率 | Precision | TP/(TP+FP)，目标 ≥ 0.95 |
| 召回率 | Recall | TP/(TP+FN)，目标 ≥ 0.96 |
| F1 分数 | F1-score | 2×P×R/(P+R)，目标 ≥ 0.955 |
| 平均精度均值 | mAP | mAP@0.5 ≥ 0.92，mAP@0.5:0.95 ≥ 0.65 |
| 交并比 | IoU | BBox 标注一致性 ≥ 0.85；检测阈值 ≥ 0.50 |
| 混淆矩阵 | Confusion Matrix | 每日更新，展示在 Grafana 模型质量看板 |
| 误报 | False Positive（FP） | 非水产车被识别为水产车，目标 FPR ≤ 3% |
| 漏报 | False Negative（FN） | 水产车未被识别，目标 FNR ≤ 4% |
| 正确检出 | True Positive（TP） | 水产车正确识别 |
| 正确排除 | True Negative（TN） | 非水产车正确排除 |
| 每秒帧数 | FPS（Throughput） | 推理吞吐量目标 ≥ 8 FPS/路 |
| 延迟 | Latency | P95 ≤ 150ms（边缘端），P99 ≤ 200ms |
| 吞吐量 | Throughput | 单节点最大并发处理能力（帧/秒）|
| ONNX | ONNX | 跨平台推理格式，用于非 NVIDIA 设备降级 |
| TensorRT | TensorRT | NVIDIA 推理加速框架，边缘主力（INT8）|
| 量化 | Quantization | FP32→INT8（3.6× 加速，mAP 损失 ≤ 1%）|
| 剪枝 | Pruning | L1 通道剪枝，参数量减少 30% |
| 知识蒸馏 | Knowledge Distillation | Teacher(YOLOv8l)→Student(YOLOv8n)，KL 散度损失 |
| FP32 | FP32 | 32位浮点，训练基准，不用于边缘部署 |
| FP16 | FP16 | 16位浮点，云端主力，速度 1.8×，mAP 损失 0.2% |
| INT8 | INT8 | 8位整型，边缘主力，速度 3.6×，mAP 损失 1% |
| 模型压缩 | Model Compression | 剪枝30% + 蒸馏 + INT8 量化，三阶段联合压缩 |
| 推理 | Inference | 边缘 TRT INT8，云端 ONNX Runtime CUDA EP |
| 边缘部署 | Edge Deployment | Jetson Orin NX，docker compose，断网72h保障 |
| 实时推理 | Real-time Inference | P95 ≤ 150ms，≥ 8 FPS，满足路口实时监管需求 |
