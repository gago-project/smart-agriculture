# 02. 模型训练方案 — 四大算法全链路（企业级）

## 1. 训练环境规格

### 1.1 硬件配置

| 级别 | GPU | 显存 | 存储 | 预估训练速度（YOLOv8m，640，bs=32） |
|------|-----|------|------|--------------------------------------|
| 最低可用 | RTX 3090 × 1 | 24GB | SSD 2TB | ~2h / 100 epoch |
| **推荐** | RTX 4090 × 2 | 24GB×2 | NVMe 4TB | ~45min / 100 epoch |
| 企业级 | A100 × 4 | 80GB×4 | NVMe 8TB RAID | ~15min / 100 epoch |
| 云端弹性 | 阿里云 A10（按需） | 24GB | OSS 挂载 | 按实际计费 |

### 1.2 软件环境

```bash
conda create -n aquatic-cv python=3.10 -y
conda activate aquatic-cv

# 深度学习框架
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121

# 目标检测（YOLO）
pip install ultralytics==8.2.0

# PaddlePaddle（OCR）
pip install paddlepaddle-gpu==2.6.1.post120 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html
pip install paddleocr==2.7.3

# 超参优化
pip install optuna==3.5.0

# 模型压缩
pip install torch-pruning==1.3.5

# 实验追踪
pip install wandb==0.16.0

# 数据质量
pip install cleanlab==2.5.0

# 量化（TensorRT 推理）
pip install tensorrt==8.6.1  # 需配合 CUDA 12.1

# 其他工具
pip install albumentations==1.4.0 opencv-python==4.9.0 dvc==3.38.0
```

### 1.3 实验追踪配置（W&B）

```python
import wandb

wandb.init(
    project="aquatic-vehicle-cv",
    entity="your-team",
    tags=["yolov8m", "detection", "v1.2"],
    config={
        "model": "yolov8m",
        "dataset_version": "v1.2",
        "epochs": 200,
        "batch_size": 32,
        "imgsz": 640,
        "optimizer": "AdamW",
    }
)
```

---

## 2. Step1：目标检测（Object Detection）

### 2.1 预训练模型（Pretrained Model）与迁移学习（Transfer Learning）

```
迁移学习策略（三段式 Fine-tuning）：

阶段1（Epoch 1-10）：冻结骨干（Freeze backbone），只训练检测头
  → 快速适应新类别，防止预训练特征被破坏
  → lr0 = 0.001，warmup

阶段2（Epoch 11-100）：解冻后6层，训练骨干后段 + 检测头
  → 特征迁移微调
  → lr0 = 0.0005

阶段3（Epoch 101-200）：全网络解冻，整体微调
  → 精细化调优
  → lr0 = 0.0001，余弦退火至 lrf=0.01
```

### 2.2 训练脚本（完整版）

```python
# train_detection.py
from ultralytics import YOLO
import wandb

def train_detection(config: dict):
    wandb.init(project="aquatic-vehicle-cv", name=config["run_name"])

    # 加载 COCO 预训练权重（Pretrained Model）
    model = YOLO("yolov8m.pt")

    results = model.train(
        data=config["data"],
        epochs=200,
        imgsz=640,
        batch=32,
        device="0,1",
        workers=8,

        # ─── Optimizer（优化器）配置 ───
        optimizer="AdamW",
        lr0=0.001,              # 初始 Learning Rate（学习率）
        lrf=0.01,               # 最终 lr = lr0 * lrf（余弦退火终点）
        momentum=0.937,
        weight_decay=0.0005,    # L2 Regularization（正则化）权重

        # ─── Warmup（热身）配置 ───
        warmup_epochs=5,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,

        # ─── Loss Function（损失函数）权重 ───
        box=7.5,                # BBox 回归损失（CIoU Loss）权重
        cls=0.5,                # 分类损失（BCE Loss）权重
        dfl=1.5,                # DFL（Distribution Focal Loss）权重

        # ─── Data Augmentation（数据增强）───
        hsv_h=0.015,            # 色调偏移
        hsv_s=0.7,              # 饱和度偏移
        hsv_v=0.4,              # 明度偏移
        degrees=0.0,            # 旋转角度
        translate=0.1,          # 平移比例
        scale=0.5,              # 缩放比例
        fliplr=0.5,             # 水平翻转概率
        mosaic=1.0,             # Mosaic 增强概率
        mixup=0.15,             # Mixup 增强概率
        copy_paste=0.3,         # Copy-Paste 增强（正样本扩充关键）
        close_mosaic=15,        # 最后 N epoch 关闭 Mosaic（提升精度）

        # ─── Overfitting 防控 ───
        dropout=0.0,            # 检测头 Dropout（分类头用，检测不启用）
        patience=30,            # 早停（Early Stopping）轮数

        # ─── Checkpoint 保存 ───
        save=True,
        save_period=10,         # 每 10 epoch 保存 Checkpoint
        val=True,
        project="runs/detection",
        name=config["run_name"],
        exist_ok=False,
        plots=True,
    )

    # 记录最终指标到 W&B
    metrics = results.results_dict
    wandb.log({
        "mAP50": metrics["metrics/mAP50(B)"],
        "mAP50-95": metrics["metrics/mAP50-95(B)"],
        "Precision": metrics["metrics/precision(B)"],
        "Recall": metrics["metrics/recall(B)"],
        "box_loss": metrics["train/box_loss"],
        "cls_loss": metrics["train/cls_loss"],
    })
    wandb.finish()
    return results

# 执行
config = {
    "data": "datasets/aquatic_vehicle_detection/dataset.yaml",
    "run_name": "yolov8m_detection_v1.2_exp001",
}
train_detection(config)
```

