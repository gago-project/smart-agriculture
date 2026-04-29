# 03. 企业级高可用部署方案

## 1. 部署架构与高可用设计

### 1.1 完整 HA 部署拓扑

```
╔══════════════════════════════════════════════════════════════════╗
║  云端中心层（双可用区，Availability Zone A/B）                    ║
║                                                                  ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │  SLB 负载均衡（4层/7层）                                  │   ║
║  └──────────────┬────────────────────────────┬──────────────┘   ║
║                 │                            │                   ║
║  ┌──────────────▼──────────┐  ┌─────────────▼───────────────┐  ║
║  │  API Server 集群（AZ-A） │  │  API Server 集群（AZ-B）    │  ║
║  │  2节点，故障自动切换     │  │  2节点，故障自动切换         │  ║
║  └──────────────┬──────────┘  └─────────────┬───────────────┘  ║
║                 └────────────┬───────────────┘                  ║
║  ┌──────────────────────────▼───────────────────────────────┐   ║
║  │  Kafka 集群（3 Broker，Replication Factor=3）             │   ║
║  │  Topic: vehicle_events / alert_tasks / model_updates      │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             │                                    ║
║  ┌──────────────────────────▼───────────────────────────────┐   ║
║  │  MySQL 主从（1主2从）+ ProxySQL 读写分离                  │   ║
║  │  Redis Sentinel（1主2从）+ Keepalived VIP                 │   ║
║  │  MinIO 分布式（3节点，EC:2 纠删码）                       │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝
                    │  专线 VPN（IPSec/TLS 1.3）
╔══════════════════════════════════════════════════════════════════╗
║  边缘节点层（每个路口独立机箱）                                  ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  主推理节点（Jetson Orin NX 16GB）                        │    ║
║  │  ├─ ZLMediaKit（RTSP 接入，最多 4 路）                   │    ║
║  │  ├─ AdaptiveFrameExtractor（自适应抽帧）                  │    ║
║  │  ├─ InferenceWorker × 2（多线程推理，GPU）               │    ║
║  │  ├─ Redis Stream（本地消息队列，断网缓存）                │    ║
║  │  ├─ ResultReporter（上报+断点续传）                       │    ║
║  │  └─ Watchdog（进程守护，心跳 10s，超时重启）             │    ║
║  ├─────────────────────────────────────────────────────────┤    ║
║  │  备推理节点（Jetson Orin 8GB）[可选，高优先级路口配置]   │    ║
║  │  主节点故障 → 15s 内接管（热备模式，模型已预加载）        │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║  断网保障：本地 Redis Stream 缓存 72h 数据；网络恢复后自动同步   ║
╚══════════════════════════════════════════════════════════════════╝
                    │  局域网 + 4G/5G 备用链路
╔══════════════════════════════════════════════════════════════════╗
║  端设备层                                                        ║
║  IP 摄像头（RTSP H.265，1080P+）│ 4G/5G 路由（主/备双链路）    ║
╚══════════════════════════════════════════════════════════════════╝
```

### 1.2 边缘节点故障切换流程

```
正常状态：
  主节点运行推理 → 备节点每 10s 心跳检测主节点状态

主节点故障检测：
  备节点连续 3 次心跳无响应（30s）→ 触发 Failover
  ↓
  备节点接管流程（目标 ≤ 15s 完成）：
    1. 备节点 ZLMediaKit 拉取所有摄像头 RTSP 流（5s）
    2. 备节点 InferenceWorker 启动（模型已预加载，秒级就绪）（3s）
    3. 云端切换上报目标至备节点 IP（2s）
    4. 告警推送：运维人员收到主节点故障通知（5s 内）
    5. 合计切换时间 ≤ 15s，期间最多丢失 2-3 帧

主节点恢复：
  备节点继续工作（不自动切回，避免抖动）
  → 运维手动确认主节点健康后执行切回
  → 切回过程相同，期间 < 15s
```

---

## 2. 边缘推理服务部署

### 2.1 硬件规格对照表

