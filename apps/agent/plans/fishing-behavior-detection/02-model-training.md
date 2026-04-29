# 02. 模型训练方案 — 六层算法全链路

## 1. 训练环境与实验管理

### 1.1 硬件配置

| 级别 | GPU | 显存 | 推荐用途 |
|------|-----|------|---------|
| **推荐** | RTX 4090 × 2 | 24GB×2 | 所有模型并行训练 |
| 企业级 | A100 × 4 | 80GB×4 | 大 Batch 快速迭代，LSTM 序列训练 |
| 最低可用 | RTX 3090 × 1 | 24GB | 单模型顺序训练 |

### 1.2 软件环境

```bash
conda create -n fishing-behavior python=3.10 -y
conda activate fishing-behavior

# 核心框架
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics==8.2.0            # YOLO 系列
pip install paddlepaddle-gpu==2.6.1       # CSRNet 等密度估计（PaddlePaddle 生态）

# 跟踪算法
pip install boxmot==10.0.43               # ByteTrack / DeepSORT / StrongSORT 统一封装
pip install lap==0.4.0                    # 匈牙利算法（ByteTrack 依赖）
pip install filterpy==1.4.5               # 卡尔曼滤波（SORT 核心）

# 聚类分析
pip install scikit-learn==1.4.0           # DBSCAN 聚类
pip install scipy==1.12.0                 # 空间距离计算

# 密度估计
pip install crowd-hat==0.1.0              # CSRNet / P2PNet 统一接口

# 实验追踪
pip install wandb==0.16.0 optuna==3.5.0

# 模型压缩
pip install torch-pruning==1.3.5
pip install onnxruntime-gpu==1.17.0

# 评估工具
pip install motmetrics==1.4.0             # 跟踪指标（MOTA、IDF1等）
pip install cleanlab==2.5.0               # Label Noise 检测
```

---

## 2. L1：人体检测（Human Detection）

### 2.1 模型与预训练策略

```python
# train_human_detection.py
from ultralytics import YOLO
import wandb

wandb.init(project="fishing-behavior-cv", name="yolov8m_human_detection_v1.0")

# 预训练模型选择（在 CrowdHuman 数据集上额外预训练的版本精度更高）
# 方案A（推荐）：COCO 预训练 → 水产场景微调（三段式迁移学习）
# 方案B：CrowdHuman 预训练 → 水产场景微调（人体检测任务更对口）
model = YOLO("yolov8m.pt")  # COCO 预训练（若有 CrowdHuman 版则用之）

results = model.train(
    data="datasets/human_detection/dataset.yaml",
    epochs=200,
    imgsz=640,
    batch=32,
    device="0,1",

    # ─── 优化器（Optimizer）───
    optimizer="AdamW",
    lr0=0.001,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,     # L2 Regularization

    # ─── Warmup ───
    warmup_epochs=5,
    warmup_momentum=0.8,
    warmup_bias_lr=0.1,

    # ─── 损失函数（Loss Function）权重 ───
    # 人体检测中，人群密集时 BBox 回归比分类更重要
    box=10.0,                # 提高定位损失权重（默认 7.5）
    cls=0.3,                 # 降低分类权重（类别少，分类相对简单）
    dfl=1.5,

    # ─── 关键数据增强（水面场景专项）───
    hsv_h=0.015,
    hsv_s=0.5,
    hsv_v=0.5,               # 较大亮度偏移（夜间→白天变化幅度大）
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.1,
    copy_paste=0.4,          # 重要！人体 Copy-Paste 扩充聚集正样本
    close_mosaic=20,

    # ─── 小目标优化 ───
    # 水面远距离人体（< 30px 高）是主要困难样本
    # 提高 IoU 阈值让模型更精确地定位小目标
    iou=0.55,               # NMS IoU（默认 0.7，降低避免漏检密集人群）

    patience=30,
    save_period=10,
    project="runs/human_detection",
    name="yolov8m_v1.0",
)
```

### 2.2 人体检测专项超参数调优（Optuna）

```python
import optuna
from ultralytics import YOLO

def human_detection_objective(trial):
    params = {
        "lr0": trial.suggest_float("lr0", 5e-4, 5e-3, log=True),
        "lrf": trial.suggest_float("lrf", 0.005, 0.05),
        "box": trial.suggest_float("box", 7.5, 15.0),   # 定位损失关键
        "cls": trial.suggest_float("cls", 0.2, 0.8),
        "copy_paste": trial.suggest_float("copy_paste", 0.2, 0.6),
        "iou": trial.suggest_float("iou", 0.40, 0.60),  # NMS IoU
    }
    model = YOLO("yolov8m.pt")
    results = model.train(
        data="datasets/human_detection/dataset.yaml",
        epochs=80,
        imgsz=640, batch=32, device="0",
        **params,
        project="runs/hpo_human", name=f"trial_{trial.number}",
    )
    metrics = results.results_dict
    # 优化目标：最大化 Recall（漏报代价高）× mAP（综合精度）
    recall = metrics.get("metrics/recall(B)", 0)
    mAP = metrics.get("metrics/mAP50(B)", 0)
    return recall * 0.6 + mAP * 0.4

study = optuna.create_study(direction="maximize", study_name="human_detection_hpo")
study.optimize(human_detection_objective, n_trials=40, n_jobs=2)
```