### 2.3 Loss Function（损失函数）详解

```
YOLOv8 检测任务总损失：
  L_total = λ_box × L_CIoU + λ_cls × L_BCE + λ_dfl × L_DFL

L_CIoU（Complete IoU Loss）：
  同时考虑 IoU、中心距、宽高比，比 L_MSE 更适合 BBox 回归
  目标：最大化预测框与 GT 框的 IoU

L_BCE（Binary Cross-Entropy）：
  目标分类损失，支持多标签（一个格子多类别）

L_DFL（Distribution Focal Loss）：
  将 BBox 边界建模为概率分布，提升小目标定位精度

车辆检测的重点：
  水产车（vehicle_aquatic）数量少 → 使用 Focal Loss 变体：
  α_aquatic = 2.0（提高正样本权重，减少 False Negative）
  γ = 2.0（抑制易分样本，聚焦困难样本）
```

### 2.4 Hyperparameter Tuning（超参数调优）

使用 Optuna 自动化超参搜索：

```python
import optuna

def objective(trial):
    config = {
        "lr0": trial.suggest_float("lr0", 1e-4, 1e-2, log=True),
        "lrf": trial.suggest_float("lrf", 0.001, 0.1, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True),
        "mosaic": trial.suggest_float("mosaic", 0.5, 1.0),
        "copy_paste": trial.suggest_float("copy_paste", 0.1, 0.5),
        "box": trial.suggest_float("box", 5.0, 10.0),
        "cls": trial.suggest_float("cls", 0.3, 1.0),
    }

    model = YOLO("yolov8m.pt")
    results = model.train(
        data="datasets/aquatic_vehicle_detection/dataset.yaml",
        epochs=50,      # 超参搜索用短 epoch
        imgsz=640,
        batch=32,
        device="0",
        **config,
        project="runs/hpo",
        name=f"trial_{trial.number}",
    )
    # 优化目标：最大化水产车 Recall（漏报代价 > 误报代价）
    return results.results_dict.get("metrics/recall(B)", 0)

study = optuna.create_study(direction="maximize", study_name="aquatic_cv_hpo")
study.optimize(objective, n_trials=50, n_jobs=2)
print("最优超参：", study.best_params)
```

---

## 3. Step2：水产车分类（Classification）

### 3.1 二分类训练

```python
# train_classification.py
from ultralytics import YOLO

model = YOLO("yolov8m-cls.pt")

results = model.train(
    data="datasets/aquatic_vehicle_classification/",
    epochs=100,
    imgsz=224,
    batch=64,
    device="0",
    optimizer="AdamW",
    lr0=0.0001,         # 分类 Fine-tuning 用更小 lr
    lrf=0.01,
    weight_decay=0.0001,
    dropout=0.2,        # 防止 Overfitting（过拟合）
    warmup_epochs=3,
    patience=20,
    augment=True,
    project="runs/classification",
    name="yolov8m_cls_v1",
)
```

### 3.2 Confusion Matrix（混淆矩阵）分析

