# 03. 企业级高可用部署方案

## 1. 边缘站点部署架构

### 1.1 单站点硬件规格

| 设备 | 型号 | 数量 | 作用 |
|------|------|------|------|
| **主推理节点** | Jetson Orin NX 16GB（工业版） | 1 | 六层流水线实时推理 |
| **备推理节点** | Jetson Orin 8GB（工业版） | 1（核心站） | HA 热备，≤15s 接管 |
| 4K 星光摄像头 | 海康 DS-2CD6944G2-IZS | 2-4 路/站 | 水面全景，红外补光 |
| 双光谱摄像头 | 可见光 + 红外热成像融合 | 1 路/站 | 夜间渔船检测强化 |
| 4G/5G 工业路由 | 双卡双链路 | 1 | 主/备网络自动切换 |
| UPS 电源 | 2KVA，8h 续航 | 1 | 断电保障 |
| 防水工业机箱 | IP67，主动散热 | 1 | 户外环境防护 |

### 1.2 完整 docker-compose.yml

```yaml
# /opt/fishing-behavior/docker-compose.yml
version: "3.8"

services:
  # ─── 流媒体接入 ───
  zlmediakit:
    image: zlmediakit/zlmediakit:release
    container_name: zlmediakit
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config/zlmediakit.ini:/opt/media/conf/config.ini:ro
    environment:
      TZ: Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/index/api/version"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ─── 本地消息队列 ───
  redis:
    image: redis:7.2-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/etc/redis/redis.conf:ro
    command: redis-server /etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      retries: 5

  # ─── 六层推理 Worker（核心服务）───
  inference_worker:
    image: fishing-behavior/inference:${MODEL_VERSION:-latest}
    container_name: inference_worker
    restart: unless-stopped
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility,video
      - REDIS_URL=redis://redis:6379/0
      - NODE_ID=${NODE_ID}
      - LOG_LEVEL=INFO
      # ─── 检测阈值配置 ───
      - PERSON_CONF_THRESHOLD=0.45
      - VESSEL_CONF_THRESHOLD=0.40
      - GEAR_CONF_THRESHOLD=0.35
      - BEHAVIOR_CONFIRM_THRESHOLD=0.80    # L6 LSTM 确认阈值
      # ─── 聚集预警配置 ───
      - CROWD_MIN_PERSONS=5
      - CROWD_ALERT_DURATION_S=30
      - CROWD_EPS_PIXELS=80
      # ─── 跟踪配置 ───
      - TRACKER_TYPE=bytetrack
      - TRACK_HIGH_THRESH=0.6
      - TRACK_LOW_THRESH=0.1
      - TRACK_BUFFER_FRAMES=30
      # ─── 天气降级 ───
      - WEATHER_API_KEY=${WEATHER_API_KEY}
      - WEATHER_STATION_ID=${WEATHER_STATION_ID}
    volumes:
      - ./models:/app/models:ro
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - evidence_storage:/app/evidence   # 证据视频片段
    depends_on:
      redis:
        condition: service_healthy
      zlmediakit:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 14G
        reservations:
          memory: 10G
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8089/health"]
      interval: 30s
      timeout: 20s
      retries: 3
      start_period: 120s    # 六层模型加载需要较长时间

  # ─── 摄像头流管理 ───
  stream_manager:
    image: fishing-behavior/stream-manager:${VERSION:-latest}
    container_name: stream_manager
    restart: unless-stopped
    network_mode: host
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ZLM_API=http://localhost:8080
      - NODE_ID=${NODE_ID}
      - NORMAL_FPS=5.0          # 正常检测帧率（人体跟踪需要 ≥ 5fps）
      - ALERT_FPS=15.0          # 告警触发时提升帧率（更精确跟踪）
      - RECORD_SECONDS_BEFORE=30  # 告警触发前保留 30s 视频
      - RECORD_SECONDS_AFTER=30   # 告警触发后继续录制 30s
    volumes:
      - ./config/cameras.yaml:/app/cameras.yaml:ro
      - evidence_storage:/app/evidence
    depends_on:
      - redis
      - zlmediakit

  # ─── 证据上传 + 断点续传 ───
  evidence_uploader:
    image: fishing-behavior/uploader:${VERSION:-latest}
    container_name: evidence_uploader
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CLOUD_API=${CLOUD_API_URL}
      - API_TOKEN=${CLOUD_API_TOKEN}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - RETRY_MAX=10
      - RETRY_BACKOFF=3.0      # 指数退避（最大 3^10 ≈ 59000s，但实际有上限）
      - LOCAL_CACHE_TTL_H=72   # 断网 72h 保障
      - EVIDENCE_BUCKET=fishing-behavior-evidence
    volumes:
      - evidence_storage:/app/evidence
      - ./logs:/app/logs
      - upload_cache:/app/cache

  # ─── Watchdog 主备切换守护 ───
  watchdog:
    image: fishing-behavior/watchdog:${VERSION:-latest}
    container_name: watchdog
    restart: unless-stopped
    environment:
      - PRIMARY_NODE_HOST=localhost
      - STANDBY_NODE_HOST=${STANDBY_NODE_IP}
      - HEARTBEAT_INTERVAL_S=10
      - FAILOVER_THRESHOLD=3    # 连续 3 次心跳失败触发切换
      - FAILOVER_TIMEOUT_S=15   # 目标切换完成时间
      - CLOUD_ALERT_URL=${CLOUD_API_URL}/edge/failover-alerts
      - NODE_ID=${NODE_ID}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/app/logs

  # ─── 指标导出 ───
  metrics_exporter:
    image: fishing-behavior/metrics:${VERSION:-latest}
    container_name: metrics_exporter
    restart: unless-stopped
    ports:
      - "127.0.0.1:8090:8090"  # Prometheus 抓取端口
    environment:
      - REDIS_URL=redis://redis:6379/0
      - NODE_ID=${NODE_ID}
    depends_on:
      - redis

  node_exporter:
    image: prom/node-exporter:v1.7.0
    container_name: node_exporter
    restart: unless-stopped
    network_mode: host
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'

volumes:
  redis_data:
  evidence_storage:
  upload_cache:
```

