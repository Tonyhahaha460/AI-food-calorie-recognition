from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


# ===== Change these in Spyder if needed =====
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "local_assets" / "backend" / "dataset" / "nutrition5k"
METADATA_PATH = PROJECT_ROOT / "backend" / "app" / "data" / "nutrition5k_metadata.json"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "runs" / "nutrition5k_mobilenet"

EPOCHS = 20
BATCH_SIZE = 32
IMAGE_SIZE = 224
LEARNING_RATE_HEAD = 1e-3
LEARNING_RATE_FINETUNE = 2e-4
WARMUP_EPOCHS = 3
NUM_WORKERS = 0  # Keep 0 for Spyder/Windows.
SEED = 42

NUTRITION_KEYS = ("calories", "protein", "fat", "carbs")
# Makes each target contribute similarly while the model still outputs real values.
LOSS_SCALE = torch.tensor([500.0, 40.0, 40.0, 80.0], dtype=torch.float32)


@dataclass
class NutritionRecord:
    image_path: Path
    target: torch.Tensor
    split: str


class Nutrition5kDataset(Dataset):
    def __init__(self, records: list[NutritionRecord], transform) -> None:
        self.records = records
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        record = self.records[index]
        with Image.open(record.image_path) as image:
            image = image.convert("RGB")
            image_tensor = self.transform(image)
        return image_tensor, record.target


class MobileNetRegressor(nn.Module):
    def __init__(self, pretrained: bool = True, output_dim: int = 4) -> None:
        super().__init__()
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = mobilenet_v3_small(weights=weights)
        self.features = backbone.features
        self.avgpool = backbone.avgpool
        hidden_dim = backbone.classifier[0].in_features
        self.regressor = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.Hardswish(),
            nn.Linear(128, output_dim),
        )

    def freeze_backbone(self) -> None:
        for parameter in self.features.parameters():
            parameter.requires_grad = False

    def unfreeze_backbone(self) -> None:
        for parameter in self.features.parameters():
            parameter.requires_grad = True

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = x.flatten(1)
        return self.regressor(x)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_train_transform():
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.12),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def build_eval_transform():
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def load_records() -> tuple[list[NutritionRecord], list[NutritionRecord]]:
    raw_items = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    train_records: list[NutritionRecord] = []
    val_records: list[NutritionRecord] = []

    for item in raw_items:
        nutrition = item.get("nutrition", {})
        if not all(key in nutrition for key in NUTRITION_KEYS):
            continue

        image_rel = item.get("image_path")
        if not image_rel:
            continue

        image_path = DATASET_ROOT / image_rel
        if not image_path.exists():
            continue

        target = torch.tensor([float(nutrition[key]) for key in NUTRITION_KEYS], dtype=torch.float32)
        split = item.get("split", "train")
        record = NutritionRecord(image_path=image_path, target=target, split=split)

        if split == "test":
            val_records.append(record)
        else:
            train_records.append(record)

    if not train_records or not val_records:
        raise RuntimeError(
            "Nutrition5k records were not found. Check DATASET_ROOT and METADATA_PATH."
        )

    return train_records, val_records


def scaled_smooth_l1_loss(prediction: torch.Tensor, target: torch.Tensor, device) -> torch.Tensor:
    scale = LOSS_SCALE.to(device)
    return nn.functional.smooth_l1_loss(prediction / scale, target / scale)


@torch.no_grad()
def evaluate(model, data_loader, device) -> dict[str, float]:
    model.eval()
    absolute_errors = []
    squared_errors = []

    for images, targets in data_loader:
        images = images.to(device)
        targets = targets.to(device)
        predictions = model(images).clamp_min(0.0)
        errors = predictions - targets
        absolute_errors.append(errors.abs().cpu())
        squared_errors.append((errors**2).cpu())

    mae = torch.cat(absolute_errors).mean(dim=0)
    rmse = torch.cat(squared_errors).mean(dim=0).sqrt()

    metrics = {}
    for index, key in enumerate(NUTRITION_KEYS):
        metrics[f"{key}_mae"] = float(mae[index])
        metrics[f"{key}_rmse"] = float(rmse[index])
    return metrics


def save_checkpoint(model, metrics: dict[str, float], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_name": "MobileNet Regression",
            "state_dict": model.state_dict(),
            "nutrition_keys": list(NUTRITION_KEYS),
            "image_size": IMAGE_SIZE,
            "metrics": metrics,
        },
        output_path,
    )


def main() -> None:
    seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_records, val_records = load_records()
    print(f"Train records: {len(train_records)}")
    print(f"Val records: {len(val_records)}")

    train_dataset = Nutrition5kDataset(train_records, build_train_transform())
    val_dataset = Nutrition5kDataset(val_records, build_eval_transform())

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available(),
    )

    model = MobileNetRegressor(pretrained=True).to(device)
    model.freeze_backbone()

    best_score = float("inf")
    best_path = OUTPUT_DIR / "mobilenet_regressor_best.pt"
    last_path = OUTPUT_DIR / "mobilenet_regressor_last.pt"

    for epoch in range(1, EPOCHS + 1):
        if epoch == WARMUP_EPOCHS + 1:
            model.unfreeze_backbone()

        learning_rate = LEARNING_RATE_HEAD if epoch <= WARMUP_EPOCHS else LEARNING_RATE_FINETUNE
        optimizer = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=learning_rate,
            weight_decay=1e-4,
        )

        model.train()
        running_loss = 0.0
        for images, targets in train_loader:
            images = images.to(device)
            targets = targets.to(device)

            optimizer.zero_grad(set_to_none=True)
            predictions = model(images)
            loss = scaled_smooth_l1_loss(predictions, targets, device)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * images.size(0)

        train_loss = running_loss / len(train_dataset)
        metrics = evaluate(model, val_loader, device)
        score = metrics["calories_mae"]

        print(
            f"Epoch {epoch:03d}/{EPOCHS} | "
            f"loss={train_loss:.4f} | "
            f"calories_mae={metrics['calories_mae']:.2f} | "
            f"protein_mae={metrics['protein_mae']:.2f} | "
            f"fat_mae={metrics['fat_mae']:.2f} | "
            f"carbs_mae={metrics['carbs_mae']:.2f}"
        )

        save_checkpoint(model, metrics, last_path)
        if score < best_score:
            best_score = score
            save_checkpoint(model, metrics, best_path)
            print(f"Saved best model: {best_path}")

    print("Done.")
    print(f"Best model: {best_path}")
    print(f"Last model: {last_path}")


if __name__ == "__main__":
    main()