### 2.3 评估指标（Confusion Matrix 分析）

```python
from sklearn.metrics import confusion_matrix
import numpy as np

def analyze_human_detection(model, test_dataset, iou_threshold=0.50):
    """
    分析检测结果，特别关注：
    FPR（False Positive Rate）：水面波纹/漂浮物误检为人体
    FNR（False Negative Rate）：夜间/遮挡人体被漏检
    """
    tp, fp, fn, tn = 0, 0, 0, 0

    for img, gt_bboxes in test_dataset:
        preds = model.predict(img, conf=0.45)[0]

        matched_gt = set()
        for pred_box in preds.boxes:
            best_iou, best_gt_idx = 0, -1
            for i, gt_box in enumerate(gt_bboxes):
                iou = compute_iou(pred_box.xyxy[0].numpy(), gt_box)
                if iou > best_iou:
                    best_iou, best_gt_idx = iou, i
            if best_iou >= iou_threshold and best_gt_idx not in matched_gt:
                tp += 1  # True Positive：正确检出
                matched_gt.add(best_gt_idx)
            else:
                fp += 1  # False Positive：误报（波纹/漂浮物）

        fn += len(gt_bboxes) - len(matched_gt)  # False Negative：漏报

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0   # 精确率（Precision）
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0       # 召回率（Recall）
    fpr = fp / (fp + tn + 1e-6)                           # 误报率（FPR）
    fnr = fn / (fn + tp + 1e-6)                           # 漏报率（FNR）
    f1 = 2 * precision * recall / (precision + recall + 1e-6)

    print(f"Precision:   {precision:.4f}  目标 ≥ 0.90")
    print(f"Recall:      {recall:.4f}  目标 ≥ 0.92")
    print(f"F1-score:    {f1:.4f}  目标 ≥ 0.91")
    print(f"FPR（误报率）:{fpr:.4f}  目标 ≤ 0.03")
    print(f"FNR（漏报率）:{fnr:.4f}  目标 ≤ 0.05")
```

---

## 3. L2：人体跟踪（Human Tracking）

### 3.1 ByteTrack（主力跟踪算法）

```python
# tracking_pipeline.py
from boxmot import ByteTrack
import numpy as np

class HumanTracker:
    """
    ByteTrack：低置信度检测框也参与跟踪（解决遮挡后恢复问题）
    核心思想：高置信度框直接关联，低置信度框用于填补被遮挡轨迹

    目标：MOTA ≥ 0.78，ID Switch ≤ 5次/h
    """
    def __init__(self, config: dict):
        self.tracker = ByteTrack(
            track_high_thresh=0.6,   # 高置信度阈值（一级关联）
            track_low_thresh=0.1,    # 低置信度阈值（二级关联，遮挡恢复）
            new_track_thresh=0.7,    # 新目标初始化阈值
            track_buffer=30,         # 目标消失后保持 N 帧（25fps → 1.2s）
            match_thresh=0.8,        # IoU 匹配阈值（卡尔曼预测框）
            frame_rate=25,
        )
        self.trajectory_store = {}   # track_id → 轨迹历史（300s 窗口）
        self.max_trajectory_length = 25 * 300  # 25fps × 300s

    def update(self, detections: np.ndarray, frame_id: int) -> list:
        """
        输入：检测结果 [N, 6]（x1,y1,x2,y2,conf,class）
        输出：跟踪结果列表（track_id + 平滑 BBox + 轨迹）
        """
        tracks = self.tracker.update(detections, frame_id)

        results = []
        for track in tracks:
            track_id = int(track[4])
            bbox = track[:4].tolist()
            conf = float(track[5])

            # 更新轨迹存储（滑动窗口）
            if track_id not in self.trajectory_store:
                self.trajectory_store[track_id] = []
            self.trajectory_store[track_id].append({
                "frame_id": frame_id,
                "bbox": bbox,
                "center": [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2],
            })
            # 保留最近 300s 轨迹
            if len(self.trajectory_store[track_id]) > self.max_trajectory_length:
                self.trajectory_store[track_id].pop(0)

            results.append({
                "track_id": track_id,
                "bbox": bbox,
                "confidence": conf,
                "trajectory": self.trajectory_store[track_id][-50:],  # 最近 2s
            })

        return results

    def get_trajectory_pattern(self, track_id: int) -> str:
        """
        轨迹分析（Trajectory Analysis）：判断运动模式
        用于 L6 行为研判的辅助特征
        """
        if track_id not in self.trajectory_store:
            return "unknown"
        traj = self.trajectory_store[track_id]
        if len(traj) < 25:
            return "insufficient_data"

        centers = np.array([p["center"] for p in traj])
        total_displacement = np.linalg.norm(centers[-1] - centers[0])
        total_path_length = sum(
            np.linalg.norm(centers[i+1] - centers[i]) for i in range(len(centers)-1)
        )

        if total_displacement < 5:
            return "stationary"                # 静止（疑似作业）
        elif total_path_length / (total_displacement + 1e-6) > 3:
            return "meandering"                # 徘徊（疑似布网）
        else:
            return "directional"               # 定向移动（正常行船）
```

