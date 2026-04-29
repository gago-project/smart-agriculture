# 01. 数据采集、标注与预处理流水线（企业级）

## 1. 数据需求规格

### 1.1 各模型最低数据量（含质量要求）

| 模型 | 正样本 | 负样本 | 标注类型 | 质量要求 |
|------|--------|--------|----------|---------|
| 目标检测（全车辆） | 8,000 张 | — | BBox（YOLO格式） | 标注 IoU 一致性 ≥ 0.85 |
| 水产车二分类 | 3,000 张（水产车） | 4,500 张（其他货车） | 图像级 Label | 正负比 ≈ 2:3，困难负样本占 30% |
| 车牌检测（LPR Det） | 5,000 张 | — | BBox | 覆盖蓝/黄/绿/新能源牌型 |
| 车牌识别（LPR Rec） | 15,000 张纯车牌图 | — | 字符串 Label | 真实:合成 ≥ 6:4 |
| 车身 OCR 检测 | 3,000 张（含文字区域） | — | Polygon + 文字内容 | 含关键词样本 ≥ 40% |
| 车身 OCR 识别 | 10,000 张文本行切片 | — | 字符串 Label | 关键词样本 ≥ 30% |

### 1.2 数据分布要求（防止 Long-tail Data 问题）

水产车分类是典型的 **Long-tail Data（长尾数据）** 问题——特殊型号的水产车极少，普通货车极多。

#### 必须覆盖的子场景分布

| 维度 | 子场景 | 最低样本占比 |
|------|--------|------------|
| **时段** | 白天正常光照 | ≥ 50% |
| | 夜间补光（红外/白光） | ≥ 15% |
| | 清晨/黄昏低光（golden hour） | ≥ 10% |
| | 阴天散射光 | ≥ 15% |
| | 雨天 | ≥ 10% |
| **角度** | 正面（0-15°） | ≥ 35% |
| | 侧面（30-60°） | ≥ 30% |
| | 俯视（无人机，45-90°） | ≥ 20% |
| | 后视 | ≥ 15% |
| **距离** | 近景（5-15m） | ≥ 35% |
| | 中景（15-35m） | ≥ 40% |
| | 远景（35-60m） | ≥ 25% |
| **车牌状态** | 标准清晰 | ≥ 50% |
| | 轻度污损/磨损 | ≥ 20% |
| | 部分遮挡（遮挡 ≤ 30%） | ≥ 15% |
| | 夜间强反光 | ≥ 10% |
| | 低分辨率（车牌宽 ≤ 80px） | ≥ 15% |
| **省份车牌** | 粤/闽/浙/桂/琼（重点沿海省份） | 合计 ≥ 60% |

#### Class Imbalance（类别不平衡）处理策略

```python
# 数据集类别不平衡检测
from collections import Counter
import numpy as np

def analyze_class_distribution(dataset_dir: str) -> dict:
    """统计各类别样本数，识别不平衡问题"""
    class_counts = Counter()
    for label_file in Path(dataset_dir).glob("labels/**/*.txt"):
        with open(label_file) as f:
            for line in f:
                cls_id = int(line.split()[0])
                class_counts[cls_id] += 1

    total = sum(class_counts.values())
    imbalance_ratio = max(class_counts.values()) / max(min(class_counts.values()), 1)

    return {
        "counts": dict(class_counts),
        "imbalance_ratio": imbalance_ratio,  # > 10 则需处理
        "recommendation": "需要过采样/欠采样" if imbalance_ratio > 5 else "分布合理"
    }

# 处理策略（按不平衡程度选择）
# 轻度不平衡（ratio 2-5）：损失函数加权 class_weights
# 中度不平衡（ratio 5-20）：过采样（Copy-Paste增强）+ 欠采样
# 严重不平衡（ratio > 20）：Focal Loss + SMOTE + 合成数据
```

---

## 2. 数据采集方案

### 2.1 固定视频监控采集

```bash
# 方案A：按关键帧（I帧）抽取（适用于高质量数据采集）
ffmpeg -i "rtsp://user:pass@192.168.1.100:554/stream" \
  -vf "select='eq(pict_type,PICT_TYPE_I)'" \
  -vsync vfr -q:v 2 \
  "frames/cam01_%06d.jpg"

# 方案B：事件触发式抽帧（运动检测触发密集采集）
ffmpeg -i "rtsp://..." \
  -vf "select='gt(scene,0.015)',setpts=N/FRAME_RATE/TB" \
  -r 3 "frames/cam01_motion_%06d.jpg"

# 方案C：固定帧率（兜底方案，数据量大但重复率高）
ffmpeg -i "rtsp://..." -r 1 "frames/cam01_%06d.jpg"
```