---

## 2. 摄像头与场景配置

### 2.1 cameras.yaml 格式（扩展版）

```yaml
# /opt/fishing-behavior/config/cameras.yaml
cameras:
  - id: "cam_shuiku_01"
    name: "水库北岸主入口"
    rtsp_url: "rtsp://admin:${CAM_PASSWORD}@192.168.10.100:554/stream1"
    type: "visible_light"              # 可见光 / infrared / dual_spectrum
    resolution: "3840x2160"            # 4K
    fps: 25
    extract_fps:
      normal: 5.0                      # 正常模式（人体跟踪需要 ≥ 5fps）
      alert: 15.0                      # 告警模式
      idle: 1.0                        # 静默模式（深夜无人）
    night_mode:
      enabled: true
      ir_cut_threshold: 40             # 平均亮度 < 40 切换红外模式
      enhancement: "clahe"             # clahe / gamma / none
    location:
      lat: 23.1234
      lon: 113.5678
      altitude_m: 5.0
    camera_params:
      height_m: 6.0                    # 摄像头安装高度（用于坐标换算）
      pitch_deg: 30                    # 俯仰角
      fov_horizontal_deg: 95           # 水平视角
    prohibited_zones:                  # 禁捕区域（监控重点，多边形）
      - name: "核心禁捕区"
        polygon: [[100,200],[800,200],[800,900],[100,900]]
        alert_on_vessel: true
        alert_on_crowd_level: "LEVEL_2"
    enabled: true

  - id: "cam_shuiku_01_ir"
    name: "水库北岸主入口（热成像）"
    rtsp_url: "rtsp://admin:${CAM_PASSWORD}@192.168.10.100:554/stream2"
    type: "infrared"
    paired_visible_cam: "cam_shuiku_01"   # 与可见光摄像头配对融合
    enabled: true
```