| 路口等级 | 主节点 | 备节点 | 摄像头路数 | 推理能力 |
|---------|--------|--------|-----------|---------|
| 核心路口 | Jetson Orin NX 16GB | Jetson Orin 8GB | 4路 | 4路 ≤ 120ms/帧 |
| **标准路口** | Jetson Orin NX 16GB | 无（依赖云端降级） | 2路 | 2路 ≤ 100ms/帧 |
| 次要路口 | Jetson Orin 8GB | 无 | 1路 | 1路 ≤ 150ms/帧 |
| 经济型 | RK3588 工控机（NPU） | 无 | 1路 | 仅检测+分类（无LPR） |

### 2.2 系统初始化（Jetson Orin NX）

```bash
#!/bin/bash
# setup_edge_node.sh — 边缘节点初始化脚本（一键执行）
set -e

NODE_ID="${1:-node_001}"
CLOUD_API="${2:-https://your-cloud-api.com}"

echo "=== [1/6] 验证 JetPack 版本 ==="
jetson_release -r
# 要求：JetPack 5.1.2+（CUDA 11.4，TensorRT 8.5.2，cuDNN 8.6）

echo "=== [2/6] 安装 Docker + NVIDIA Runtime ==="
apt-get update -qq
apt-get install -y docker.io curl
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L "https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list" \
  > /etc/apt/sources.list.d/nvidia-docker.list
apt-get update && apt-get install -y nvidia-container-runtime
systemctl daemon-reload && systemctl restart docker

echo "=== [3/6] 配置 NVIDIA 运行时为默认 ==="
cat > /etc/docker/daemon.json << 'EOF'
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": { "path": "nvidia-container-runtime", "runtimeArgs": [] }
  },
  "log-driver": "json-file",
  "log-opts": { "max-size": "100m", "max-file": "5" }
}
EOF
systemctl restart docker

echo "=== [4/6] 写入节点配置 ==="
mkdir -p /opt/aquatic-cv/config
cat > /opt/aquatic-cv/config/node.yaml << EOF
node_id: ${NODE_ID}
cloud_api: ${CLOUD_API}
heartbeat_interval_s: 10
model_dir: /opt/aquatic-cv/models
log_dir: /opt/aquatic-cv/logs
local_cache_ttl_h: 72
EOF

echo "=== [5/6] 下载模型文件 ==="
./scripts/download_models.sh --version $(cat /opt/aquatic-cv/config/current_version)

echo "=== [6/6] 启动服务 ==="
cd /opt/aquatic-cv && docker compose up -d

# 等待健康检查
sleep 15
./scripts/health_check.sh || { echo "健康检查失败！"; exit 1; }
echo "✅ 边缘节点 ${NODE_ID} 初始化完成"
```

### 2.3 完整 docker-compose.yml

