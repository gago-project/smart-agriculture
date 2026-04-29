# 01. 数据采集、标注与预处理流水线

## 1. 数据需求规格

### 1.1 六大模型数据量要求

| 模型 | 正样本 | 负样本 | 标注类型 | 最低质量要求 |
|------|--------|--------|----------|------------|
| 人体检测（L1） | 10,000 张（含人体场景） | 3,000 张（空场景/误报场景） | BBox | 标注 IoU 一致性 ≥ 0.85 |
| 人体跟踪（L2） | 200 段视频（每段 ≥ 30s） | — | Tracking ID + BBox 序列 | 轨迹连续性 ≥ 90% |
| 区域聚集（L3） | 5,000 张（含密度图标注） | 2,000 张（1-2 人稀疏场景） | 密度图 / 点标注 | MAE 标注误差 ≤ 1 人 |
| 渔船检测（L4） | 8,000 张（含各船型） | 2,000 张（水面无船/波浪）| BBox + 类别 | 覆盖 5 种船型 |
| 渔具检测（L5） | 6,000 张（含各渔具类型） | 2,000 张（渔具入水/半可见）| BBox + Polygon | 覆盖 6 种渔具 |
| 捕捞行为（L6 LSTM） | 1,000 段正样本序列 | 1,000 段负样本序列 | 行为类别标签 + 时间戳 | 序列长度 30s，25fps |

### 1.2 场景覆盖矩阵（必须满足）

| 维度 | 子场景 | 最低占比 | 重要性 |
|------|--------|---------|-------|
| **时段** | 白天（6:00-18:00） | ≥ 40% | 基准 |
| | 黄昏/清晨（5:00-7:00 / 17:00-19:00） | ≥ 15% | 高风险时段 |
| | 夜间（19:00-5:00，红外补光） | ≥ 25% | 非法捕捞高发 |
| | 无补光纯夜间 | ≥ 5% | 极端场景 |
| **天气** | 晴天 | ≥ 35% | — |
| | 阴天/多云 | ≥ 25% | — |
| | 小雨 | ≥ 15% | — |
| | 大雨/暴雨 | ≥ 10% | 模型鲁棒性 |
| | 雾天（能见度 < 500m） | ≥ 10% | — |
| | 光照强烈（水面强反射） | ≥ 5% | 水面特有干扰 |
| **水面状态** | 平静水面 | ≥ 35% | — |
| | 轻度波浪 | ≥ 30% | 干扰检测 |
| | 大风浪（波高 > 0.5m） | ≥ 15% | 困难场景 |
| | 水草/漂浮物遮挡 | ≥ 10% | 误报来源 |
| | 水雾蒸腾（早晨） | ≥ 10% | — |
| **摄像头角度** | 岸基平视（10-30°俯角） | ≥ 40% | — |
| | 岸基大俯角（30-60°） | ≥ 30% | — |
| | 无人机俯视（60-90°） | ≥ 20% | 俯视场景 |
| | 水面无人船侧视 | ≥ 10% | — |
| **人群密度** | 1-3 人（稀疏） | ≥ 30% | 早期预警 |
| | 4-10 人（中等） | ≥ 40% | 主要场景 |
| | > 10 人（密集） | ≥ 20% | 聚集预警 |
| | 遮挡严重（人体 > 30% 被遮挡）| ≥ 10% | 跟踪困难场景 |

### 1.3 Long-tail Data（长尾数据）分析

捕捞行为识别的典型长尾分布：

```
非捕捞场景（负样本）：数量远多于捕捞场景（正样本）
  ├─ 正常行船（高频，每天数百次）
  ├─ 养殖工人日常作业（高频）
  ├─ 游客观光船（中频）
  └─ 捕捞作业（低频，但是核心正样本！）
       ├─ 合法养殖区内作业（极少）
       └─ 非法捕捞（极低频，核心目标）

处理策略：
  正负样本比 ≈ 1:3，严格控制
  使用 Copy-Paste 扩充捕捞正样本
  通过 Focal Loss 抑制简单负样本
  渔具类别不平衡：拖网 >> 刺网 >> 围网，需过采样
```

---

## 2. 数据采集方案

### 2.1 固定岸基监控采集