### 2.2 禁捕区域感兴趣区域（ROI）管理

```python
import cv2
import numpy as np

class ProhibitedZoneManager:
    """
    禁捕区域动态管理
    - 支持多边形禁捕区域定义
    - 渔船/人员进入禁捕区立即触发告警
    - 坐标系：图像像素坐标（支持多边形）
    """
    def __init__(self, camera_config: dict):
        self.zones = []
        for zone in camera_config.get("prohibited_zones", []):
            polygon = np.array(zone["polygon"], dtype=np.int32)
            self.zones.append({
                "name": zone["name"],
                "polygon": polygon,
                "alert_on_vessel": zone.get("alert_on_vessel", True),
                "alert_on_crowd_level": zone.get("alert_on_crowd_level", "LEVEL_2"),
            })

    def check_intrusion(self, detections: list, detection_type: str) -> list:
        """
        检查目标是否进入禁捕区
        detection_type: "vessel" / "person" / "gear"
        """
        intrusions = []
        for det in detections:
            cx = int((det["bbox"][0] + det["bbox"][2]) / 2)
            cy = int((det["bbox"][1] + det["bbox"][3]) / 2)

            for zone in self.zones:
                # cv2.pointPolygonTest: 点在多边形内返回正值
                if cv2.pointPolygonTest(zone["polygon"], (cx, cy), False) >= 0:
                    if detection_type == "vessel" and zone["alert_on_vessel"]:
                        intrusions.append({
                            "zone_name": zone["name"],
                            "detection": det,
                            "alert_type": f"vessel_in_prohibited_zone",
                            "severity": "HIGH",
                        })
                    break
        return intrusions
```

---

## 3. 证据固定与存证系统

### 3.1 证据链完整性设计

```python
import hashlib
import json
import time
from pathlib import Path

class EvidenceManager:
    """
    执法证据固定系统
    按照司法鉴定规范：
    - MD5 + SHA256 双重哈希（防篡改）
    - 时间戳链（每条证据包含前一条的哈希，形成链式结构）
    - 元数据完整（摄像头 ID、GPS 坐标、推理模型版本）
    """
    def __init__(self, evidence_dir: str):
        self.evidence_dir = Path(evidence_dir)
        self.chain_file = self.evidence_dir / "evidence_chain.jsonl"
        self._prev_hash = self._get_last_hash()

    def save_evidence(self, event: dict, snapshot: np.ndarray,
                       video_clip_path: str) -> dict:
        """保存完整证据包（截图 + 视频片段 + 元数据 + 哈希链）"""
        evidence_id = f"ev_{int(time.time()*1000)}_{event['camera_id']}"
        evidence_dir = self.evidence_dir / evidence_id
        evidence_dir.mkdir(parents=True)

        # 保存截图
        snapshot_path = evidence_dir / "snapshot.jpg"
        cv2.imwrite(str(snapshot_path), snapshot, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # 计算文件哈希
        def file_hash(path: str) -> dict:
            with open(path, "rb") as f:
                content = f.read()
            return {
                "md5": hashlib.md5(content).hexdigest(),
                "sha256": hashlib.sha256(content).hexdigest(),
            }

        snapshot_hash = file_hash(snapshot_path)
        video_hash = file_hash(video_clip_path)

        # 构建证据元数据
        metadata = {
            "evidence_id": evidence_id,
            "event_id": event["event_id"],
            "camera_id": event["camera_id"],
            "timestamp_utc": event["timestamp"],
            "behavior_type": event["behavior_type"],
            "confidence": event["confidence"],
            "model_version": event.get("model_version", "unknown"),
            "gps": event.get("camera_gps"),
            "evidence_files": {
                "snapshot": {"path": str(snapshot_path), **snapshot_hash},
                "video_clip": {"path": video_clip_path, **video_hash},
            },
            "prev_evidence_hash": self._prev_hash,  # 链式结构
        }

        # 计算整体哈希（链式签名）
        meta_str = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
        meta_hash = hashlib.sha256(meta_str.encode()).hexdigest()
        metadata["self_hash"] = meta_hash
        self._prev_hash = meta_hash

        # 写入证据链
        with open(self.chain_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        # 保存元数据文件
        with open(evidence_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return metadata
```