```yaml
# /opt/aquatic-cv/docker-compose.yml
version: "3.8"

services:
  # ─── 流媒体服务 ───
  zlmediakit:
    image: zlmediakit/zlmediakit:release
    container_name: zlmediakit
    restart: unless-stopped
    network_mode: host          # 使用 host 网络，降低 RTSP 延迟
    volumes:
      - ./config/zlmediakit.ini:/opt/media/conf/config.ini:ro
    environment:
      - TZ=Asia/Shanghai
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
      - "127.0.0.1:6379:6379"   # 仅本地访问
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/etc/redis/redis.conf:ro
    command: redis-server /etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    sysctls:
      net.core.somaxconn: 1024

  # ─── 核心推理服务 ───
  inference_worker:
    image: aquatic-cv/inference:${MODEL_VERSION:-latest}
    container_name: inference_worker
    restart: unless-stopped
    runtime: nvidia             # 使用 NVIDIA Container Runtime
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility,video
      - REDIS_URL=redis://redis:6379/0
      - NODE_ID=${NODE_ID}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - CONF_THRESHOLD=0.50
      - CLS_THRESHOLD=0.75
      - LPR_THRESHOLD=0.80
      - OCR_THRESHOLD=0.70
      - MAX_BATCH_SIZE=1
      - INFERENCE_THREADS=2
    volumes:
      - ./models:/app/models:ro
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - /tmp/snapshots:/tmp/snapshots  # 截图临时存储
    depends_on:
      redis:
        condition: service_healthy
      zlmediakit:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 12G
        reservations:
          memory: 8G
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "python3", "-c", "import requests; requests.get('http://localhost:8088/health', timeout=5)"]
      interval: 30s
      timeout: 15s
      retries: 3
      start_period: 60s         # TensorRT 引擎加载需要时间

  # ─── 帧抽取 + 摄像头管理 ───
  stream_puller:
    image: aquatic-cv/stream-puller:${VERSION:-latest}
    container_name: stream_puller
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ZLM_API=http://localhost:8080
      - NODE_ID=${NODE_ID}
      - NORMAL_FPS=1.0          # 正常抽帧率（Throughput：帧/秒）
      - EVENT_FPS=5.0           # 事件触发抽帧率
      - MOTION_THRESHOLD=0.015  # 运动检测阈值
    volumes:
      - ./config/cameras.yaml:/app/cameras.yaml:ro
      - ./logs:/app/logs
    network_mode: host          # 访问摄像头局域网
    depends_on:
      redis:
        condition: service_healthy

  # ─── 结果上报 + 断点续传 ───
  result_reporter:
    image: aquatic-cv/reporter:${VERSION:-latest}
    container_name: result_reporter
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CLOUD_API=${CLOUD_API_URL}
      - API_TOKEN=${CLOUD_API_TOKEN}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - RETRY_MAX=5
      - RETRY_BACKOFF=2.0       # 指数退避（断网后恢复时）
      - LOCAL_CACHE_TTL_H=72    # 本地缓存 72 小时
    volumes:
      - ./logs:/app/logs
      - reporter_cache:/app/cache  # 断网时本地缓存
    depends_on:
      redis:
        condition: service_healthy

  # ─── Prometheus 指标导出 ───
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
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

  # ─── Watchdog（进程守护） ───
  watchdog:
    image: aquatic-cv/watchdog:${VERSION:-latest}
    container_name: watchdog
    restart: unless-stopped
    environment:
      - MONITORED_SERVICES=inference_worker,stream_puller,result_reporter
      - HEARTBEAT_INTERVAL_S=10
      - FAILURE_THRESHOLD=3     # 连续 3 次失败触发告警
      - CLOUD_ALERT_URL=${CLOUD_API_URL}/edge/alerts
      - NODE_ID=${NODE_ID}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/app/logs
    depends_on:
      - redis

volumes:
  redis_data:
  reporter_cache:
```

---

## 3. 推理引擎选型与精度配置

### 3.1 FP32 / FP16 / INT8 精度对比（Jetson Orin NX 实测）

| 精度格式 | YOLOv8m mAP50 | 单帧延迟（检测） | GPU 显存 | 适用场景 |
|---------|--------------|----------------|---------|---------|
| **FP32**（PyTorch原生） | 0.891（基准） | 310ms | 8.2GB | 不可用（超出延迟） |
| **FP16**（TensorRT） | 0.889（-0.2%） | 165ms | 4.1GB | 可用（边界情况） |
| **INT8**（TensorRT）✅ | 0.882（-1.0%） | 85ms | 2.3GB | **推荐**（边缘主力） |
| INT8 + 剪枝30% | 0.875（-1.8%） | 62ms | 1.6GB | 经济型设备 |

**结论**：边缘端统一使用 INT8，mAP 损失控制在 1% 以内，延迟从 310ms 降至 85ms（3.6×加速）。

### 3.2 TensorRT INT8 校准与导出