```python
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt

def analyze_confusion_matrix(model, test_loader, class_names):
    all_preds, all_labels = [], []
    for imgs, labels in test_loader:
        preds = model.predict(imgs)
        all_preds.extend(preds)
        all_labels.extend(labels)

    cm = confusion_matrix(all_labels, all_preds)
    # 关键指标提取
    TN = cm[0][0]  # True Negative：正确排除（非水产车判为非水产车）
    FP = cm[0][1]  # False Positive：误报（非水产车误判为水产车）
    FN = cm[1][0]  # False Negative：漏报（水产车被漏检）
    TP = cm[1][1]  # True Positive：正确检出（水产车判为水产车）

    precision = TP / (TP + FP)  # 精确率
    recall = TP / (TP + FN)     # 召回率
    fpr = FP / (FP + TN)        # False Positive Rate（误报率）
    fnr = FN / (FN + TP)        # False Negative Rate（漏报率）
    f1 = 2 * precision * recall / (precision + recall)

    print(f"Precision（精确率）: {precision:.4f}  目标 ≥ 0.95")
    print(f"Recall（召回率）:    {recall:.4f}  目标 ≥ 0.96")
    print(f"F1-score:           {f1:.4f}  目标 ≥ 0.955")
    print(f"FPR（误报率）:      {fpr:.4f}  目标 ≤ 0.03")
    print(f"FNR（漏报率）:      {fnr:.4f}  目标 ≤ 0.04")

    # 可视化
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.savefig("confusion_matrix.png", dpi=150)

    # 生成详细报告
    print(classification_report(all_labels, all_preds, target_names=class_names))
```

### 3.3 类别不平衡处理（分类任务）

```python
import torch
from torch.utils.data import WeightedRandomSampler

def get_balanced_sampler(dataset, class_counts: dict) -> WeightedRandomSampler:
    """加权采样，使训练时各类别频率均衡"""
    class_weights = {cls: 1.0 / count for cls, count in class_counts.items()}
    sample_weights = [class_weights[label] for _, label in dataset]
    return WeightedRandomSampler(sample_weights, len(sample_weights))

# 损失函数加权（补充方案）
class_counts = {"aquatic": 3000, "non_aquatic": 4500}
pos_weight = torch.tensor([class_counts["non_aquatic"] / class_counts["aquatic"]])
criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
```

---

## 4. Step3：车牌识别（LPR）

### 4.1 车牌检测（YOLOv8n）

```python
model = YOLO("yolov8n.pt")

results = model.train(
    data="datasets/license_plate_detection/dataset.yaml",
    epochs=150,
    imgsz=640,
    batch=64,
    device="0",
    optimizer="AdamW",
    lr0=0.001,
    # 车牌专项增强（模拟各种拍摄条件）
    degrees=5.0,        # 轻微旋转（处理摄像头安装角度偏差）
    perspective=0.001,  # 透视变换（模拟俯视角）
    fliplr=0.0,         # 禁用水平翻转（车牌翻转后字符无效）
    flipud=0.0,         # 禁用垂直翻转
    scale=0.3,          # 缩放（覆盖远近距离）
    mosaic=0.5,         # 适度 Mosaic
    project="runs/lp_detection",
    name="yolov8n_lp_v1",
)
```

### 4.2 车牌识别（CRNN：CNN + BiLSTM + CTC）