**采集策略**：
- 每路口摄像头连续采集 **14 天**（覆盖工作日/周末/不同天气）
- 采集前确认摄像头分辨率 ≥ 1080P，夜间补光有效
- 每天 4 个时段重点采集：6:00-9:00、11:00-13:00、15:00-18:00、20:00-22:00

### 2.2 无人机航飞数据处理

```python
import subprocess
from pathlib import Path
import exiftool  # pip install pyexiftool

def process_drone_video(video_path: str, output_dir: str, fps: float = 2.0):
    """处理无人机视频：抽帧 + GPS 信息提取"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 抽帧（2fps，保持高质量）
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-r", str(fps),
        "-q:v", "2",        # JPEG 质量 95
        f"{output_dir}/frame_%06d.jpg"
    ], check=True)

    # 提取 GPS 元数据（用于地理标注）
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(video_path)
        gps_info = {
            "lat": metadata[0].get("Composite:GPSLatitude"),
            "lon": metadata[0].get("Composite:GPSLongitude"),
            "altitude": metadata[0].get("Composite:GPSAltitude"),
        }
    return gps_info
```

**无人机专项处理**：
- 俯视角透视矫正（Homography 变换，用于车牌辨识增强）
- 飞行高度 > 100m 的帧自动降低优先级（分辨率不足）
- 保留飞行轨迹数据（Trajectory Analysis），用于后续行为识别

### 2.3 合成数据扩充策略

#### 车牌合成（解决 Label Noise 和样本不足问题）

```python
import random
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import cv2

# 省份列表（按采集区域权重配置）
PROVINCE_WEIGHTS = {
    "粤": 0.30, "闽": 0.20, "浙": 0.15, "桂": 0.15,
    "琼": 0.10, "苏": 0.05, "沪": 0.05
}
CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
PLATE_TYPES = {
    "blue": {"bg": (0, 90, 200), "fg": (255, 255, 255), "size": (440, 140)},
    "yellow": {"bg": (255, 200, 0), "fg": (0, 0, 0), "size": (440, 140)},
    "green": {"bg": (0, 160, 60), "fg": (255, 255, 255), "size": (480, 140)},
}

def synthesize_plate(plate_type: str = "blue", augment: bool = True) -> tuple:
    province = random.choices(
        list(PROVINCE_WEIGHTS.keys()),
        weights=list(PROVINCE_WEIGHTS.values())
    )[0]
    plate_text = (province +
                  random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") +
                  "·" +
                  "".join(random.choices(CHARS, k=5)))

    cfg = PLATE_TYPES[plate_type]
    img = Image.new("RGB", cfg["size"], cfg["bg"])
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("fonts/plate_font.ttf", size=100)
    draw.text((20, 15), plate_text, fill=cfg["fg"], font=font)

    if augment:
        img_np = np.array(img)
        # 随机仿射变换（模拟拍摄角度）
        angle = random.uniform(-15, 15)
        M = cv2.getRotationMatrix2D((cfg["size"][0]//2, cfg["size"][1]//2), angle, 1.0)
        img_np = cv2.warpAffine(img_np, M, cfg["size"])
        # 随机噪声
        noise = np.random.normal(0, random.uniform(0, 15), img_np.shape).astype(np.uint8)
        img_np = cv2.add(img_np, noise)
        # 随机模糊（模拟运动/失焦）
        if random.random() < 0.3:
            k = random.choice([3, 5])
            img_np = cv2.GaussianBlur(img_np, (k, k), 0)
        img = Image.fromarray(img_np)

    return img, plate_text

# 批量合成
for i in range(5000):
    plate_type = random.choices(["blue","yellow","green"], weights=[0.6,0.3,0.1])[0]
    img, text = synthesize_plate(plate_type)
    img.save(f"datasets/lpr_rec_synthetic/{text}_{i:05d}.jpg")
```

---

## 3. 数据标注规范

### 3.1 工具选型与适用场景

| 工具 | 标注类型 | 优势 | 团队建议 |
|------|---------|------|---------|
| **Label Studio** | BBox / Polygon / Keypoint / 分类 | Web UI、团队协作、质控流程 | 主力工具（≥3人团队） |
| Labelme | BBox / Polygon / Mask | 轻量、本地部署 | 个人标注 |
| **PaddleLabel** | OCR 文本行（Polygon + 内容） | PaddleOCR 无缝对接 | OCR 专用 |
| CVAT | 视频标注（Tracking） | 支持 Multi-object Tracking 标注 | 视频序列标注 |