### 3.2 视频证据片段自动剪辑

```python
class EvidenceVideoClipper:
    """
    告警事件触发时，自动从录像中截取前后 30s 作为证据片段
    并在视频上叠加标注（BBox、时间戳、事件信息）
    """
    def __init__(self, pre_seconds=30, post_seconds=30):
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds

    def clip_and_annotate(self, video_buffer: list, event: dict,
                           output_path: str) -> str:
        """
        video_buffer：环形缓冲区，存储最近 N 秒的帧（带时间戳）
        event：告警事件信息
        """
        # 提取证据片段（前 30s + 后 30s）
        clip_frames = [f for f in video_buffer
                       if (event["timestamp"] - self.pre_seconds) <=
                          f["timestamp"] <=
                          (event["timestamp"] + self.post_seconds)]

        # 在视频上叠加标注
        annotated_frames = []
        for frame_data in clip_frames:
            frame = frame_data["image"].copy()

            # 时间戳水印
            timestamp = frame_data["timestamp"]
            ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(frame, ts_str, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # 摄像头 ID + 模型版本
            info_str = f"CAM:{event['camera_id']} | MODEL:{event.get('model_version')}"
            cv2.putText(frame, info_str, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

            # 行为标签（红色，醒目）
            label = f"FISHING DETECTED | CONF:{event['confidence']:.2f}"
            cv2.putText(frame, label, (10, frame.shape[0]-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            # 绘制检测框
            for det in event.get("evidence", {}).get("vessels", []):
                x1,y1,x2,y2 = map(int, det["bbox"])
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,165,255), 2)
                cv2.putText(frame, det["class"], (x1,y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,165,255), 2)

            annotated_frames.append(frame)

        # 写入视频文件（H.265 高压缩比，证据存储）
        h, w = annotated_frames[0].shape[:2]
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            25.0, (w, h)
        )
        for frame in annotated_frames:
            writer.write(frame)
        writer.release()

        return output_path
```

---

## 4. 云端中心服务

### 4.1 核心数据库表设计