```python
import torch
import torch.nn as nn

class BidirectionalLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.rnn = nn.LSTM(input_size, hidden_size, bidirectional=True, batch_first=True)
        self.linear = nn.Linear(hidden_size * 2, output_size)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.linear(out)

class CRNN(nn.Module):
    """
    CNN（特征提取）→ BiLSTM（序列建模）→ CTC（序列解码）
    Loss Function: CTC Loss（Connectionist Temporal Classification）
    适合不定长序列识别，无需对齐字符位置
    """
    def __init__(self, nc=1, nclass=79, nh=256):
        super().__init__()
        self.cnn = nn.Sequential(
            self._conv(nc,  64,  pooling=(2,2)),
            self._conv(64,  128, pooling=(2,2)),
            self._conv(128, 256),
            self._conv(256, 256, pooling=(2,1)),   # 纵向池化，保留横向时序
            self._conv(256, 512, bn=True),
            self._conv(512, 512, pooling=(2,1), bn=True),
            self._conv(512, 512, k=2, p=0, bn=True),
        )
        self.rnn = nn.Sequential(
            BidirectionalLSTM(512, nh, nh),
            BidirectionalLSTM(nh, nh, nclass),
        )

    def _conv(self, ic, oc, k=3, p=1, pooling=None, bn=False):
        layers = [nn.Conv2d(ic, oc, k, 1, p), nn.ReLU(inplace=True)]
        if bn: layers.append(nn.BatchNorm2d(oc))
        if pooling: layers.append(nn.MaxPool2d(pooling))
        return nn.Sequential(*layers)

    def forward(self, x):
        feat = self.cnn(x)                        # [B, C, 1, W]
        feat = feat.squeeze(2).permute(2, 0, 1)   # [W, B, C]（时序维度放首位）
        return self.rnn(feat)                      # [W, B, nclass]

# 训练配置
TRAIN_CONFIG = {
    "charset": "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁"
               "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ·",
    "img_h": 32,
    "img_w": 100,
    "batch_size": 256,
    "lr": 0.001,
    "epochs": 200,
    "weight_decay": 1e-4,
    "scheduler": "cosine",     # 余弦退火
    "early_stopping_patience": 20,
}

# CTC Loss 计算
ctc_loss = nn.CTCLoss(blank=0, reduction='mean', zero_infinity=True)
```

### 4.3 车牌识别评估指标

```python
def evaluate_lpr(model, test_dataset) -> dict:
    char_correct, char_total = 0, 0
    plate_correct, plate_total = 0, 0
    per_province = {}  # 分省份统计

    for img, gt_text in test_dataset:
        pred_text, confidence = model.predict(img)

        # 字符级准确率（Character Accuracy）
        for p, g in zip(pred_text, gt_text):
            char_total += 1
            if p == g: char_correct += 1

        # 完整车牌准确率（Plate Accuracy）
        plate_total += 1
        if pred_text == gt_text:
            plate_correct += 1

        # 分省份统计
        province = gt_text[0]
        if province not in per_province:
            per_province[province] = {"total": 0, "correct": 0}
        per_province[province]["total"] += 1
        if pred_text == gt_text:
            per_province[province]["correct"] += 1

    return {
        "character_accuracy": char_correct / char_total,   # 目标 ≥ 0.996
        "plate_accuracy": plate_correct / plate_total,      # 目标 ≥ 0.98
        "per_province": {
            p: v["correct"]/v["total"] for p, v in per_province.items()
        }
    }
```

---

## 5. Step4：车身 OCR（PaddleOCR 微调）

### 5.1 PP-OCRv4 Fine-tuning 配置

```yaml
# config/det_ppocr_v4_finetune.yml（文字检测 DB++ 微调）
Global:
  use_gpu: true
  epoch_num: 100
  log_smooth_window: 20
  print_batch_step: 50
  save_model_dir: ./output/det_body_text_v1/
  save_epoch_step: 10
  eval_batch_step: [0, 500]
  cal_metric_during_train: false
  pretrained_model: ./pretrain_models/ch_PP-OCRv4_det_train/best_accuracy
  checkpoints: null
  use_visualdl: false
  character_dict_path: ppocr/utils/ppocr_keys_v1.txt

Optimizer:
  name: Adam
  beta1: 0.9
  beta2: 0.999
  lr:
    name: Cosine                   # 余弦退火学习率调度
    learning_rate: 0.0001          # Fine-tuning 用小 lr
    warmup_epoch: 2
  regularizer:
    name: L2                       # L2 Regularization（正则化）
    factor: 5.0e-05

Architecture:
  model_type: det
  algorithm: DB
  Transform: null
  Backbone:
    name: ResNet
    layers: 50
    dcn_stage: [false, true, true, true]   # Deformable Conv（可变形卷积）
  Neck:
    name: LKPAN
  Head:
    name: DBHead
    k: 50                          # 二值化阈值扩展系数

Loss:
  name: DBLoss
  balance_loss: true
  main_loss_type: DiceLoss        # Dice Loss（文字检测常用）
  alpha: 5
  beta: 10
  ohem_ratio: 3                  # OHEM（在线困难样本挖掘）

Train:
  dataset:
    name: SimpleDataSet
    data_dir: ./train_data/body_text_ocr/train/images/
    label_file_list: ["./train_data/body_text_ocr/train/label.txt"]
    transforms:
      - DecodeImage
      - DetLabelEncode
      - IaaAugment:
          augmenter_args:
            - { type: Fliplr, args: { p: 0.5 } }
            - { type: Affine, args: { rotate: [-10, 10] } }
      - EastRandomCropData:
          size: [960, 960]
          max_tries: 50
          keep_ratio: true
      - MakeBorderMap
      - MakeShrinkMap
      - NormalizeImage
      - ToCHWImage
      - KeepKeys:
          keep_keys: [image, threshold_map, threshold_mask, shrink_map, shrink_mask]
  loader:
    shuffle: true
    drop_last: false
    batch_size_per_card: 8        # DB++ 显存消耗大，batch 不宜过大
    num_workers: 4
```