```bash
# 智能抽帧（事件触发 + 定时结合）
python scripts/smart_extractor.py \
  --camera-id cam_shuiku_01 \
  --rtsp "rtsp://admin:pass@192.168.10.100:554/stream1" \
  --normal-fps 1 \
  --event-fps 10 \            # 检测到运动时加密
  --motion-threshold 0.02 \
  --save-dir data/cam_shuiku_01/ \
  --duration-days 14

# 采集重点时段（每天自动加密采集）
PRIORITY_HOURS="5,6,7,17,18,19,20,21,22,23,0,1,2"  # 非法捕捞高发时段
```

**采集策略**：
- 每个站点连续采集 **21 天**（覆盖各天气、潮汐、作业周期）
- 正常时段 1 FPS，检测到运动目标时提升至 10 FPS
- 夜间强制保存每 5s 一帧（配合红外补光）
- 遇到特殊事件（聚集、渔船出现）自动触发 30s 高清录制存证

### 2.2 无人机巡查数据处理

```python
import subprocess
from pathlib import Path

def process_drone_mission(video_path: str, output_dir: str,
                           flight_altitude: float, gps_track: list):
    """
    无人机任务数据处理流水线
    flight_altitude: 飞行高度（米），用于估算地面分辨率
    gps_track: 飞行轨迹 GPS 坐标列表（Trajectory Analysis 数据源）
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 1. 自适应抽帧（低空高密，高空低密）
    fps = 3.0 if flight_altitude < 50 else 1.5
    subprocess.run([
        "ffmpeg", "-i", video_path, "-r", str(fps),
        "-q:v", "1",  # 最高质量（无人机数据昂贵）
        f"{output_dir}/frame_%06d.jpg"
    ], check=True)

    # 2. 地面分辨率估算（GSD：Ground Sampling Distance）
    sensor_width_mm = 6.3  # DJI Mavic 3 传感器宽度
    focal_length_mm = 24
    image_width_px = 5280
    gsd_cm = (flight_altitude * sensor_width_mm / focal_length_mm) / image_width_px * 100
    print(f"地面分辨率 GSD = {gsd_cm:.2f} cm/pixel")

    # 3. 俯视角透视矫正（对渔船/渔具标注预处理）
    if flight_altitude > 80:
        apply_perspective_correction(output_dir, gsd_cm)

    # 4. GPS 轨迹绑定（用于船只 Re-identification）
    bind_gps_to_frames(output_dir, gps_track)

    return {"frame_count": len(list(Path(output_dir).glob("*.jpg"))), "gsd_cm": gsd_cm}
```

### 2.3 跟踪标注专用视频数据集

```bash
# 使用 CVAT 进行视频序列跟踪标注
# 安装 CVAT（Docker版，支持多人协作）
docker compose -f cvat/docker-compose.yml up -d

# 标注任务配置
# - 标注模式：Tracking（视频逐帧跟踪）
# - 标注格式：MOT（Multiple Object Tracking）
# - 导出格式：MOT Challenge Format
# person_id, frame, x, y, w, h, conf, class, visibility
```

### 2.4 捕捞行为专项数据收集

**正样本（捕捞场景）获取路径**：

| 来源 | 数量 | 合规性 | 说明 |
|------|------|--------|------|
| 历史执法记录视频 | ~200段 | 有授权 | 执法机构提供，已脱敏 |
| 合作渔民演练记录 | ~300段 | 有授权 | 专项拍摄各类捕捞动作 |
| 公开数据集（FishVista等）| ~200段 | 开源 | 国际渔业监测数据集 |
| 仿真合成（3D引擎）| ~300段 | 自有 | 覆盖极稀缺捕捞场景 |

---

## 3. 数据标注规范

### 3.1 工具体系

| 工具 | 任务 | 优势 |
|------|------|------|
| **CVAT** | 视频跟踪标注（L2 数据集） | 支持 Track 模式，自动插值，多人协作 |
| **Label Studio** | BBox 标注（L1/L4/L5）+ 行为分类（L6） | Web UI、质控流程完善 |
| **LabelMe + 脚本** | Polygon 精细分割（渔具 Mask） | 支持多边形，导出 COCO 格式 |
| **密度图生成脚本** | 人群密度 Ground Truth（L3） | 高斯核生成密度图 |

### 3.2 各模块标注规范

#### L1 人体检测标注