### 3.2 BBox 标注规范（目标检测）

#### 类别定义与标注 ID

```yaml
# dataset.yaml 类别定义
classes:
  0: vehicle_car           # 普通乘用车
  1: vehicle_truck_normal  # 普通货车（厢式/平板/冷链，无水箱）
  2: vehicle_aquatic       # 水产运输车（有水箱/罐体，核心类别）
  3: vehicle_tanker        # 油罐车（困难负样本，外形与水产车相似）
  4: license_plate         # 车牌区域
  5: body_text_region      # 车身文字区域
```

#### 标注质量规则

```
BBox 标注规则：
  ✅ 框需紧贴目标外轮廓，留白 ≤ 5px
  ✅ 截断目标（超出图像边缘）：可见面积 > 30% → 标注，设 truncated=1
  ✅ 严重遮挡（可见 < 30%）：标注但设 occluded=1，不参与 mAP 统计
  ✅ vehicle_aquatic 必须完整包含水箱/罐体区域
  ❌ 禁止对运动模糊严重（目标不可辨认）的图像强行标注
  ❌ 车辆镜像、仪表台、倒影不标注

IoU 一致性要求（多标注员同图标注后交叉验证）：
  同类别 BBox 标注 IoU ≥ 0.85 → 合格
  IoU 0.70-0.85 → 需仲裁
  IoU < 0.70 → 重新标注
```

### 3.3 水产运输车（vehicle_aquatic）判定标准

**正样本（满足以下任意一条）**：
| 特征 | 说明 |
|------|------|
| 圆柱形罐体 | 车厢为圆柱状，类似液罐车但通常为玻璃钢材质 |
| 方形水箱 | 大型方形透明/白色水箱，顶部有盖 |
| 充氧管道 | 车顶或车身侧面有充氧设备、软管连接 |
| 多水箱堆叠 | 多个小型水箱叠放于货厢中（开放式） |
| 车身文字 | 可见"渔""水产""养殖""水族"等字样 |

**困难负样本（必须专门采集作为训练负样本）**：
- 油罐车（圆柱形，与水产车外形最相似，是最常见的 False Positive 来源）
- 冷链冷藏车（封闭厢体，偶尔有误判）
- 混凝土搅拌车（圆柱形但有旋转滚筒，尾部明显不同）

### 3.4 OCR 文字标注规范

```json
// PaddleOCR Label 格式（label.txt 每行一条）
[
  {
    "transcription": "渔运0023",
    "points": [[120, 340], [380, 340], [380, 390], [120, 390]],
    "illegibility": false,
    "attributes": {
      "is_key_text": true,
      "text_type": "vehicle_number"
    }
  },
  {
    "transcription": "某某水产有限公司",
    "points": [[50, 400], [520, 400], [520, 445], [50, 445]],
    "illegibility": false,
    "attributes": {
      "is_key_text": true,
      "text_type": "company_name"
    }
  }
]
```

**is_key_text 触发条件**：
- 含"渔、水、养、鱼、虾、蟹、贝、海"等水产相关字
- 车辆编号（格式：字母数字组合，如"YY2023001"）
- 企业名称（含"水产""渔业""养殖场"等词）

### 3.5 标注质量控制（三轮质检）

```
第一轮：标注员 A 标注
第二轮：标注员 B 复核（重点检查 vehicle_aquatic 与 vehicle_tanker 的区分）
第三轮：算法工程师抽检（抽检率 10%）

自动化质检脚本（每次批量导入前运行）：

def run_quality_check(dataset_dir: str) -> QualityReport:
    issues = []
    for label_file in Path(dataset_dir).glob("labels/**/*.txt"):
        boxes = parse_yolo_labels(label_file)
        img_path = get_corresponding_image(label_file)
        img_w, img_h = get_image_size(img_path)

        for box in boxes:
            # 检查1：坐标合法性
            if not (0 <= box.cx <= 1 and 0 <= box.cy <= 1):
                issues.append(Issue("坐标越界", label_file, box))

            # 检查2：极小框（可能是错误标注）
            if box.w * img_w < 20 or box.h * img_h < 15:
                issues.append(Issue("极小框", label_file, box))

            # 检查3：重复框（IoU > 0.85 的同类别框）
            for other in boxes:
                if other != box and other.cls == box.cls:
                    if compute_iou(box, other) > 0.85:
                        issues.append(Issue("疑似重复标注", label_file, box))

    return QualityReport(total=count_boxes(dataset_dir), issues=issues)

# 验收标准：issue 率 < 0.5%
```