```sql
-- ─── 捕捞行为事件主表 ───
CREATE TABLE fishing_events (
    id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id          CHAR(36) NOT NULL UNIQUE,
    site_id           VARCHAR(32) NOT NULL,
    camera_id         VARCHAR(64) NOT NULL,
    occurred_at       DATETIME(3) NOT NULL,

    -- 行为研判结果
    behavior_type     ENUM('CONFIRMED','SUSPICIOUS','NORMAL') NOT NULL,
    behavior_confidence DECIMAL(5,4),
    decision_basis    VARCHAR(64),               -- rule_engine_confirmed / lstm_confirmed
    alert_level       ENUM('CRITICAL','HIGH','MEDIUM','LOW','NONE') DEFAULT 'NONE',

    -- 人体检测
    person_count      SMALLINT UNSIGNED DEFAULT 0,
    persons_with_gear SMALLINT UNSIGNED DEFAULT 0,
    crowd_level       ENUM('NORMAL','LEVEL_1','LEVEL_2','LEVEL_3') DEFAULT 'NORMAL',
    crowd_duration_s  SMALLINT UNSIGNED DEFAULT 0,

    -- 渔船
    vessel_count      TINYINT UNSIGNED DEFAULT 0,
    vessel_types      JSON,                       -- ["fishing_boat_small", ...]
    vessel_stationary TINYINT(1) DEFAULT 0,

    -- 渔具
    gear_count        TINYINT UNSIGNED DEFAULT 0,
    gear_types        JSON,                       -- ["gill_net", "trawl_net"]
    gear_deployed     TINYINT(1) DEFAULT 0,

    -- 轨迹
    trajectory_pattern VARCHAR(32),              -- stationary / meandering / directional

    -- 证据文件
    snapshot_url      VARCHAR(512),
    video_clip_url    VARCHAR(512),
    evidence_hash     CHAR(64),                  -- SHA256（防篡改）

    -- 系统字段
    model_version     VARCHAR(32),
    inference_ms      SMALLINT UNSIGNED,
    alert_sent        TINYINT(1) DEFAULT 0,
    handled           TINYINT(1) DEFAULT 0,       -- 是否已被执法人员处理
    handler_note      TEXT,
    created_at        DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_site_time    (site_id, occurred_at),
    INDEX idx_behavior     (behavior_type, occurred_at),
    INDEX idx_alert        (alert_sent, behavior_type, occurred_at),
    INDEX idx_unhandled    (handled, behavior_type, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── 人体跟踪轨迹记录（用于 Trajectory Analysis）───
CREATE TABLE tracking_trajectories (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    site_id       VARCHAR(32) NOT NULL,
    camera_id     VARCHAR(64) NOT NULL,
    track_id      INT UNSIGNED NOT NULL,
    frame_id      INT UNSIGNED NOT NULL,
    recorded_at   DATETIME(3) NOT NULL,
    bbox          JSON NOT NULL,              -- [x1,y1,x2,y2]
    center_x      SMALLINT,
    center_y      SMALLINT,
    track_class   TINYINT,                    -- 0=person, 1=person_with_gear
    confidence    DECIMAL(4,3),
    event_id      CHAR(36),                   -- 关联到告警事件（若有）
    INDEX idx_site_track   (site_id, camera_id, track_id, recorded_at),
    INDEX idx_event        (event_id)
) ENGINE=InnoDB ROW_FORMAT=COMPRESSED;

-- ─── 渔船历史轨迹（Re-identification + 巡逻分析）───
CREATE TABLE vessel_trajectories (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    site_id       VARCHAR(32) NOT NULL,
    camera_id     VARCHAR(64) NOT NULL,
    track_id      INT UNSIGNED NOT NULL,
    recorded_at   DATETIME(3) NOT NULL,
    vessel_class  VARCHAR(32),
    bbox          JSON,
    ais_mmsi      VARCHAR(20),               -- AIS 船舶编号（若能匹配）
    speed_px      DECIMAL(6,2),             -- 像素速度（间接估算船速）
    stationary    TINYINT(1) DEFAULT 0,
    event_id      CHAR(36),
    INDEX idx_site_track   (site_id, camera_id, track_id, recorded_at)
) ENGINE=InnoDB ROW_FORMAT=COMPRESSED;

-- ─── 模型性能日志 ───
CREATE TABLE model_performance_log (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    model_version       VARCHAR(32) NOT NULL,
    log_date            DATE NOT NULL,
    camera_id           VARCHAR(64),
    total_frames        INT UNSIGNED DEFAULT 0,
    persons_detected    INT UNSIGNED DEFAULT 0,
    vessels_detected    INT UNSIGNED DEFAULT 0,
    behaviors_confirmed INT UNSIGNED DEFAULT 0,
    false_positive_manual INT UNSIGNED DEFAULT 0,  -- 人工标记误报（FP）
    false_negative_manual INT UNSIGNED DEFAULT 0,  -- 人工标记漏报（FN）
    crowd_alerts_total  INT UNSIGNED DEFAULT 0,
    crowd_alerts_fp     INT UNSIGNED DEFAULT 0,    -- 聚集预警误报
    avg_inference_ms    DECIMAL(7,2),
    p95_inference_ms    DECIMAL(7,2),
    p99_inference_ms    DECIMAL(7,2),
    avg_mota_estimate   DECIMAL(5,4),              -- 抽样估算 MOTA
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ver_date_cam (model_version, log_date, camera_id)
) ENGINE=InnoDB;
```