```yaml
类别定义：
  0: person              # 普通人员（养殖工人/游客/执法人员）
  1: person_with_gear    # 持有渔具的人员（捕捞高风险标志）
  2: person_on_boat      # 在船只上的人员（结合 L4 联合研判）

BBox 规则：
  ✅ 紧贴人体外轮廓，留白 ≤ 5px
  ✅ 水面倒影中的人不标注
  ✅ 严重遮挡（可见 < 25%）→ occluded=1，仍需标注（跟踪算法需要）
  ✅ 截断人体（超出画面）→ truncated=1
  ❌ 水草、漂浮物误形似人体的区域 → 标注为困难负样本（difficult=1）
  特殊规则：远距离小人体（面积 < 30×60px）→ 仍需标注，标记 small=1
```

#### L2 跟踪数据标注（MOT 格式）

```
MOT Challenge 格式（每帧一行）：
  <frame_id>,<track_id>,<bb_left>,<bb_top>,<bb_width>,<bb_height>,<conf>,<class>,<visibility>

标注要求：
  □ 每个连续人体实体分配唯一且稳定的 track_id（整段视频不变）
  □ 被完全遮挡的帧：保留 track_id，设 conf=0（跟踪算法用于轨迹补全）
  □ 新人体入画：分配新 track_id，第一帧设 conf=1
  □ 人体离开画面：该 track_id 停止标注（不复用）
  □ 轨迹最短有效长度：≥ 10 帧（短于此的过路人不标注）

质控：
  标注员需确保同一物理人体的 track_id 在全视频中一致
  使用 py-motmetrics 工具计算标注员间 IoU 一致性（目标 ≥ 0.90）
```

#### L3 区域聚集标注（密度图）

```python
import numpy as np
import scipy.ndimage

def generate_density_map(img_shape: tuple, person_points: list,
                          sigma: float = 15.0) -> np.ndarray:
    """
    输入：图像尺寸 + 人体头部中心点列表（点标注）
    输出：密度图（每像素的人体密度值，积分 = 人数）

    sigma 参数：根据场景人体大小调整
      - 近距离（人体 > 100px 高）：sigma ≈ 20-30
      - 中距离（50-100px 高）：sigma ≈ 10-20
      - 远距离（< 50px 高）：sigma ≈ 5-10
    """
    density = np.zeros(img_shape[:2], dtype=np.float32)
    for (x, y) in person_points:
        if 0 <= x < img_shape[1] and 0 <= y < img_shape[0]:
            density[int(y), int(x)] = 1.0

    # 使用自适应高斯核（根据最近邻距离调整 sigma）
    density = scipy.ndimage.gaussian_filter(density, sigma=sigma)

    # 归一化：使积分等于人数
    if density.sum() > 0:
        density = density / density.sum() * len(person_points)

    return density  # 积分 ≈ 人数

# 验证：np.sum(density) ≈ len(person_points)，误差 < 0.01
```

#### L4 渔船检测标注

```yaml
类别定义：
  0: fishing_boat_small   # 小型渔船（< 8m，木船/玻璃钢船）
  1: fishing_boat_medium  # 中型渔船（8-15m，机动渔船）
  2: fishing_boat_large   # 大型渔船（> 15m，拖网船/围网船）
  3: speedboat            # 快艇/巡逻艇（非捕捞，应排除）
  4: raft                 # 竹排/浮排（养殖用，通常合法）
  5: unknown_vessel       # 无法分类的水面移动目标

作业状态标注（附加属性）：
  moving: true/false        # 是否在移动（静止可疑）
  gear_deployed: true/false # 是否已布放渔具（关键证据）
  night_lights: true/false  # 是否开灯（夜间捕捞特征）
```

#### L5 渔具检测标注

```yaml
类别定义：
  0: trawl_net       # 拖网（扇形展开，危害最大）
  1: purse_seine     # 围网（圆形/半圆，大型）
  2: gill_net        # 刺网（长条状，水面漂浮）
  3: fish_trap       # 地笼/虾笼（筒状，水面漂浮端可见）
  4: fishing_rod     # 鱼竿（线状）
  5: fish_cage       # 养殖网箱（合法，标注为负样本）

标注类型：BBox（初级）+ Polygon（精细，用于证据存证）
渔具入水部分处理：只标注水面可见部分，设 truncated=1（水下部分不可见）
困难样本：与水草/波浪相似的渔具 → 标注但设 difficult=1
```

#### L6 行为分类标注

```python
# 行为序列标注格式（JSON）
behavior_annotation = {
    "video_id": "cam_shuiku_01_20260501_220000",
    "duration_s": 30,
    "fps": 25,
    "behavior_label": "FISHING",  # FISHING / NORMAL / SUSPICIOUS / UNKNOWN
    "confidence": 1.0,             # 标注员置信度
    "evidence": {
        "vessel_type": "fishing_boat_small",
        "gear_types": ["gill_net"],
        "person_count": 3,
        "key_moments": [
            {"time_s": 8.2, "action": "gear_deployment"},   # 渔具布放时刻
            {"time_s": 24.7, "action": "gear_retrieval"},   # 收网时刻
        ]
    },
    "annotator": "A001",
    "review_status": "approved"  # pending / approved / rejected
}
```