```python
# export_trt.py
from ultralytics import YOLO
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def export_trt_int8(
    model_path: str,
    calibration_data: str,
    output_dir: str,
    device: int = 0,
    workspace_gb: int = 4,
):
    """
    TensorRT INT8 量化导出
    校准数据集要求：
      - 至少 500 张（推荐 1000 张）代表性生产图片
      - 覆盖所有场景（白天/夜间/雨天/不同角度）
      - 图片来自 val 集（不能用 test 集，防止泄漏）
    """
    model = YOLO(model_path)

    # 验证校准数据集质量
    calib_imgs = list(Path(calibration_data).glob("images/val/**/*.jpg"))
    assert len(calib_imgs) >= 500, f"校准数据不足：{len(calib_imgs)} < 500"
    logging.info(f"校准数据集：{len(calib_imgs)} 张图片")

    # 导出 TensorRT INT8
    export_path = model.export(
        format="engine",
        device=device,
        half=False,
        int8=True,
        data=calibration_data,
        batch=1,
        workspace=workspace_gb,
        simplify=True,
        imgsz=640,
    )

    # 保存导出路径和哈希
    import hashlib, json
    with open(export_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    meta = {
        "model_path": model_path,
        "precision": "INT8",
        "framework": "TensorRT",
        "export_path": str(export_path),
        "sha256": sha256,
        "calibration_images": len(calib_imgs),
    }
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{output_dir}/export_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logging.info(f"✅ TRT INT8 导出完成: {export_path}")
    logging.info(f"   SHA256: {sha256}")
    return export_path

# 执行导出
export_trt_int8(
    model_path="models/detection/v1.2/best.pt",
    calibration_data="datasets/aquatic_vehicle_detection/dataset.yaml",
    output_dir="models/detection/v1.2/",
)
```

### 3.3 ONNX 导出（跨平台备用）

```python
# ONNX 导出（兼容 ONNX Runtime CPU/CUDA EP，用于非 NVIDIA 设备降级）
model.export(
    format="onnx",
    opset=17,
    simplify=True,
    dynamic=False,      # 固定 batch=1 输入，优化推理图
    imgsz=640,
    half=False,         # ONNX Runtime CPU 不支持 FP16
)

# 验证 ONNX 模型输出一致性
import onnxruntime as ort
import numpy as np

def verify_onnx_output(pt_model_path: str, onnx_model_path: str):
    test_input = np.random.randn(1, 3, 640, 640).astype(np.float32)

    # PyTorch 输出
    import torch
    pt_model = YOLO(pt_model_path).model.eval()
    with torch.no_grad():
        pt_out = pt_model(torch.from_numpy(test_input)).numpy()

    # ONNX Runtime 输出
    sess = ort.InferenceSession(onnx_model_path, providers=["CPUExecutionProvider"])
    ort_out = sess.run(None, {"images": test_input})[0]

    # 验证数值差异（允许误差 < 1e-4）
    max_diff = np.abs(pt_out - ort_out).max()
    assert max_diff < 1e-4, f"ONNX 输出与 PyTorch 不一致！max_diff={max_diff}"
    print(f"✅ ONNX 验证通过，最大误差: {max_diff:.2e}")
```

---

## 4. 四步推理流水线（边缘端实现）

### 4.1 流水线调度器（并行优化）