### 5.2 OCR 识别模型（SVTR 微调配置关键项）

```yaml
# config/rec_ppocr_v4_finetune.yml
Global:
  pretrained_model: ./pretrain_models/ch_PP-OCRv4_rec_train/best_accuracy
  epoch_num: 100
  character_dict_path: ppocr/utils/ppocr_keys_v1.txt  # 中文字符集 6625 个字
  max_text_length: 25                                   # 最大车身文字长度

Architecture:
  model_type: rec
  algorithm: SVTR_LCNet          # Transformer + 轻量级 CNN 联合架构
  Transform: null
  Backbone:
    name: MobileNetV1Enhance
    scale: 0.5
    last_conv_stride: [1, 2]
  Head:
    name: MultiHead
    head_list:
      - CTCHead:
          Neck:
            name: svtr
            dims: 64
            depth: 2
            hidden_dims: 120
            use_guide: True
      - SARHead:              # SAR Head（校正识别头，处理弯曲文字）
          enc_dim: 512
          max_text_length: 25

Loss:
  name: MultiLoss
  loss_config_list:
    - CTCLoss                  # CTC Loss（主损失）
    - SARLoss                  # SAR Loss（辅助损失，提升弯曲文字）

Optimizer:
  name: AdamW
  lr:
    name: Cosine
    learning_rate: 0.0005
    warmup_epoch: 5
  regularizer:
    name: L2
    factor: 3.0e-05

Train:
  loader:
    batch_size_per_card: 128    # 识别网络轻量，batch 可较大
```

### 5.3 关键词过滤与后处理

```python
import re

# 水产行业关键词字典（动态可配置）
AQUATIC_KEYWORDS = {
    "industry": ["渔", "水产", "养殖", "水族", "渔业", "渔港"],
    "species": ["鱼", "虾", "蟹", "贝", "海鲜", "鳗", "鳖"],
    "institution": ["渔政", "水产局", "海洋", "捕捞"],
    "patterns": [
        r"渔\d{4,}",           # 渔字头编号（如：渔20230012）
        r"[A-Z]{2}\d{6,8}",   # 渔船登记号格式
        r"[粤闽浙桂琼苏沪]渔\w+",  # 地区渔船编号
    ]
}

def extract_key_texts(ocr_results: list, min_confidence: float = 0.70) -> dict:
    """
    输入：PaddleOCR 返回 [[[bbox_points], (text, conf)], ...]
    输出：结构化提取结果
    """
    key_texts, all_texts = [], []

    for item in ocr_results:
        if not item: continue
        bbox_points, (text, conf) = item
        if conf < min_confidence:
            continue

        text_info = {
            "text": text,
            "confidence": round(conf, 4),
            "bbox": bbox_points,
            "is_key": False,
            "match_reason": None,
        }

        # 关键词匹配
        for category, keywords in AQUATIC_KEYWORDS.items():
            if category == "patterns":
                for pattern in keywords:
                    if re.search(pattern, text):
                        text_info["is_key"] = True
                        text_info["match_reason"] = f"pattern:{pattern}"
                        break
            else:
                for kw in keywords:
                    if kw in text:
                        text_info["is_key"] = True
                        text_info["match_reason"] = f"{category}:{kw}"
                        break
            if text_info["is_key"]:
                break

        all_texts.append(text_info)
        if text_info["is_key"]:
            key_texts.append(text_info)

    return {
        "key_texts": key_texts,
        "all_texts": all_texts,
        "has_aquatic_mark": len(key_texts) > 0,
        "key_text_count": len(key_texts),
    }
```

---

## 6. 模型压缩工程（Pruning + Distillation + Quantization）

### 6.1 剪枝（Pruning）