### 3.3 标注质量控制（三轮质检）

```
第一轮：标注员 A（BBox 标注 + 类别）
第二轮：标注员 B（复核，重点审查 person_with_gear、fishing_boat 分类）
第三轮：算法工程师（10% 抽检 + 自动化质检脚本）

自动化质检项目（每批次入库前必跑）：
  □ BBox 坐标合法性（0 ≤ x,y,w,h ≤ 1）
  □ 极小框过滤（面积 < 10×20px 的人体框标记疑问）
  □ 重叠框检测（同类别 IoU > 0.85 → 疑似重复标注）
  □ 跟踪 ID 连续性（track_id 中断超过 3 帧需说明理由）
  □ 密度图积分误差（|density.sum() - point_count| > 0.1 → 重新生成）
  □ 行为标签与证据一致性（FISHING 必须有渔具或渔船证据）

Label Noise 检测（Cleanlab，每个 epoch 后运行）：
  • 模型预测概率与标注标签差异大的样本 → 优先人工复核
  • 连续多 epoch 高损失样本 → 推入标注复查队列
```

---

## 4. 数据预处理流水线

### 4.1 图像预处理标准

```python
import albumentations as A
import cv2

# ─── L1/L4/L5 检测模型训练预处理 ───
detection_train_transform = A.Compose([
    A.LongestMaxSize(max_size=640),
    A.PadIfNeeded(640, 640, border_mode=cv2.BORDER_CONSTANT, value=(114, 114, 114)),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.25))

# ─── L3 密度估计模型预处理 ───
density_transform = A.Compose([
    A.RandomCrop(512, 512),           # CSRNet 标准输入
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ─── L6 LSTM 序列预处理 ───
def extract_tracking_features(tracking_sequence: list) -> np.ndarray:
    """
    将跟踪轨迹序列转换为 LSTM 输入特征向量
    输入：30s × 25fps = 750 帧的跟踪结果列表
    输出：[750, feature_dim=64] 的特征矩阵
    """
    features = []
    for frame_data in tracking_sequence:
        frame_feat = [
            len(frame_data["persons"]),          # 人数
            len(frame_data["persons_with_gear"]),# 持渔具人数
            len(frame_data["vessels"]),          # 船只数
            len(frame_data["gears"]),            # 渔具数
            frame_data.get("crowd_density", 0),  # 聚集密度
            frame_data.get("vessel_speed", 0),   # 船速（像素/帧）
            # ... 共 64 维特征
        ]
        features.append(frame_feat)
    return np.array(features, dtype=np.float32)  # [T, 64]
```

### 4.2 水产/水面场景专项数据增强

```python
import albumentations as A
import numpy as np
import cv2

# ─── 水面专项增强策略 ───
water_surface_augmentations = A.Compose([
    # 波光粼粼（水面反光）
    A.RandomSunFlare(
        flare_roi=(0.0, 0.0, 1.0, 0.5),  # 只在水面区域（图像下半部）
        angle_lower=0, angle_upper=1,
        num_flare_circles_lower=3, num_flare_circles_upper=6,
        src_radius=200, p=0.15
    ),
    # 水雾模拟（早晨/雨后）
    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.4, alpha_coef=0.1, p=0.15),
    # 水面波纹模糊（运动模糊）
    A.MotionBlur(blur_limit=(3, 9), p=0.20),
    # 雨纹
    A.RandomRain(
        slant_lower=-10, slant_upper=10,
        drop_length=15, drop_width=1,
        drop_color=(200, 200, 200),
        rain_type="drizzle", p=0.15
    ),
    # 夜间光照
    A.RandomBrightnessContrast(brightness_limit=(-0.5, -0.2), contrast_limit=(-0.2, 0.2), p=0.25),
    # 镜头水雾（模拟摄像头镜头附着水分）
    A.GlassBlur(sigma=0.3, max_delta=2, iterations=1, p=0.05),
    # 标准增强
    A.HorizontalFlip(p=0.5),
    A.RandomScale(scale_limit=0.3, p=0.5),
    A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=30, val_shift_limit=20, p=0.5),
    A.GaussNoise(var_limit=(5, 30), p=0.3),
    A.JPEG(quality_lower=60, quality_upper=95, p=0.3),
])

# ─── 人群聚集专项增强（Copy-Paste 正样本扩充）───
def copy_paste_crowd(base_img: np.ndarray, person_crops: list,
                      target_count: int, area_polygon) -> tuple:
    """
    将人体 Crop 粘贴至水面背景，构造聚集场景（正样本合成）
    area_polygon: 禁捕区域多边形（人员只粘贴在水域范围内）
    """
    result = base_img.copy()
    new_bboxes = []
    for i in range(target_count):
        person = random.choice(person_crops)
        # 在禁捕区域内随机选取粘贴位置
        pos = sample_point_in_polygon(area_polygon)
        # 随机缩放（模拟远近距离）
        scale = random.uniform(0.5, 1.2)
        h, w = int(person.shape[0] * scale), int(person.shape[1] * scale)
        person_resized = cv2.resize(person, (w, h))
        # 泊松融合（边缘平滑）
        result = poisson_blend(result, person_resized, pos)
        new_bboxes.append([pos[0], pos[1], w, h])
    return result, new_bboxes
```