### 3.2 跟踪质量评估（MOTA / IDF1）

```python
import motmetrics as mm
import pandas as pd

def evaluate_tracking(gt_file: str, pred_file: str) -> dict:
    """
    使用 py-motmetrics 评估多目标跟踪性能
    标准指标（MOT Challenge 格式）：
    """
    acc = mm.MOTAccumulator(auto_id=True)

    gt_df = pd.read_csv(gt_file, header=None,
                         names=["frame","id","x","y","w","h","conf","cls","vis"])
    pred_df = pd.read_csv(pred_file, header=None,
                           names=["frame","id","x","y","w","h","conf","cls","vis"])

    for frame_id in sorted(gt_df["frame"].unique()):
        gt_frame = gt_df[gt_df["frame"] == frame_id]
        pred_frame = pred_df[pred_df["frame"] == frame_id]

        gt_ids = gt_frame["id"].values
        pred_ids = pred_frame["id"].values

        gt_boxes = gt_frame[["x","y","w","h"]].values
        pred_boxes = pred_frame[["x","y","w","h"]].values

        if len(gt_boxes) > 0 and len(pred_boxes) > 0:
            dist_matrix = mm.distances.iou_matrix(gt_boxes, pred_boxes, max_iou=0.5)
            acc.update(gt_ids, pred_ids, dist_matrix)

    mh = mm.metrics.create()
    summary = mh.compute(acc, metrics=[
        "mota",       # Multi-object Tracking Accuracy（MOTA）主指标
        "idf1",       # ID F1 Score（Re-identification 质量）
        "mostly_tracked",   # 大部分帧被正确跟踪的目标比例（MT）
        "mostly_lost",      # 大部分帧丢失的目标比例（ML）
        "num_switches",     # ID Switch 次数
        "num_fragmentations",  # 轨迹碎片化次数
        "precision",    # 轨迹精确率
        "recall",       # 轨迹召回率
    ])

    print(mm.io.render_summary(summary, namemap=mm.io.motchallenge_metric_names))
    print(f"\nMOTA 目标 ≥ 0.78，当前: {summary['mota'].values[0]:.4f}")
    print(f"ID Switch 目标 ≤ 5次/h，当前: {summary['num_switches'].values[0]}")
    return summary.to_dict()
```

### 3.3 Re-identification（跨摄像头重识别）

对于跨越多个摄像头的人员，需要 Re-ID 模型关联身份：

```python
# 使用 StrongSORT（ByteTrack + OSNet ReID）
from boxmot import StrongSORT
import torch

class CrossCameraReID:
    """
    跨摄像头目标重识别（Re-identification）
    场景：同一人从摄像头 A 区域进入摄像头 B 区域
    模型：OSNet（Omni-Scale Network），轻量高精度 ReID 网络
    """
    def __init__(self, reid_weights: str = "osnet_x0_25_market.pt"):
        self.tracker = StrongSORT(
            reid_weights=reid_weights,
            device=torch.device("cuda:0"),
            fp16=True,              # FP16 推理加速
        )
        self.camera_features = {}   # camera_id → 最近 N 帧的特征向量库

    def match_across_cameras(self, cam_a_features: np.ndarray,
                              cam_b_detections: list) -> list:
        """
        在摄像头 B 的新检测框中，找到摄像头 A 中出现过的同一人
        使用余弦相似度（cosine similarity）匹配外观特征
        """
        matches = []
        for det in cam_b_detections:
            query_feat = self._extract_feature(det["crop"])
            sims = [np.dot(query_feat, feat) /
                    (np.linalg.norm(query_feat) * np.linalg.norm(feat) + 1e-6)
                    for feat in cam_a_features]
            best_sim = max(sims) if sims else 0
            if best_sim > 0.75:  # 相似度阈值（cosine ≥ 0.75 视为同一人）
                matches.append({
                    "det": det,
                    "matched_cam_a_id": np.argmax(sims),
                    "similarity": best_sim
                })
        return matches
```

