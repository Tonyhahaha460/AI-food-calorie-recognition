from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from torchvision.datasets import Food101


FOOD101_TO_PROFILE_LABEL = {
    "caesar_salad": "凱薩沙拉",
    "cheesecake": "乳酪蛋糕",
    "chocolate_cake": "巧克力蛋糕",
    "club_sandwich": "sandwich",
    "donuts": "甜甜圈",
    "french_fries": "french_fries",
    "fried_rice": "炒飯",
    "greek_salad": "salad",
    "grilled_cheese_sandwich": "sandwich",
    "hamburger": "hamburger",
    "ice_cream": "冰淇淋",
    "lobster_roll_sandwich": "sandwich",
    "omelette": "fried_egg",
    "pizza": "pizza",
    "ramen": "ramen",
    "seaweed_salad": "salad",
    "spaghetti_bolognese": "義大利麵",
    "spaghetti_carbonara": "義大利麵",
    "steak": "steak",
    "strawberry_shortcake": "草莓蛋糕",
    "sushi": "sushi",
    "waffles": "鬆餅",
}


@dataclass
class ClassificationRecord:
    image_path: Path
    label: str
    source: str
    source_label: str


def download_food101_dataset(root: str | Path) -> dict[str, int | str]:
    dataset_root = Path(root)
    dataset_root.mkdir(parents=True, exist_ok=True)

    train_dataset = Food101(root=dataset_root, split="train", download=True)
    test_dataset = Food101(root=dataset_root, split="test", download=True)

    return {
        "root": str((dataset_root / "food-101").resolve()),
        "train_count": len(train_dataset),
        "test_count": len(test_dataset),
        "class_count": len(train_dataset.classes),
    }


def load_food101_records(
    root: str | Path,
    split: str = "train",
    allowed_profile_labels: set[str] | None = None,
    max_per_label: int | None = None,
    download: bool = False,
) -> list[ClassificationRecord]:
    dataset = Food101(root=root, split=split, download=download)
    allowed = set(allowed_profile_labels or [])
    counts: dict[str, int] = defaultdict(int)
    records: list[ClassificationRecord] = []

    for image_path, raw_target in zip(dataset._image_files, dataset._labels):
        food101_label = dataset.classes[raw_target]
        mapped_label = FOOD101_TO_PROFILE_LABEL.get(food101_label)
        if not mapped_label:
            continue
        if allowed and mapped_label not in allowed:
            continue
        if max_per_label is not None and counts[mapped_label] >= max_per_label:
            continue

        records.append(
            ClassificationRecord(
                image_path=Path(image_path),
                label=mapped_label,
                source="food101",
                source_label=food101_label,
            )
        )
        counts[mapped_label] += 1

    return records