```python
# pipeline.py
import tensorrt as trt
import numpy as np
import cv2
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import time
import redis

class AquaticVehiclePipeline:
    """
    四步推理流水线（Step 3 + Step 4 并行执行，最大化 Throughput）
    目标 Latency P95 ≤ 150ms
    """
    def __init__(self, config: dict):
        # 加载各阶段模型（TensorRT INT8）
        self.det_engine    = TRTInferencer("models/detection/best_int8.engine")
        self.cls_engine    = TRTInferencer("models/classification/best_int8.engine")
        self.lpr_det       = TRTInferencer("models/lpr_det/best_int8.engine")
        self.lpr_rec       = CRNNInferencer("models/lpr_rec/crnn.onnx")
        self.ocr_det       = PaddleDBInferencer("models/ocr/det_model/")
        self.ocr_rec       = PaddleSVTRInferencer("models/ocr/rec_model/")

        # 线程池（Step 3+4 并行）
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 置信度阈值配置
        self.det_conf_thr = config.get("det_conf_threshold", 0.50)
        self.cls_conf_thr = config.get("cls_conf_threshold", 0.75)
        self.lpr_conf_thr = config.get("lpr_conf_threshold", 0.80)
        self.ocr_conf_thr = config.get("ocr_conf_threshold", 0.70)

        # 时序滤波器（减少视频流中的单帧误判）
        self.trackers = {}  # track_id → VehicleTracker

    def process_frame(
        self,
        frame: np.ndarray,
        frame_meta: dict,
        track_results: Optional[dict] = None,  # 来自 ByteTrack 的目标跟踪结果
    ) -> list:
        t0 = time.perf_counter()
        results = []

        # ─── Step 1：目标检测（Object Detection）───
        preprocessed = self._preprocess(frame, (640, 640))
        detections = self.det_engine.infer(preprocessed)
        # 过滤：仅保留货车/大车类别，conf ≥ 阈值
        truck_dets = [
            d for d in detections
            if d["class"] in [1, 2, 3] and d["conf"] >= self.det_conf_thr
        ]

        if not truck_dets:
            self._record_latency("total", time.perf_counter() - t0)
            return []

        for det in truck_dets:
            vehicle_bbox = det["bbox"]
            track_id = track_results.get(str(vehicle_bbox)) if track_results else None

            # ─── Step 2：水产车分类（Classification）───
            t2 = time.perf_counter()
            vehicle_crop = self._crop_with_margin(frame, vehicle_bbox, margin=0.10)
            cls_input = self._preprocess(vehicle_crop, (224, 224))
            cls_pred, cls_conf = self.cls_engine.infer(cls_input)
            self._record_latency("classification", time.perf_counter() - t2)

            # 不确定区间（0.50-0.75）→ 多模型集成投票
            if self.cls_conf_thr > cls_conf >= 0.50:
                cls_pred, cls_conf = self._ensemble_classify(vehicle_crop)

            # 时序滤波（连续帧投票，减少误判）
            if track_id:
                cls_pred, cls_conf = self._temporal_vote(track_id, cls_pred, cls_conf)

            if cls_pred != "aquatic":
                continue  # 非水产车，跳过后续步骤

            # ─── Step 3 + Step 4 并行执行 ───
            future_lpr = self._executor.submit(self._recognize_plate, frame, vehicle_bbox)
            future_ocr = self._executor.submit(self._extract_body_text, frame, vehicle_bbox)

            lpr_result = future_lpr.result(timeout=0.1)  # 最多等 100ms
            ocr_result = future_ocr.result(timeout=0.1)

            total_ms = (time.perf_counter() - t0) * 1000
            self._record_latency("total", total_ms / 1000)

            results.append({
                "frame_id": frame_meta["frame_id"],
                "camera_id": frame_meta["camera_id"],
                "timestamp": frame_meta["timestamp"],
                "vehicle_bbox": vehicle_bbox,
                "detection_conf": round(det["conf"], 4),
                "is_aquatic_vehicle": True,
                "cls_confidence": round(cls_conf, 4),
                "cls_method": "ensemble" if cls_conf < self.cls_conf_thr else "single",
                "license_plate": lpr_result.get("plate_text"),
                "lp_confidence": lpr_result.get("confidence"),
                "key_texts": ocr_result.get("key_texts", []),
                "has_aquatic_mark": ocr_result.get("has_aquatic_mark", False),
                "inference_latency_ms": round(total_ms, 1),
            })

        return results

    def _temporal_vote(self, track_id: str, pred: str, conf: float) -> tuple:
        """5 帧滑动窗口投票（Multi-object Tracking 时序平滑）"""
        if track_id not in self.trackers:
            self.trackers[track_id] = []
        history = self.trackers[track_id]
        history.append(conf if pred == "aquatic" else 0)
        if len(history) > 5:
            history.pop(0)
        avg_conf = sum(history) / len(history)
        return ("aquatic", avg_conf) if avg_conf > 0.60 else ("non_aquatic", 1 - avg_conf)

    def _recognize_plate(self, frame: np.ndarray, vehicle_bbox: list) -> dict:
        """Step 3：车牌检测 + 识别（LPR）"""
        roi = self._crop_with_margin(frame, vehicle_bbox, margin=0.05)

        # 车牌检测
        lp_dets = self.lpr_det.infer(self._preprocess(roi, (640, 640)))
        if not lp_dets:
            return {"plate_text": None, "confidence": 0.0}

        lp_bbox = lp_dets[0]["bbox"]
        lp_crop = roi[lp_bbox[1]:lp_bbox[3], lp_bbox[0]:lp_bbox[2]]

        # 低分辨率车牌超分辨率增强
        if lp_crop.shape[1] < 80:
            lp_crop = self._super_resolve(lp_crop)  # ESRGAN 2×

        # 车牌字符识别（CRNN）
        plate_text, confidence = self.lpr_rec.infer(lp_crop)

        # 置信度低于阈值 → 标记进入 Active Learning 队列
        if confidence < self.lpr_conf_thr:
            self._push_to_annotation_queue({
                "type": "low_conf_plate",
                "image": lp_crop,
                "confidence": confidence,
            })

        return {"plate_text": plate_text, "confidence": round(confidence, 4)}

    def _extract_body_text(self, frame: np.ndarray, vehicle_bbox: list) -> dict:
        """Step 4：车身关键文字提取（OCR）"""
        roi = self._crop_with_margin(frame, vehicle_bbox, margin=0.15)
        ocr_raw = self.ocr_rec.infer(self.ocr_det.infer(roi))
        return extract_key_texts(ocr_raw, min_confidence=self.ocr_conf_thr)
```