### 4.3 数据集划分策略

```python
def split_behavior_dataset(metadata_df, test_size=0.15, val_size=0.15):
    """
    捕捞行为数据集的分层分组划分
    分层依据：behavior_label（FISHING/NORMAL/SUSPICIOUS 分布均衡）
    分组依据：camera_id + date（同摄像头同天不跨 split，防止数据泄漏）
    """
    from sklearn.model_selection import StratifiedGroupKFold

    sgkf = StratifiedGroupKFold(n_splits=7)
    groups = metadata_df["camera_id"] + "_" + metadata_df["date"].astype(str)

    splits = list(sgkf.split(
        metadata_df,
        metadata_df["behavior_label"],  # 分层：确保各 split 行为分布一致
        groups                          # 分组：同摄像头同天不跨 split
    ))

    # 注意：test 集从第一次划分取，封存不用于超参决策
    train_idx = splits[0][0]
    remaining_idx = splits[0][1]
    val_idx = remaining_idx[:len(remaining_idx)//2]
    test_idx = remaining_idx[len(remaining_idx)//2:]

    return {
        "train": metadata_df.iloc[train_idx],   # 70%
        "val": metadata_df.iloc[val_idx],        # 15%
        "test": metadata_df.iloc[test_idx],      # 15%（封存）
    }
```

### 4.4 数据集版本管理（DVC）

```bash
# 版本化数据集
dvc init
dvc remote add -d oss oss://aquatic-behavior-datasets/dvc

# 数据集版本命名约定
# v{major}.{minor}_{YYYYMMDD}_{描述}
# 示例：v1.0_20260601_baseline / v1.1_20260701_add_nighttime_fishing

# 每版数据集质量指标追踪
cat metrics/data_quality_v1.1.json
{
  "version": "v1.1",
  "total_images": 31000,
  "class_counts": {
    "person": 18500,
    "person_with_gear": 4200,
    "fishing_boat_small": 3800,
    "gill_net": 2100,
    "trawl_net": 800,      // 长尾类别，需特别关注
    "purse_seine": 600     // 长尾类别
  },
  "imbalance_ratio": 3.1,          // < 5 可接受（渔具类别有长尾）
  "behavior_distribution": {
    "FISHING": 0.28,
    "NORMAL": 0.55,
    "SUSPICIOUS": 0.17
  },
  "annotation_iou_consistency": 0.887,  // > 0.85 合格
  "nighttime_ratio": 0.253,
  "tracking_completeness": 0.912        // > 0.90 合格
}
```

---

## 5. 数据治理

| 事项 | 具体措施 |
|------|---------|
| 隐私保护 | 人脸自动模糊处理（YOLOv8-face 检测后 GaussianBlur，训练前完成） |
| 视频安全 | 原始执法视频不出内网；标注在私有 CVAT/Label Studio 完成 |
| 采集授权 | 禁捕区摄像头采集前取得水利/渔业主管部门书面授权 |
| 证据合规 | 存证视频按司法鉴定规范保存（MD5+时间戳+链式签名） |
| 合规外包 | 标注外包团队 NDA；不提供执法视频原始素材，仅提供脱敏版本 |
| 数据保留 | 原始视频 7 天循环；证据片段永久保存（OSS 归档层）；标注集永久保留 |