---

## 4. 数据预处理流水线

### 4.1 图像预处理标准

```python
import cv2
import albumentations as A

# 检测模型标准预处理（训练阶段）
detection_train_transform = A.Compose([
    # 尺寸标准化（Letterbox 保持宽高比）
    A.LongestMaxSize(max_size=640),
    A.PadIfNeeded(
        min_height=640, min_width=640,
        border_mode=cv2.BORDER_CONSTANT,
        value=(114, 114, 114)  # YOLOv8 默认 padding 颜色
    ),
    # 归一化（YOLOv8 内部处理，训练时不显式归一化）
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.3))

# 分类模型预处理（训练阶段）
classification_train_transform = A.Compose([
    A.Resize(224, 224),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # ImageNet 统计量
    A.ToTensorV2(),
])

# 推理阶段预处理（轻量，不含增强）
inference_transform = A.Compose([
    A.LongestMaxSize(max_size=640),
    A.PadIfNeeded(640, 640, border_mode=cv2.BORDER_CONSTANT, value=(114, 114, 114)),
])
```

### 4.2 Data Augmentation（数据增强）完整策略

| 增强类型 | 参数配置 | 适用模型 | 注意事项 |
|----------|---------|---------|---------|
| **Mosaic 拼接** | 4图拼接，p=1.0 | 检测 | YOLOv8内置；最后 15 epoch 关闭（close_mosaic=15） |
| **Mixup** | alpha=0.1，p=0.15 | 检测 | 与 Mosaic 配合使用 |
| **Copy-Paste** | p=0.3 | 检测 | 将 vehicle_aquatic 粘贴至新背景（正样本扩充） |
| 水平翻转 | p=0.5 | 检测/分类 | 车牌识别模型**关闭**（翻转后字符镜像） |
| 随机裁剪 | scale=(0.6,1.0)，p=0.5 | 分类 | 保证主体可见 > 50% |
| 亮度/对比度 | brightness=±0.3，contrast=±0.3 | 全部 | 模拟光照变化 |
| HSV 色调偏移 | h=0.015，s=0.7，v=0.4 | 检测 | YOLOv8内置 |
| 运动模糊 | kernel=5-15，p=0.2 | 全部 | 模拟运动车辆 |
| 高斯噪声 | var=0-25，p=0.2 | 全部 | 模拟低照度噪声 |
| 雨纹模拟 | p=0.1 | 检测/分类 | 雨天专项场景 |
| JPEG 压缩 | quality=50-95，p=0.3 | 全部 | 模拟视频压缩损失 |
| 透视变换 | scale=0.05，p=0.3 | 车牌识别 | 模拟拍摄角度偏差 |
| 随机遮挡（Cutout） | max_holes=4，p=0.2 | 检测 | 模拟车辆遮挡 |
| CLAHE | clip_limit=3.0，p=0.1 | 全部 | 夜间图像专项 |

### 4.3 Label Noise 处理

Label Noise（标签噪声）会严重影响模型精度，必须主动处理：

```python
# 方法1：置信度学习（Cleanlab）自动检测噪声标签
# pip install cleanlab
from cleanlab.filter import find_label_issues
import numpy as np

def detect_label_noise(train_probs: np.ndarray, train_labels: np.ndarray) -> list:
    """
    train_probs: [N, num_classes] 模型在训练集上的预测概率（交叉验证得到）
    train_labels: [N] 原始标注标签
    返回：疑似噪声标签的样本索引
    """
    label_issues = find_label_issues(
        labels=train_labels,
        pred_probs=train_probs,
        return_indices_ranked_by="self_confidence"
    )
    return label_issues  # 优先送人工复核


# 方法2：训练损失监控（损失异常高的样本通常是噪声标签）
class NoiseSampleDetector:
    def __init__(self, loss_threshold: float = 3.0):
        self.loss_threshold = loss_threshold
        self.loss_history = {}

    def record(self, sample_id: str, loss: float):
        if sample_id not in self.loss_history:
            self.loss_history[sample_id] = []
        self.loss_history[sample_id].append(loss)

    def get_suspicious_samples(self) -> list:
        """连续多个 epoch 损失都高于阈值的样本为可疑噪声"""
        suspicious = []
        for sid, losses in self.loss_history.items():
            if len(losses) >= 5 and np.mean(losses[-5:]) > self.loss_threshold:
                suspicious.append(sid)
        return suspicious
```

### 4.4 数据集划分策略