```python
import torch_pruning as tp
import torch

def prune_yolo_model(model_path: str, pruning_ratio: float = 0.3):
    """
    结构化剪枝（L1-norm 通道剪枝）
    目标：参数量减少 30%，mAP 损失 ≤ 0.5%
    """
    model = YOLO(model_path).model.eval()

    # 构建依赖图
    example_input = torch.randn(1, 3, 640, 640)
    DG = tp.DependencyGraph()
    DG.build_dependency(model, example_inputs=example_input)

    # 选择剪枝策略（L1 范数，剪掉权重绝对值最小的通道）
    pruner = tp.pruner.MagnitudePruner(
        model,
        example_inputs=example_input,
        importance=tp.importance.MagnitudeImportance(p=1),  # L1 范数
        global_pruning=False,
        pruning_ratio=pruning_ratio,
        ignored_layers=[model.model[-1]],  # 保留检测头不剪枝
    )

    # 执行剪枝
    pruner.step()

    # 剪枝后必须重新微调（Fine-tuning）恢复精度
    print(f"剪枝后参数量: {sum(p.numel() for p in model.parameters()):,}")
    return model

# 剪枝后微调（Epoch 减少到原来 30%，lr 降低 10 倍）
def finetune_after_pruning(pruned_model, data_config: dict):
    model = YOLO(pruned_model)
    model.train(
        data=data_config["data"],
        epochs=60,            # 精简 epoch
        lr0=0.0001,           # 降低 lr（避免损坏剪枝后的权重分布）
        freeze=0,             # 全层解冻微调
        patience=15,
        project="runs/pruning",
        name="pruned_finetune_v1",
    )
```

### 6.2 知识蒸馏（Knowledge Distillation）

```python
import torch
import torch.nn.functional as F

class DistillationLoss(nn.Module):
    """
    Teacher（YOLOv8l，高精度）→ Student（YOLOv8n，轻量）
    目标：Student 以 1/4 参数量达到 Teacher 90% 的精度

    总损失 = α × L_task（学生自身任务损失）
           + β × L_distill（与教师输出的 KL 散度）
    """
    def __init__(self, alpha: float = 0.4, beta: float = 0.6, temperature: float = 4.0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.T = temperature   # 温度参数：T↑ → 软标签分布更平滑

    def forward(self, student_logits, teacher_logits, task_loss):
        # 蒸馏损失（KL 散度）
        soft_student = F.log_softmax(student_logits / self.T, dim=-1)
        soft_teacher = F.softmax(teacher_logits / self.T, dim=-1)
        distill_loss = F.kl_div(soft_student, soft_teacher, reduction='batchmean') * (self.T ** 2)

        total_loss = self.alpha * task_loss + self.beta * distill_loss
        return total_loss, distill_loss

# 蒸馏训练流程
def train_with_distillation(teacher_path: str, student_config: dict):
    teacher = YOLO(teacher_path).model.eval()
    student = YOLO("yolov8n.pt").model.train()

    criterion = DistillationLoss(alpha=0.4, beta=0.6, temperature=4.0)
    optimizer = torch.optim.AdamW(student.parameters(), lr=0.001)

    for epoch in range(150):
        for imgs, targets in train_loader:
            with torch.no_grad():
                teacher_out = teacher(imgs)

            student_out, task_loss = student(imgs, targets)
            total_loss, distill_loss = criterion(student_out, teacher_out, task_loss)

            optimizer.zero_grad()
            total_loss.backward()    # Backpropagation（反向传播）
            optimizer.step()

        # 每 10 epoch 在 val 集评估
        if epoch % 10 == 0:
            val_metrics = validate(student, val_loader)
            wandb.log({"epoch": epoch, "distill_loss": distill_loss.item(), **val_metrics})
```

### 6.3 量化（Quantization）：FP32 → FP16 → INT8