---

## 4. L3：区域聚集分析（Crowd Aggregation）

### 4.1 密度估计（CSRNet）

```python
import torch
import torch.nn as nn
import torchvision.models as models

class CSRNet(nn.Module):
    """
    Congested Scene Recognition Network（CSRNet）
    通过密度图估计人群数量和分布
    Loss Function: MSE Loss（预测密度图 vs 真实密度图）
    目标：MAE（Mean Absolute Error）≤ 2 人
    """
    def __init__(self):
        super().__init__()
        # 前端：VGG-16 前 10 层（预训练特征提取）
        vgg = models.vgg16(pretrained=True)
        self.frontend = nn.Sequential(*list(vgg.features.children())[:23])

        # 后端：膨胀卷积（保留空间分辨率，扩大感受野）
        self.backend = nn.Sequential(
            self._dilated_conv(512, 512, dilation=2),
            self._dilated_conv(512, 512, dilation=2),
            self._dilated_conv(512, 512, dilation=2),
            self._dilated_conv(512, 256, dilation=4),
            self._dilated_conv(256, 128, dilation=4),
            self._dilated_conv(128, 64, dilation=4),
        )
        self.output = nn.Conv2d(64, 1, 1)   # 输出单通道密度图

    def _dilated_conv(self, in_c, out_c, dilation):
        return nn.Sequential(
            nn.Conv2d(in_c, out_c, 3, padding=dilation, dilation=dilation),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        return self.output(x)  # [B, 1, H/8, W/8]

# 训练配置
CSRNET_CONFIG = {
    "batch_size": 8,
    "lr": 1e-5,              # CSRNet 收敛需要极小 lr
    "weight_decay": 5e-4,
    "epochs": 400,
    "loss": "mse",           # MSE Loss（密度图像素级均方误差）
    "scheduler": "cosine",
}

def train_csrnet(model, train_loader, val_loader, config):
    optimizer = torch.optim.AdamW(model.parameters(),
                                   lr=config["lr"],
                                   weight_decay=config["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["epochs"])
    criterion = nn.MSELoss()

    best_mae = float("inf")
    for epoch in range(config["epochs"]):
        # 训练（Backpropagation）
        model.train()
        for imgs, density_maps in train_loader:
            pred_density = model(imgs.cuda())
            # 上采样到与 GT 密度图相同尺寸
            pred_density = nn.functional.interpolate(
                pred_density, size=density_maps.shape[-2:])
            loss = criterion(pred_density, density_maps.cuda())
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # 验证
        model.eval()
        mae_list = []
        with torch.no_grad():
            for imgs, density_maps in val_loader:
                pred = model(imgs.cuda())
                pred_count = pred.sum().item()
                gt_count = density_maps.sum().item()
                mae_list.append(abs(pred_count - gt_count))

        mae = np.mean(mae_list)
        if mae < best_mae:
            best_mae = mae
            torch.save(model.state_dict(), "models/csrnet_best.pth")

        scheduler.step()
        print(f"Epoch {epoch}: MAE={mae:.2f} (目标 ≤ 2.0)")
```

### 4.2 空间聚类（DBSCAN）