### 4.2 告警推送格式（企业微信 Markdown）

```python
def build_wechat_alert(event: dict) -> dict:
    behavior_emoji = {"CONFIRMED": "🚨", "SUSPICIOUS": "⚠️"}
    level_color = {"CRITICAL": "red", "HIGH": "warning", "MEDIUM": "comment"}

    gear_str = "、".join(event["evidence"].get("gear_types", ["未检测到"])) or "无"
    vessel_str = "、".join(
        [v["class"] for v in event["evidence"].get("vessels", [])]
    ) or "无"

    return {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""## {behavior_emoji.get(event['behavior_type'], '📋')} 捕捞行为告警

> **告警级别**：<font color=\"{level_color.get(event['alert_level'], 'info')}\">{event['alert_level']}</font>
> **研判结果**：{event['behavior_type']}（置信度 {event['confidence']:.1%}）

**📍 站点**：{event.get('site_name', event['camera_id'])}
**🕐 时间**：{event['timestamp']}
**👥 现场人数**：{event['evidence']['person_count']}人（持渔具 {event['evidence']['persons_with_gear']}人）
**🚢 渔船**：{vessel_str}
**🎣 渔具**：{gear_str}
**⏱ 持续时长**：{event['evidence'].get('crowd_duration_s', 0)}秒

[查看截图]({event['snapshot_url']}) | [查看视频证据]({event['video_clip_url']}) | [查看详情]({event['detail_url']})

> 执法建议：{event.get('enforcement_suggestion', '请立即派员核查')}"""
        }
    }
```

---

## 5. 推理框架精度配置

### 5.1 各模型量化方案

| 模型层 | 框架 | 精度 | 延迟（Jetson Orin NX） | 说明 |
|--------|------|------|----------------------|------|
| L1 人体检测 | TensorRT | INT8 | 85ms | 校准集 1000 张水面人体图 |
| L2 ByteTrack | ONNX Runtime CPU | FP32 | 12ms | 纯 CPU，轻量无需量化 |
| L3 CSRNet | TensorRT | FP16 | 25ms | FP16 足够，INT8 MAE 增大过多 |
| L4 渔船检测 | TensorRT | INT8 | 130ms | 大模型（YOLOv8l），INT8 必要 |
| L5 渔具检测 | TensorRT | INT8 | 85ms | 同 L1 配置 |
| L6 LSTM | ONNX Runtime CPU | FP32 | 28ms | CPU 执行，30s 延迟可接受 |
| **合计 P95** | | | **~430ms** | 目标 ≤ 500ms ✅ |

### 5.2 INT8 校准注意事项

```python
# 渔具检测 INT8 校准特别说明
# 渔具外观多样（细长网、围网、鱼笼），校准集必须覆盖全类型

def validate_gear_calibration_coverage(calib_dir: str) -> bool:
    """验证 INT8 校准集的渔具类型覆盖"""
    required_classes = {
        "trawl_net": 80,     # 最少 80 张拖网图
        "purse_seine": 60,
        "gill_net": 80,
        "fish_trap": 60,
        "fishing_rod": 100,
        "fish_cage": 80,
    }
    # 统计各类别样本数...
    # 未满足要求时拒绝进行量化
    pass
```

---

## 6. CI/CD 流水线