```python
from ultralytics import YOLO

model = YOLO("runs/detection/best.pt")

# FP32 基准（不量化，用于精度对比）
# 推理速度 = 1× 基准

# FP16 量化（TensorRT FP16）
model.export(
    format="engine",
    half=True,            # FP16
    int8=False,
    device=0,
    workspace=4,          # TensorRT workspace (GB)
    simplify=True,
    batch=1,
)
# 精度损失：mAP ≈ -0.1%，速度提升 ≈ 1.8-2×

# INT8 量化（TensorRT INT8，需要校准数据）
model.export(
    format="engine",
    half=False,
    int8=True,            # INT8
    data="datasets/aquatic_vehicle_detection/dataset.yaml",  # 校准集（≥1000张）
    device=0,
    workspace=4,
    simplify=True,
    batch=1,
)
# 精度损失：mAP ≈ -0.8%，速度提升 ≈ 3-4×，显存减半

# 量化对比验证（必须在 test 集上执行）
def compare_quantization_accuracy():
    results = {}
    for precision, model_path in [
        ("FP32", "models/best.pt"),
        ("FP16", "models/best_fp16.engine"),
        ("INT8", "models/best_int8.engine"),
    ]:
        m = YOLO(model_path)
        metrics = m.val(data="datasets/aquatic_vehicle_detection/dataset.yaml", split="test")
        results[precision] = {
            "mAP50": metrics.box.map50,
            "mAP50-95": metrics.box.map,
            "inference_ms": metrics.speed["inference"],
        }
        print(f"{precision}: mAP50={results[precision]['mAP50']:.4f}, "
              f"推理={results[precision]['inference_ms']:.1f}ms")

    # 验证 INT8 vs FP32 mAP 损失 ≤ 1%
    assert abs(results["FP32"]["mAP50"] - results["INT8"]["mAP50"]) <= 0.01, \
        "INT8 量化精度损失超过 1%，需检查校准数据"
    return results
```

---

## 7. 模型版本门控（三层 Gate）

### Gate 1：离线指标门控（训练完成后）

```python
OFFLINE_GATES = {
    "vehicle_detection": {
        "mAP50": 0.87,           # 最低可接受
        "mAP50_target": 0.92,    # 目标值
        "aquatic_recall": 0.93,  # 水产车召回率（漏报代价高）
    },
    "classification": {
        "precision": 0.90,
        "recall": 0.93,
        "f1": 0.915,
        "fpr": 0.05,             # False Positive Rate ≤ 5%
    },
    "lpr": {
        "plate_accuracy": 0.96,
        "character_accuracy": 0.99,
    },
    "ocr": {
        "key_recall": 0.85,
    }
}

def check_offline_gates(metrics: dict, model_type: str) -> bool:
    gates = OFFLINE_GATES[model_type]
    passed = True
    for metric, threshold in gates.items():
        val = metrics.get(metric, 0)
        status = "✅" if val >= threshold else "❌"
        print(f"  {status} {metric}: {val:.4f} (门控: ≥{threshold})")
        if val < threshold:
            passed = False
    return passed
```

### Gate 2：推理性能门控（边缘设备压测）

```bash
# 在 Jetson Orin NX 上运行四步流水线压测
python benchmark_pipeline.py \
  --model-dir models/v1.2/ \
  --test-video data/benchmark_video.mp4 \
  --duration 600 \           # 压测 10 分钟
  --report-path reports/perf_gate_v1.2.json

# 验收标准：
# P95 端到端延迟 ≤ 150ms
# P99 延迟 ≤ 200ms
# GPU 显存峰值 ≤ 8GB
# 10 分钟内无 OOM / 崩溃
```

### Gate 3：线上 A/B 门控（灰度 7 天）

```
灰度策略：
  新模型在 1 个试点路口运行（流量 100%，旧模型并行运行用于对比）
  7 天后统计：
  □ 车牌识别率 ≥ 上版本 -0.5%
  □ 水产车 FPR ≤ 5%（目标 ≤ 3%）
  □ 水产车 FNR ≤ 7%（目标 ≤ 4%）
  □ 系统可用性 ≥ 99%
  □ 无 P0 级故障

通过以上全部条件 → 全量推送
任一未通过 → 保留旧模型，触发紧急分析
```

---

## 8. 训练产物归档规范

```
models/
├── detection/
│   └── v1.2_20260601/
│       ├── best.pt              # PyTorch FP32 原始权重
│       ├── best_fp16.engine     # TensorRT FP16（云端）
│       ├── best_int8.engine     # TensorRT INT8（边缘）
│       ├── best.onnx            # ONNX 通用格式
│       ├── metrics_offline.json # 离线评估指标快照
│       ├── metrics_gate.json    # 三层 Gate 通过记录
│       ├── model_card.md        # 模型卡（精度/局限/适用范围）
│       ├── train_config.yaml    # 完整训练配置
│       └── dataset_version.txt # 训练用数据集版本：v1.2_20260501
├── classification/
├── lpr/
└── ocr/
```