---

## 5. 云端中心服务部署

### 5.1 核心数据库设计

```sql
-- ─── 车辆事件主表 ───
CREATE TABLE vehicle_events (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id       CHAR(36) NOT NULL UNIQUE,           -- UUID v4
    camera_id      VARCHAR(64) NOT NULL,
    site_id        VARCHAR(32) NOT NULL,               -- 养殖基地 ID（行级隔离）
    occurred_at    DATETIME(3) NOT NULL,
    license_plate  VARCHAR(20),                        -- 加密存储（AES-256）
    lp_confidence  DECIMAL(5,4),
    is_aquatic     TINYINT(1) NOT NULL DEFAULT 0,
    cls_confidence DECIMAL(5,4),
    cls_method     ENUM('single_model','ensemble','temporal_vote') DEFAULT 'single_model',
    key_texts      JSON,                               -- 车身文字列表
    has_aquatic_mark TINYINT(1) DEFAULT 0,
    snapshot_url   VARCHAR(512),                       -- MinIO OSS 地址
    vehicle_bbox   JSON,                               -- [x1,y1,x2,y2]
    inference_ms   SMALLINT UNSIGNED,                  -- 推理耗时（Latency）
    model_version  VARCHAR(32),                        -- 产生此事件的模型版本
    alert_sent     TINYINT(1) DEFAULT 0,
    created_at     DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    -- 查询优先索引
    INDEX idx_site_time    (site_id, occurred_at),
    INDEX idx_camera_time  (camera_id, occurred_at),
    INDEX idx_plate        (license_plate),
    INDEX idx_aquatic_time (is_aquatic, occurred_at),
    INDEX idx_alert        (alert_sent, is_aquatic, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;

-- ─── 车牌白名单（合规水产运输车） ───
CREATE TABLE plate_whitelist (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    site_id        VARCHAR(32) NOT NULL,
    license_plate  VARCHAR(20) NOT NULL,               -- 加密存储
    owner_name     VARCHAR(100),
    company_name   VARCHAR(200),
    permit_no      VARCHAR(100),                       -- 捕捞许可证号
    permit_type    ENUM('transport','fishing','both') DEFAULT 'transport',
    expire_date    DATE,
    is_active      TINYINT(1) DEFAULT 1,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_site_plate (site_id, license_plate),
    INDEX idx_plate_active (license_plate, is_active)
) ENGINE=InnoDB;

-- ─── 告警记录 ───
CREATE TABLE alert_records (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id       CHAR(36) NOT NULL,
    site_id        VARCHAR(32) NOT NULL,
    alert_type     ENUM(
                     'unknown_aquatic',       -- 水产车但车牌不在白名单
                     'plate_mismatch',        -- 车牌识别与预期不符
                     'no_permit',             -- 无捕捞许可证
                     'permit_expired',        -- 证件已过期
                     'frequent_entry',        -- 24h 内过车超阈值
                     'suspicious_text'        -- 车身有可疑文字
                   ) NOT NULL,
    channel        ENUM('wechat','sms','platform','email') NOT NULL,
    recipients     JSON,                               -- 接收人列表
    sent_at        DATETIME(3),
    status         ENUM('pending','sent','failed','deduplicated') DEFAULT 'pending',
    error_msg      TEXT,
    INDEX idx_event   (event_id),
    INDEX idx_site_time (site_id, sent_at),
    INDEX idx_status  (status, sent_at)
) ENGINE=InnoDB;

-- ─── 模型性能日志（生产指标追踪）───
CREATE TABLE model_performance_log (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    model_version  VARCHAR(32) NOT NULL,
    log_date       DATE NOT NULL,
    camera_id      VARCHAR(64),
    total_frames   INT UNSIGNED DEFAULT 0,
    aquatic_detected INT UNSIGNED DEFAULT 0,
    plate_recognized INT UNSIGNED DEFAULT 0,
    low_conf_plate  INT UNSIGNED DEFAULT 0,       -- 低置信度车牌（< 0.80）
    false_positive_manual INT UNSIGNED DEFAULT 0, -- 人工标记的误报
    false_negative_manual INT UNSIGNED DEFAULT 0, -- 人工标记的漏报
    avg_inference_ms DECIMAL(6,2),
    p95_inference_ms DECIMAL(6,2),
    p99_inference_ms DECIMAL(6,2),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_version_date_cam (model_version, log_date, camera_id)
) ENGINE=InnoDB;
```