```python
from sklearn.cluster import DBSCAN
import numpy as np

class CrowdAggregationDetector:
    """
    基于 DBSCAN 聚类的人群聚集区域检测
    DBSCAN（Density-Based Spatial Clustering of Applications with Noise）：
    - 无需预设聚类数量
    - 自动识别噪声点（离群人员）
    - 适合不规则形状的聚集区域
    """
    def __init__(self, config: dict):
        # eps：同一聚集簇的最大像素距离（根据摄像头分辨率和视野范围换算）
        # 实际距离 3 米 → 像素距离（需按摄像头参数标定）
        self.eps_pixels = config.get("eps_pixels", 80)
        self.min_samples = config.get("min_samples", 3)   # 簇最少 3 人
        self.alert_threshold = config.get("alert_threshold", 5)  # 预警阈值：5人
        self.alert_duration_s = config.get("alert_duration_s", 30)  # 持续 30s

        self.cluster_history = {}   # cluster_id → 持续时间记录

    def analyze(self, track_results: list, timestamp: float) -> list:
        """
        输入：当前帧所有人体跟踪结果
        输出：聚集簇列表（含预警级别）
        """
        if len(track_results) < self.min_samples:
            return []

        # 提取人体中心点坐标
        centers = np.array([
            [(t["bbox"][0]+t["bbox"][2])/2, (t["bbox"][1]+t["bbox"][3])/2]
            for t in track_results
        ])

        # DBSCAN 聚类
        clustering = DBSCAN(eps=self.eps_pixels, min_samples=self.min_samples)
        labels = clustering.fit_predict(centers)

        clusters = []
        unique_labels = set(labels) - {-1}  # -1 是噪声点

        for cluster_id in unique_labels:
            mask = labels == cluster_id
            cluster_centers = centers[mask]
            cluster_people = [track_results[i] for i in range(len(track_results)) if mask[i]]

            # 聚集区域边界框
            x_min, y_min = cluster_centers.min(axis=0)
            x_max, y_max = cluster_centers.max(axis=0)
            margin = 30
            cluster_bbox = [x_min-margin, y_min-margin, x_max+margin, y_max+margin]

            # 聚集持续时间追踪
            persistent_id = self._get_persistent_cluster_id(cluster_bbox)
            if persistent_id not in self.cluster_history:
                self.cluster_history[persistent_id] = timestamp
            duration_s = timestamp - self.cluster_history[persistent_id]

            # 统计持渔具人数
            persons_with_gear = sum(
                1 for p in cluster_people if p.get("class") == "person_with_gear"
            )

            # 预警级别判定
            count = int(mask.sum())
            alert_level = self._calc_alert_level(count, duration_s, persons_with_gear)

            clusters.append({
                "cluster_id": persistent_id,
                "person_count": count,
                "persons_with_gear": persons_with_gear,
                "bbox": cluster_bbox,
                "center": cluster_centers.mean(axis=0).tolist(),
                "duration_s": round(duration_s, 1),
                "alert_level": alert_level,
                "track_ids": [p["track_id"] for p in cluster_people],
            })

        return clusters

    def _calc_alert_level(self, count: int, duration_s: float,
                           persons_with_gear: int) -> str:
        """
        多维度综合预警级别
        LEVEL_3（红）：≥5人 + 持续≥30s + 有持渔具者 → 立即告警
        LEVEL_2（橙）：≥5人 + 持续≥30s
        LEVEL_1（黄）：≥3人 + 持续≥60s
        NORMAL：不触发预警
        """
        if (count >= self.alert_threshold and
            duration_s >= self.alert_duration_s and
            persons_with_gear >= 1):
            return "LEVEL_3"
        elif count >= self.alert_threshold and duration_s >= self.alert_duration_s:
            return "LEVEL_2"
        elif count >= 3 and duration_s >= 60:
            return "LEVEL_1"
        return "NORMAL"
```

---

## 5. L4：渔船识别（Vessel Detection）

### 5.1 渔船检测训练（YOLOv8l + SAHI）

```python
from ultralytics import YOLO
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

# 渔船通常是大目标，YOLOv8l 精度优先
model = YOLO("yolov8l.pt")

results = model.train(
    data="datasets/vessel_detection/dataset.yaml",
    epochs=200,
    imgsz=1280,              # 渔船细节多，使用更大输入尺寸
    batch=16,                # 大图 batch 相应减小
    device="0,1",
    optimizer="AdamW",
    lr0=0.0005,              # 大图训练用较小 lr
    lrf=0.01,
    weight_decay=0.0005,

    # 渔船专项增强
    fliplr=0.5,
    degrees=10.0,            # 船只可能倾斜（水面波浪）
    perspective=0.001,       # 透视变换（不同摄像头角度）
    scale=0.4,

    # 夜间场景关键
    hsv_v=0.5,               # 大亮度偏移（夜间↔白天）

    project="runs/vessel_detection",
    name="yolov8l_vessel_v1.0",
)

# SAHI（Slicing Aided Hyper Inference）切片推理
# 对于远距离小型渔船，切片推理大幅提升检测率
detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="runs/vessel_detection/yolov8l_vessel_v1.0/weights/best.pt",
    confidence_threshold=0.40,
    device="cuda:0",
)

def predict_with_sahi(image_path: str) -> list:
    """切片推理：将大图切成小块分别检测，再合并（适合远距离小渔船）"""
    result = get_sliced_prediction(
        image_path,
        detection_model,
        slice_height=640,
        slice_width=640,
        overlap_height_ratio=0.2,
        overlap_width_ratio=0.2,
    )
    return result.object_prediction_list
```

### 5.2 夜间渔船检测（红外+可见光融合）