```yaml
# .github/workflows/behavior_model_release.yml
name: 捕捞行为模型发布

on:
  push:
    tags: ['behavior-model-v[0-9]+.[0-9]+']

jobs:
  gate1_offline:
    name: Gate1 六层模型离线评估
    runs-on: [self-hosted, gpu]
    steps:
      - name: 人体检测评估
        run: python eval/eval_detection.py --model L1 --min-mAP50 0.85 --max-fnr 0.10
      - name: 跟踪评估（MOTA）
        run: python eval/eval_tracking.py --min-mota 0.70 --max-id-switch 20
      - name: 聚集评估（MAE）
        run: python eval/eval_crowd.py --max-mae 3.0 --min-precision 0.85
      - name: 渔船评估
        run: python eval/eval_vessel.py --min-mAP50 0.87
      - name: 渔具评估
        run: python eval/eval_gear.py --min-mAP50 0.80
      - name: 行为研判评估
        run: python eval/eval_behavior.py --min-f1 0.85 --max-fpr 0.08 --max-fnr 0.08

  gate2_performance:
    needs: gate1_offline
    name: Gate2 推理性能压测（Jetson Orin NX）
    runs-on: [self-hosted, jetson-orin]
    steps:
      - name: 导出六层 TensorRT 引擎
        run: python scripts/export_all_trt.py --version ${{ github.ref_name }}
      - name: 六层流水线压测（600s）
        run: |
          python benchmark/pipeline_benchmark.py \
            --duration 600 \
            --max-p95-ms 500 \
            --max-p99-ms 700 \
            --max-gpu-mem-gb 12

  gate3_canary:
    needs: gate2_performance
    name: Gate3 灰度部署（7天）
    runs-on: ubuntu-latest
    steps:
      - name: 推送至试点站点
        run: python scripts/deploy_canary.py --site ${{ vars.CANARY_SITE_ID }}
      - name: 安排 7 天后自动门控检查
        run: python scripts/schedule_gate3_check.py --version ${{ github.ref_name }}

  gate4_full_deploy:
    needs: gate3_canary
    if: github.event_name == 'workflow_dispatch'
    name: 全量发布（人工触发）
    runs-on: ubuntu-latest
    steps:
      - name: 滚动更新所有站点
        run: |
          python scripts/rolling_deploy.py \
            --sites config/all_sites.yaml \
            --version ${{ github.ref_name }} \
            --batch-size 2 \
            --health-check-interval 180 \
            --auto-rollback-on-alert
```

---

## 7. 成本估算

### 7.1 单站点硬件成本

| 组件 | 型号 | 单价（元） | 数量 | 小计 |
|------|------|---------|------|------|
| 主推理节点 | Jetson Orin NX 16GB（工业版） | 9,500 | 1 | 9,500 |
| 备推理节点（核心站） | Jetson Orin 8GB | 6,500 | 1 | 6,500 |
| 4K 星光摄像头 | 海康 DS-2CD6944G2-IZS | 4,500 | 3 | 13,500 |
| 双光谱摄像头（热成像）| 海康 DS-2TD2628-3/QA | 18,000 | 1 | 18,000 |
| 4G/5G 双链路路由 | 工业级双卡 | 3,200 | 1 | 3,200 |
| UPS 电源（2KVA） | 8h 续航 | 4,500 | 1 | 4,500 |
| 防水工业机箱 + 散热 | IP67 | 2,800 | 1 | 2,800 |
| 太阳能供电（备用）| 200W 板 + 控制器 | 3,500 | 1 | 3,500 |
| 安装施工（立杆+布线）| — | — | 1 | 8,000 |
| **单站点合计** | | | | **~69,500** |

### 7.2 云端运维成本（月，10 站点规模）

| 项目 | 规格 | 月费（元） |
|------|------|---------|
| ECS（API+业务服务，2台） | 8核16GB | 1,200 |
| RDS MySQL HA | 4核8GB | 1,500 |
| Redis Sentinel | 2核4GB | 400 |
| Kafka（3节点） | 托管 | 1,000 |
| MinIO/OSS（证据存储，20TB） | 归档型 | 1,200 |
| 带宽（视频+证据上传） | 200Mbps 共享 | 1,500 |
| **月合计** | | **~6,800** |