### 5.2 CI/CD 模型发布流水线

```yaml
# .github/workflows/model_release.yml
name: 模型发布流水线

on:
  push:
    tags:
      - 'model-v[0-9]+.[0-9]+'

env:
  REGISTRY: your-registry.com
  MODEL_BASE_PATH: s3://aquatic-cv-models

jobs:
  # ─── 阶段1：离线评估（Gate 1）───
  offline_evaluation:
    name: Gate1 离线指标评估
    runs-on: [self-hosted, gpu, linux]
    outputs:
      passed: ${{ steps.gate.outputs.passed }}
    steps:
      - uses: actions/checkout@v4
      - name: 下载模型权重
        run: |
          aws s3 cp $MODEL_BASE_PATH/${{ github.ref_name }}/best.pt models/

      - name: 运行离线评估
        run: |
          python scripts/evaluate_all.py \
            --model models/best.pt \
            --detection-data datasets/aquatic_vehicle_detection \
            --classification-data datasets/aquatic_vehicle_classification \
            --lpr-data datasets/license_plate_recognition \
            --ocr-data datasets/body_text_ocr \
            --output reports/offline_eval.json

      - name: Gate1 门控检查
        id: gate
        run: |
          python scripts/check_gate1.py --report reports/offline_eval.json
          # 检查项：mAP50≥0.87 / FPR≤5% / FNR≤7% / 车牌准确率≥96%

  # ─── 阶段2：模型压缩 + 导出（Gate 2）───
  model_packaging:
    name: Gate2 推理性能压测
    needs: offline_evaluation
    if: needs.offline_evaluation.outputs.passed == 'true'
    runs-on: [self-hosted, jetson-orin, linux]
    steps:
      - name: 导出 TensorRT INT8
        run: |
          python scripts/export_trt.py \
            --model models/best.pt \
            --calibration datasets/aquatic_vehicle_detection \
            --output artifacts/int8/

      - name: 边缘端压测（600s）
        run: |
          python scripts/benchmark_pipeline.py \
            --model-dir artifacts/ \
            --test-video data/benchmark_30min.mp4 \
            --duration 600 \
            --report reports/perf_gate.json
          # 验收：P95≤150ms / P99≤200ms / GPU显存≤8GB / 无崩溃

      - name: 量化精度验证（INT8 vs FP32 mAP 差 ≤ 1%）
        run: python scripts/verify_quantization.py

      - name: 上传 Artifacts 到 OSS
        run: |
          mc cp artifacts/ minio/models/${{ github.ref_name }}/
          # 同时上传 SHA256 校验文件

  # ─── 阶段3：灰度发布（Gate 3）───
  canary_deploy:
    name: Gate3 灰度发布
    needs: model_packaging
    runs-on: ubuntu-latest
    steps:
      - name: 推送至试点路口（1个节点）
        run: |
          python scripts/rolling_deploy.py \
            --nodes config/canary_nodes.yaml \
            --version ${{ github.ref_name }} \
            --batch-size 1 \
            --health-check-interval 60

      - name: 等待灰度观察（7天）
        run: |
          # 触发异步监控，7天后自动汇报指标
          python scripts/schedule_canary_check.py \
            --version ${{ github.ref_name }} \
            --check-after-days 7

  # ─── 阶段4：全量发布 ───
  full_deploy:
    name: 全量发布
    needs: canary_deploy
    if: github.event_name == 'workflow_dispatch'  # 人工触发全量
    runs-on: ubuntu-latest
    steps:
      - name: 批量更新所有边缘节点（滚动，每批 3 个）
        run: |
          python scripts/rolling_deploy.py \
            --nodes config/all_edge_nodes.yaml \
            --version ${{ github.ref_name }} \
            --batch-size 3 \
            --health-check-interval 120 \
            --auto-rollback-on-alert
```