```python
class InfraredVisibleFusion:
    """
    双通道融合：可见光（RGB）+ 红外（IR）
    夜间红外图像中，渔船发动机热源特征明显
    目标：夜间渔船 Recall 从 0.75 提升至 ≥ 0.88
    """
    def __init__(self, fusion_mode: str = "channel_concat"):
        self.fusion_mode = fusion_mode

    def fuse(self, visible: np.ndarray, infrared: np.ndarray) -> np.ndarray:
        """
        fusion_mode 选项：
          channel_concat：直接拼接为 4 通道（RGB+IR），需重训模型
          weighted_blend：加权融合为 RGB，兼容现有模型（边缘场景推荐）
        """
        if self.fusion_mode == "channel_concat":
            ir_gray = cv2.cvtColor(infrared, cv2.COLOR_BGR2GRAY)
            return np.concatenate([visible, ir_gray[:,:,np.newaxis]], axis=-1)

        elif self.fusion_mode == "weighted_blend":
            # 动态权重：越暗的区域 IR 权重越高
            mean_brightness = visible.mean()
            ir_weight = max(0.2, min(0.8, (60 - mean_brightness) / 60))
            vis_weight = 1 - ir_weight
            ir_enhanced = cv2.applyColorMap(
                cv2.cvtColor(infrared, cv2.COLOR_BGR2GRAY),
                cv2.COLORMAP_JET  # 伪彩色：热源区域显示为红色
            )
            return cv2.addWeighted(visible, vis_weight, ir_enhanced, ir_weight, 0)
```

---

## 6. L5：渔具识别（Gear Detection）

### 6.1 渔具检测训练（SAHI + 多尺度）

```python
# 渔具特点：细长、部分入水、与水面颜色相近
# 是六层中最困难的检测任务

model = YOLO("yolov8m.pt")

results = model.train(
    data="datasets/gear_detection/dataset.yaml",
    epochs=250,
    imgsz=1280,              # 大图：渔具细节需要高分辨率
    batch=8,                 # 显存受限
    device="0",
    optimizer="AdamW",
    lr0=0.001,

    # 渔具专项 Loss 权重
    # 渔具形状细长（DFL 对细长目标定位更重要）
    box=8.0,
    cls=0.4,
    dfl=2.0,                 # 提高 DFL 权重（细长目标 BBox 定位关键）

    # 关键增强：渔具通常颜色与水面接近
    hsv_s=0.8,               # 高饱和度偏移（水面蓝绿色 vs 渔网颜色）
    hsv_v=0.5,

    # 最大尺度覆盖（拖网可能跨越半个画面，刺网可能很细小）
    scale=0.5,
    mosaic=1.0,

    project="runs/gear_detection",
    name="yolov8m_gear_v1.0",
)
```

### 6.2 SAM 精细分割（证据存证）

```python
from segment_anything import SamPredictor, sam_model_registry
import torch

class GearSegmenter:
    """
    使用 SAM（Segment Anything Model）对检测到的渔具进行精细 Mask 分割
    用途：生成精确的渔具轮廓 Polygon，作为执法证据
    注意：SAM 推理较慢（~200ms/帧），仅在确认捕捞行为时触发
    """
    def __init__(self, checkpoint: str = "models/sam_vit_b.pth"):
        sam = sam_model_registry["vit_b"](checkpoint=checkpoint)
        sam.to(device="cuda")
        self.predictor = SamPredictor(sam)

    def segment_gear(self, image: np.ndarray,
                     gear_bbox: list) -> dict:
        """
        输入：原始图像 + 渔具 BBox（来自 L5 检测结果）
        输出：精细 Mask + Polygon 轮廓
        """
        self.predictor.set_image(image)

        input_box = np.array(gear_bbox)  # [x1,y1,x2,y2]
        masks, scores, _ = self.predictor.predict(
            box=input_box[None, :],
            multimask_output=True,
        )
        # 选择面积最大且置信度最高的 Mask
        best_mask_idx = np.argmax(scores)
        mask = masks[best_mask_idx]

        # 提取多边形轮廓（用于证据存档）
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        polygon = contours[0].reshape(-1, 2).tolist() if contours else []

        return {
            "mask": mask,
            "polygon": polygon,
            "score": float(scores[best_mask_idx]),
            "area_pixels": int(mask.sum()),
        }
```

---

## 7. L6：捕捞行为综合研判（Behavior Recognition）

### 7.1 规则引擎（Level 1，实时）

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BehaviorEvidence:
    person_count: int
    persons_with_gear: int
    vessel_count: int
    vessel_stationary: bool      # 船只静止超过 10 分钟
    gear_detected: bool          # 渔具可见
    gear_types: list
    crowd_level: str             # NORMAL / LEVEL_1 / LEVEL_2 / LEVEL_3
    trajectory_pattern: str      # stationary / meandering / directional
    gear_deployed: bool          # 渔具已布放（L4 属性）

