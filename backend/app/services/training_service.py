from __future__ import annotations

import pickle
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from app.data.food_profiles import get_dataset_dir, list_dataset_images, load_food_profiles
from app.ml.datasets.food101_dataset import ClassificationRecord, load_food101_records
from app.ml.models.mobilenet_classifier import MobileNetClassifier
from app.ml.training.evaluate import compute_classification_metrics
from app.ml.training.transforms import build_eval_transform, build_train_transform


class TrainingError(Exception):
    pass


MODEL_IMAGE_SIZE = 128
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

TRAIN_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((MODEL_IMAGE_SIZE, MODEL_IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(12),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

INFERENCE_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((MODEL_IMAGE_SIZE, MODEL_IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


class MealCNN(nn.Module):
    def __init__(self, class_count: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, class_count),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)


def tensor_from_bytes(image_bytes: bytes) -> torch.Tensor:
    with Image.open(BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        return INFERENCE_TRANSFORM(image)


def extract_features(image_bytes: bytes) -> np.ndarray:
    with Image.open(BytesIO(image_bytes)) as image:
        image = image.convert("RGB").resize((64, 64))
        array = np.asarray(image, dtype=np.float32) / 255.0

    means = array.mean(axis=(0, 1))
    stds = array.std(axis=(0, 1))
    pooled = array[::8, ::8].reshape(-1)
    return np.concatenate([means, stds, pooled])


@dataclass
class TrainingSummary:
    model_path: str
    trained_at: str
    class_count: int
    image_count: int
    training_sample_count: int
    sample_counts: dict[str, int]
    class_details: list[dict]
    model_name: str
    epochs: int
    source_counts: dict[str, int]
    metrics: dict[str, float]


class _FoodImageDataset(Dataset):
    def __init__(self, records: list[ClassificationRecord], label_to_index: dict[str, int], transform) -> None:
        self.records = records
        self.label_to_index = label_to_index
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        record = self.records[index]
        with Image.open(record.image_path) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.label_to_index[record.label]


class TrainingService:
    MODEL_NAME = "MobileNetV3 Food Classifier"
    WARMUP_EPOCHS = 2
    FINETUNE_EPOCHS = 4
    BATCH_SIZE = 16
    WARMUP_LR = 1e-3
    FINETUNE_LR = 2e-4

    @staticmethod
    def _resolve_model_path(config) -> Path:
        path = Path(config["TRAINED_MODEL_PATH"])
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _resolve_food101_root(config) -> Path:
        path = Path(config.get("FOOD101_ROOT", "dataset"))
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _split_custom_filenames(filenames: list[str]) -> tuple[list[str], list[str]]:
        ordered = sorted(filenames)
        if len(ordered) <= 2:
            return ordered, []
        if len(ordered) <= 4:
            return ordered[:-1], ordered[-1:]

        val_count = max(1, int(round(len(ordered) * 0.2)))
        return ordered[:-val_count], ordered[-val_count:]

    @classmethod
    def _collect_custom_records(cls, profiles: dict, repeat_factor: int) -> tuple[
        list[ClassificationRecord],
        list[ClassificationRecord],
        Counter,
        Counter,
        Counter,
    ]:
        train_records: list[ClassificationRecord] = []
        val_records: list[ClassificationRecord] = []
        image_counts: Counter = Counter()
        train_counts: Counter = Counter()
        val_counts: Counter = Counter()

        for label in profiles.keys():
            filenames = list_dataset_images(label, profiles)
            if not filenames:
                continue

            directory = get_dataset_dir(label, profiles)
            image_counts[label] = len(filenames)
            train_files, val_files = cls._split_custom_filenames(filenames)

            for filename in train_files:
                record = ClassificationRecord(
                    image_path=directory / filename,
                    label=label,
                    source="custom",
                    source_label=filename,
                )
                for _ in range(max(1, repeat_factor)):
                    train_records.append(record)
                    train_counts[label] += 1

            for filename in val_files:
                val_records.append(
                    ClassificationRecord(
                        image_path=directory / filename,
                        label=label,
                        source="custom",
                        source_label=filename,
                    )
                )
                val_counts[label] += 1

        return train_records, val_records, image_counts, train_counts, val_counts

    @classmethod
    def _collect_food101_records(cls, config, profiles: dict) -> tuple[
        list[ClassificationRecord],
        list[ClassificationRecord],
        Counter,
        Counter,
    ]:
        if not config.get("FOOD101_USE", True):
            return [], [], Counter(), Counter()

        food101_root = cls._resolve_food101_root(config)
        allowed_labels = set(profiles.keys())
        download = config.get("FOOD101_DOWNLOAD_ON_TRAIN", False)

        try:
            train_records = load_food101_records(
                root=food101_root,
                split="train",
                allowed_profile_labels=allowed_labels,
                max_per_label=int(config.get("FOOD101_TRAIN_SAMPLES_PER_LABEL", 120)),
                download=download,
            )
            val_records = load_food101_records(
                root=food101_root,
                split="test",
                allowed_profile_labels=allowed_labels,
                max_per_label=int(config.get("FOOD101_VAL_SAMPLES_PER_LABEL", 40)),
                download=False,
            )
        except RuntimeError:
            return [], [], Counter(), Counter()

        return (
            train_records,
            val_records,
            Counter(record.label for record in train_records),
            Counter(record.label for record in val_records),
        )

    @staticmethod
    def _train_one_epoch(model: nn.Module, loader: DataLoader, criterion, optimizer) -> None:
        model.train()
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(DEVICE)
            batch_y = batch_y.to(DEVICE)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

    @staticmethod
    def _evaluate(model: nn.Module, loader: DataLoader | None) -> dict[str, float]:
        if loader is None:
            return {}

        model.eval()
        logits_chunks = []
        target_chunks = []
        with torch.no_grad():
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(DEVICE)
                batch_logits = model(batch_x).cpu()
                logits_chunks.append(batch_logits)
                target_chunks.append(batch_y.cpu())

        if not logits_chunks:
            return {}

        logits = torch.cat(logits_chunks, dim=0)
        targets = torch.cat(target_chunks, dim=0)
        return compute_classification_metrics(logits, targets)

    @classmethod
    def _build_class_details(
        cls,
        profiles: dict,
        class_labels: list[str],
        image_counts: Counter,
        custom_train_counts: Counter,
        custom_val_counts: Counter,
        food101_train_counts: Counter,
        food101_val_counts: Counter,
        total_train_counts: Counter,
    ) -> list[dict]:
        details = []
        for label in class_labels:
            profile = profiles.get(label, {})
            details.append(
                {
                    "label": label,
                    "display_name": profile.get("display_name", label),
                    "parent_category": profile.get("parent_category", ""),
                    "image_count": int(image_counts.get(label, 0)),
                    "custom_train_count": int(custom_train_counts.get(label, 0)),
                    "custom_val_count": int(custom_val_counts.get(label, 0)),
                    "food101_train_count": int(food101_train_counts.get(label, 0)),
                    "food101_val_count": int(food101_val_counts.get(label, 0)),
                    "training_count": int(total_train_counts.get(label, 0)),
                }
            )
        return details

    @classmethod
    def train(cls, config) -> dict:
        profiles = load_food_profiles()
        repeat_factor = int(config.get("CUSTOM_TRAIN_REPEAT", 12))

        custom_train_records, custom_val_records, image_counts, custom_train_counts, custom_val_counts = (
            cls._collect_custom_records(profiles, repeat_factor)
        )
        food101_train_records, food101_val_records, food101_train_counts, food101_val_counts = (
            cls._collect_food101_records(config, profiles)
        )

        train_records = food101_train_records + custom_train_records
        val_records = food101_val_records + custom_val_records
        class_labels = list(dict.fromkeys(record.label for record in train_records + val_records))

        if len(class_labels) < 2:
            raise TrainingError(
                "At least two labels are required for training. Download Food-101 or upload more custom images first."
            )
        if not train_records:
            raise TrainingError("No training images were found.")

        label_to_index = {label: index for index, label in enumerate(class_labels)}
        train_dataset = _FoodImageDataset(train_records, label_to_index, build_train_transform())
        val_dataset = _FoodImageDataset(val_records, label_to_index, build_eval_transform()) if val_records else None

        train_loader = DataLoader(
            train_dataset,
            batch_size=min(cls.BATCH_SIZE, max(1, len(train_dataset))),
            shuffle=True,
        )
        val_loader = (
            DataLoader(
                val_dataset,
                batch_size=min(cls.BATCH_SIZE, max(1, len(val_dataset))),
                shuffle=False,
            )
            if val_dataset is not None
            else None
        )

        model = MobileNetClassifier(num_classes=len(class_labels), pretrained=True).to(DEVICE)
        criterion = nn.CrossEntropyLoss()

        model.freeze_features()
        warmup_optimizer = torch.optim.Adam(
            (parameter for parameter in model.parameters() if parameter.requires_grad),
            lr=cls.WARMUP_LR,
        )
        for _ in range(cls.WARMUP_EPOCHS):
            cls._train_one_epoch(model, train_loader, criterion, warmup_optimizer)

        model.unfreeze_all()
        finetune_optimizer = torch.optim.Adam(model.parameters(), lr=cls.FINETUNE_LR)
        for _ in range(cls.FINETUNE_EPOCHS):
            cls._train_one_epoch(model, train_loader, criterion, finetune_optimizer)

        metrics = cls._evaluate(model, val_loader)
        trained_at = datetime.now(timezone.utc).isoformat()
        total_train_counts = Counter(record.label for record in train_records)
        class_details = cls._build_class_details(
            profiles=profiles,
            class_labels=class_labels,
            image_counts=image_counts,
            custom_train_counts=custom_train_counts,
            custom_val_counts=custom_val_counts,
            food101_train_counts=food101_train_counts,
            food101_val_counts=food101_val_counts,
            total_train_counts=total_train_counts,
        )

        model_data = {
            "backend": "mobilenet_classifier",
            "state_dict": model.state_dict(),
            "class_labels": class_labels,
            "trained_at": trained_at,
            "sample_counts": dict(total_train_counts),
            "class_details": class_details,
            "profiles": profiles,
            "model_name": cls.MODEL_NAME,
            "training_sample_count": len(train_records),
            "epochs": cls.WARMUP_EPOCHS + cls.FINETUNE_EPOCHS,
            "image_size": 224,
            "source_counts": {
                "food101": int(len(food101_train_records)),
                "custom": int(len(custom_train_records)),
            },
            "metrics": metrics,
        }

        model_path = cls._resolve_model_path(config)
        with model_path.open("wb") as file:
            pickle.dump(model_data, file)

        unique_image_count = len({str(record.image_path) for record in train_records + val_records})
        return TrainingSummary(
            model_path=str(model_path),
            trained_at=trained_at,
            class_count=len(class_labels),
            image_count=unique_image_count,
            training_sample_count=len(train_records),
            sample_counts=dict(total_train_counts),
            class_details=class_details,
            model_name=cls.MODEL_NAME,
            epochs=cls.WARMUP_EPOCHS + cls.FINETUNE_EPOCHS,
            source_counts={
                "food101": int(len(food101_train_records)),
                "custom": int(len(custom_train_records)),
            },
            metrics=metrics,
        ).__dict__

    @classmethod
    def status(cls, config) -> dict:
        model_path = cls._resolve_model_path(config)
        if not model_path.exists():
            return {
                "available": False,
                "model_path": str(model_path),
                "trained_at": None,
                "class_count": 0,
                "image_count": 0,
                "training_sample_count": 0,
                "sample_counts": {},
                "class_details": [],
                "model_name": cls.MODEL_NAME,
                "epochs": cls.WARMUP_EPOCHS + cls.FINETUNE_EPOCHS,
                "source_counts": {},
                "metrics": {},
            }

        with model_path.open("rb") as file:
            model_data = pickle.load(file)

        sample_counts = model_data.get("sample_counts", {})
        class_details = model_data.get("class_details", [])
        return {
            "available": True,
            "model_path": str(model_path),
            "trained_at": model_data.get("trained_at"),
            "class_count": len(model_data.get("class_labels", sample_counts)),
            "image_count": int(sum(detail.get("image_count", 0) for detail in class_details)),
            "training_sample_count": int(model_data.get("training_sample_count", sum(sample_counts.values()))),
            "sample_counts": sample_counts,
            "class_details": class_details,
            "model_name": model_data.get("model_name", cls.MODEL_NAME),
            "epochs": int(model_data.get("epochs", cls.WARMUP_EPOCHS + cls.FINETUNE_EPOCHS)),
            "source_counts": model_data.get("source_counts", {}),
            "metrics": model_data.get("metrics", {}),
        }