```python
from sklearn.model_selection import StratifiedGroupKFold
import pandas as pd

def split_dataset(metadata_df: pd.DataFrame) -> dict:
    """
    分层分组划分：
    - 分层（Stratified）：各子集类别分布一致
    - 分组（Group）：同一路口/同一天的数据不跨越 train/val/test
    """
    # metadata 包含：img_path, label, camera_id, date
    sgkf = StratifiedGroupKFold(n_splits=7)

    # 7折中取 5/1/1 = 71.4% / 14.3% / 14.3%
    splits = list(sgkf.split(
        metadata_df,
        metadata_df["label"],
        metadata_df["camera_id"]  # group by camera，防止同路口数据泄漏
    ))

    train_idx = splits[0][0]
    val_idx = splits[0][1][:len(splits[0][1])//2]
    test_idx = splits[0][1][len(splits[0][1])//2:]

    return {
        "train": metadata_df.iloc[train_idx],  # 70%
        "val": metadata_df.iloc[val_idx],       # 15%
        "test": metadata_df.iloc[test_idx],     # 15%（封存！）
    }

# 注意事项：
# test 集在整个项目周期内只用于最终评估，不参与任何超参调整决策
# 日常开发仅依据 val 集指标调整模型
```

### 4.5 数据集分布验证（每次新版数据集发布必执行）

```python
def validate_distribution(dataset_splits: dict) -> ValidationReport:
    """验证 train/val/test 的数据分布一致性"""
    results = {}
    for split_name, data in dataset_splits.items():
        class_dist = data["label"].value_counts(normalize=True).to_dict()
        time_dist = data["hour"].value_counts(normalize=True).to_dict()
        weather_dist = data["weather"].value_counts(normalize=True).to_dict()
        results[split_name] = {
            "class_distribution": class_dist,
            "time_distribution": time_dist,
            "weather_distribution": weather_dist,
        }

    # 检查 train 和 test 分布的 JS 散度（< 0.05 为合格）
    from scipy.spatial.distance import jensenshannon
    js_div = jensenshannon(
        list(results["train"]["class_distribution"].values()),
        list(results["test"]["class_distribution"].values())
    )
    assert js_div < 0.05, f"Train/Test 类别分布 JS 散度过大: {js_div:.4f}"
    return results
```

---

## 5. 数据版本管理（DVC）

```bash
# 初始化
dvc init && dvc remote add -d oss oss://aquatic-cv-data/dvc

# 每次数据更新
dvc add datasets/
git add datasets.dvc .gitignore
git commit -m "data: add v1.2 dataset (8234 images, +1200 nighttime)"
dvc push

# 版本命名约定
# v{major}.{minor}_{YYYYMMDD}_{变更描述}
# 示例：v1.2_20260601_add_nighttime_and_rain_scenes

# 查看数据集历史
dvc dag  # 显示数据处理 DAG
dvc metrics show  # 显示各版本数据质量指标
```

**数据质量指标追踪（dvc metrics）**：

```yaml
# metrics/data_quality.json（每版数据集自动生成）
{
  "version": "v1.2",
  "total_images": 8234,
  "class_counts": {
    "vehicle_aquatic": 3102,
    "vehicle_truck_normal": 4589,
    "vehicle_tanker": 543
  },
  "imbalance_ratio": 1.48,          # < 3 为合格
  "annotation_iou_consistency": 0.893,  # > 0.85 为合格
  "label_noise_rate": 0.012,         # < 0.02 为合格
  "nighttime_ratio": 0.168,          # > 0.15 为合格
  "coverage": {
    "provinces": ["粤","闽","浙","桂","琼"],
    "weather_types": ["sunny","cloudy","rainy"],
    "angle_types": ["front","side","overhead","rear"]
  }
}
```

---

## 6. 数据治理与合规

| 事项 | 具体措施 |
|------|---------|
| 隐私保护 | 非车辆区域人脸自动模糊（YOLOv8-face 检测后 Gaussian blur，训练前处理） |
| 传输安全 | 原始视频不出边缘节点；仅抽取帧经 AES-256 加密后传输 |
| 采集授权 | 采集前取得所有监控点位运营主体书面授权（模板归档） |
| 标注外包 | 外包商签 NDA；标注在私有 Label Studio 实例完成，不允许外部访问 |
| 数据保留 | 原始视频边缘端保留 3 天；标注数据永久保留；生产截图 OSS 保留 1 年 |
| 脱敏归档 | 车牌最后 2 位在归档时脱敏（`粤B123**`），原始加密存储 |