class BehaviorRuleEngine:
    """
    Level 1 规则引擎：基于当前帧状态的快速研判（< 10ms）
    规则按风险等级从高到低排列，首个匹配的规则输出结果
    """
    RULES = [
        {
            "name": "confirmed_gear_deployment",
            "description": "渔具布放 + 船只停泊 + 人员聚集（最高置信捕捞）",
            "condition": lambda e: (
                e.gear_deployed and e.vessel_stationary and
                e.crowd_level in ["LEVEL_2", "LEVEL_3"]
            ),
            "result": "CONFIRMED",
            "confidence": 0.95,
        },
        {
            "name": "vessel_with_gear_visible",
            "description": "渔船停泊 + 渔具可见 + 有持渔具人员",
            "condition": lambda e: (
                e.vessel_stationary and e.gear_detected and e.persons_with_gear >= 2
            ),
            "result": "CONFIRMED",
            "confidence": 0.88,
        },
        {
            "name": "suspicious_crowd_on_vessel",
            "description": "船只上人群聚集 + 有渔具迹象",
            "condition": lambda e: (
                e.person_count >= 3 and e.vessel_count >= 1 and
                (e.gear_detected or e.persons_with_gear >= 1)
            ),
            "result": "SUSPICIOUS",
            "confidence": 0.70,
        },
        {
            "name": "vessel_loitering",
            "description": "渔船徘徊（往返轨迹）",
            "condition": lambda e: (
                e.vessel_stationary and e.trajectory_pattern == "meandering"
            ),
            "result": "SUSPICIOUS",
            "confidence": 0.60,
        },
    ]

    def evaluate(self, evidence: BehaviorEvidence) -> dict:
        for rule in self.RULES:
            if rule["condition"](evidence):
                return {
                    "result": rule["result"],
                    "confidence": rule["confidence"],
                    "matched_rule": rule["name"],
                    "description": rule["description"],
                }
        return {"result": "NORMAL", "confidence": 0.95, "matched_rule": "no_rule_matched"}
```

### 7.2 LSTM 时序模型（Level 2，滞后 30s）

```python
import torch
import torch.nn as nn

class FishingBehaviorLSTM(nn.Module):
    """
    双向 LSTM 时序行为识别
    输入：过去 30s 的多维特征序列（750帧×64维）
    输出：捕捞行为概率 ∈ [0,1]
    目标：在规则引擎的 SUSPICIOUS 结果上，进一步确认/排除（降低 FPR）
    """
    def __init__(self, input_size=64, hidden_size=128, num_layers=2,
                 dropout=0.3, num_classes=3):
        super().__init__()
        # BiLSTM：双向捕获前向和后向时序依赖
        self.lstm = nn.LSTM(
            input_size, hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout,
        )
        self.attention = nn.MultiheadAttention(hidden_size * 2, num_heads=4, batch_first=True)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),  # NORMAL / SUSPICIOUS / FISHING
        )

    def forward(self, x):
        # x: [B, T, input_size]（B=batch, T=750帧, input_size=64维特征）
        lstm_out, _ = self.lstm(x)            # [B, T, hidden*2]
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)  # 注意力
        pooled = attn_out.mean(dim=1)         # 时序平均池化 [B, hidden*2]
        return self.classifier(pooled)        # [B, 3]

# 训练配置
LSTM_CONFIG = {
    "input_size": 64,
    "hidden_size": 128,
    "num_layers": 2,
    "dropout": 0.3,
    "batch_size": 32,
    "sequence_length": 750,   # 30s × 25fps
    "lr": 0.001,
    "weight_decay": 1e-4,
    "epochs": 100,
    "scheduler": "cosine",
    # 类别权重（处理 Class Imbalance）
    "class_weights": [1.0, 1.5, 3.0],  # NORMAL / SUSPICIOUS / FISHING
}

# 训练
def train_lstm(model, train_loader, val_loader, config):
    # Focal Loss 处理长尾（FISHING 样本少）
    class FocalLoss(nn.Module):
        def __init__(self, gamma=2.0, weight=None):
            super().__init__()
            self.gamma = gamma
            self.weight = weight

        def forward(self, logits, labels):
            ce_loss = nn.functional.cross_entropy(logits, labels,
                                                   weight=self.weight, reduction="none")
            pt = torch.exp(-ce_loss)
            focal_loss = ((1 - pt) ** self.gamma) * ce_loss
            return focal_loss.mean()

    weights = torch.tensor(config["class_weights"]).cuda()
    criterion = FocalLoss(gamma=2.0, weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(),
                                   lr=config["lr"],
                                   weight_decay=config["weight_decay"])