---

## 6. 安全设计

### 6.1 网络安全

| 层级 | 具体措施 |
|------|---------|
| 传输层 | 边缘→云端：TLS 1.3（双向认证 mTLS）；摄像头→边缘：VPN 802.1Q 隔离 |
| 应用层 | API JWT Token（2h 过期）+ IP 白名单 + 请求频率限制（限速 1000 QPS） |
| 数据层 | 车牌字段 AES-256-GCM 加密存储；密钥托管 KMS（阿里云 KMS / HashiCorp Vault） |
| 审计 | 所有 API 操作记录操作人、时间戳、IP、请求体摘要，保留 1 年 |
| 模型文件 | SHA256 哈希验证（加载前校验，防止篡改）；模型文件仅 root 可读 |

### 6.2 隐私保护

```python
# 图片上传前自动脱敏（非车辆/车牌区域人脸模糊）
def anonymize_frame(frame: np.ndarray, vehicle_bboxes: list) -> np.ndarray:
    """
    使用 YOLOv8-face 检测人脸，对非感兴趣区域（非车辆、非车牌）进行高斯模糊
    """
    face_model = YOLO("yolov8n-face.pt")
    face_dets = face_model.predict(frame, conf=0.5)[0]

    result = frame.copy()
    for face_box in face_dets.boxes.xyxy.cpu().numpy():
        x1, y1, x2, y2 = map(int, face_box)
        # 检查是否与车辆 BBox 有交叉（车牌位置的人脸字符不模糊）
        if not any(compute_iou([x1,y1,x2,y2], vb) > 0.1 for vb in vehicle_bboxes):
            roi = result[y1:y2, x1:x2]
            result[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (51, 51), 0)

    return result
```

---

## 7. 成本估算

### 7.1 边缘硬件成本（单路口，标准配置）

| 组件 | 型号/规格 | 单价（元）| 数量 | 小计（元）|
|------|---------|---------|-----|--------|
| 推理计算盒 | Jetson Orin NX 16GB（工业版含散热） | 9,500 | 1 | 9,500 |
| 工业摄像头 | 海康 4K 星光夜视（H.265，宽动态） | 3,200 | 2 | 6,400 |
| 红外补光灯 | 50m 照射距离 | 1,200 | 2 | 2,400 |
| 4G/5G 路由 | 工业双卡（主/备链路） | 2,500 | 1 | 2,500 |
| UPS 电源 | 1KVA，4h 续航 | 2,800 | 1 | 2,800 |
| 工业机箱 | IP65 防护，带散热风扇 | 1,800 | 1 | 1,800 |
| 安装施工 | 立杆、布线、调试 | — | 1 | 3,000 |
| **单路口合计** | | | | **~28,400** |

### 7.2 云端运维成本（月度，10 个路口规模）

| 项目 | 规格 | 月费（元）|
|------|------|---------|
| ECS（API 服务集群，2台） | 8核16GB | 1,200 |
| RDS MySQL（主从，高可用） | 4核8GB | 1,500 |
| Redis（Sentinel 集群） | 2核4GB | 400 |
| Kafka（3 节点） | 自建 / 托管 | 800 |
| OSS 存储（截图，5TB/月增量） | 标准型 | 600 |
| 带宽（100Mbps，10路口上行） | 按流量 | 800 |
| MinIO（自建对象存储，3节点） | 硬件折旧 | 500 |
| **月合计** | | **~5,800** |
| **年合计** | | **~70,000** |