```

### 7.3 两级联合研判逻辑

```python
def joint_behavior_decision(rule_result: dict, lstm_prob: dict) -> dict:
    """
    Level1（规则引擎）× Level2（LSTM）联合决策
    设计原则：
      - 降低 FPR：规则引擎 SUSPICIOUS → LSTM 进一步确认才告警
      - 控制 FNR：规则引擎 CONFIRMED 直接告警（不等 LSTM，避免漏报延迟）
    """
    rule_result_val = rule_result["result"]
    fishing_prob = lstm_prob.get("FISHING", 0)
    rule_conf = rule_result["confidence"]

    # 最终判断逻辑
    if rule_result_val == "CONFIRMED":
        # 规则确认 → 立即告警（不依赖 LSTM，避免 FNR 增加）
        return {
            "final_decision": "CONFIRMED",
            "confidence": rule_conf,
            "decision_basis": "rule_engine_confirmed",
            "alert_level": "CRITICAL",
        }
    elif rule_result_val == "SUSPICIOUS" and fishing_prob >= 0.80:
        # 规则可疑 + LSTM 高概率 → 确认告警
        return {
            "final_decision": "CONFIRMED",
            "confidence": (rule_conf + fishing_prob) / 2,
            "decision_basis": "rule_suspicious_lstm_confirmed",
            "alert_level": "HIGH",
        }
    elif rule_result_val == "SUSPICIOUS" and fishing_prob >= 0.50:
        # 规则可疑 + LSTM 中等概率 → 平台推送但不短信
        return {
            "final_decision": "SUSPICIOUS",
            "confidence": fishing_prob,
            "decision_basis": "rule_suspicious_lstm_uncertain",
            "alert_level": "MEDIUM",
        }
    else:
        return {
            "final_decision": "NORMAL",
            "confidence": 1 - fishing_prob,
            "decision_basis": "rule_normal_or_lstm_low",
            "alert_level": "NONE",
        }
```

---

## 8. 模型压缩（Pruning + Distillation + Quantization）

### 8.1 压缩目标（边缘端 Jetson Orin NX）

| 模型 | FP32 延迟 | INT8 延迟 | mAP 损失 | 压缩方法 |
|------|---------|---------|---------|---------|
| L1 人体检测 YOLOv8m | 310ms | 85ms | ≤ 1% | INT8 量化 |
| L2 ByteTrack | 15ms | — | — | 纯 CPU，轻量 |
| L3 CSRNet | 45ms | 20ms | MAE+0.3 | FP16 量化 |
| L4 渔船 YOLOv8l | 480ms | 130ms | ≤ 1.5% | INT8 + 剪枝 20% |
| L5 渔具 YOLOv8m | 310ms | 85ms | ≤ 1.5% | INT8 量化 |
| L6 LSTM（CPU） | 30ms | — | — | ONNX Runtime CPU |
| **六层合计** | **~1190ms** | **~365ms** | — | **目标 ≤ 500ms P95** |

### 8.2 知识蒸馏（L4 渔船检测）

```python
# Teacher：YOLOv8l（高精度，云端）
# Student：YOLOv8s（轻量，边缘）
# 目标：Student 以 1/4 参数量达到 Teacher 92% 精度

from torch.nn import functional as F

class VesselDistillationLoss(nn.Module):
    """
    Feature-level 蒸馏（不只是 logit 蒸馏）
    Teacher 和 Student 的中间特征图对齐，效果优于仅 KL 散度
    """
    def __init__(self, alpha=0.5, beta=0.5, temperature=4.0):
        super().__init__()
        self.alpha = alpha   # 任务损失权重
        self.beta = beta     # 蒸馏损失权重
        self.T = temperature

    def forward(self, student_logits, teacher_logits,
                student_features, teacher_features, task_loss):
        # Logit 蒸馏（KL 散度）
        soft_s = F.log_softmax(student_logits / self.T, dim=-1)
        soft_t = F.softmax(teacher_logits / self.T, dim=-1)
        kl_loss = F.kl_div(soft_s, soft_t, reduction="batchmean") * (self.T ** 2)

        # Feature 蒸馏（L2 距离，中间层特征对齐）
        feat_loss = F.mse_loss(student_features, teacher_features.detach())

        total = self.alpha * task_loss + self.beta * (0.7 * kl_loss + 0.3 * feat_loss)
        return total
```

### 8.3 模型版本门控

```
Gate 1（离线指标）：
  □ L1 人体：mAP50 ≥ 0.85，FNR ≤ 10%
  □ L2 跟踪：MOTA ≥ 0.70，ID Switch ≤ 20次/h
  □ L3 聚集：MAE ≤ 3.0，聚集 Precision ≥ 0.85
  □ L4 渔船：mAP50 ≥ 0.87，船型 Accuracy ≥ 0.85
  □ L5 渔具：mAP50 ≥ 0.80
  □ L6 行为：F1 ≥ 0.85，FPR ≤ 8%，FNR ≤ 8%

Gate 2（推理性能，Jetson Orin NX 压测）：
  □ 六层流水线 P95 ≤ 500ms
  □ GPU 显存峰值 ≤ 12GB
  □ 600s 压测无崩溃/OOM

Gate 3（灰度 7 天，1个站点）：
  □ 捕捞行为 FPR ≤ 5%
  □ 捕捞行为 FNR ≤ 5%
  □ 聚集预警误报率 ≤ 5%
  □ 系统可用性 ≥ 99%
  □ P0 故障 0 次
```
