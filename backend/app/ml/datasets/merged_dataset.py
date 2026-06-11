from __future__ import annotations

from app.ml.datasets.custom_food_dataset import load_custom_food_samples
from app.ml.datasets.nutrition5k_dataset import load_nutrition5k_samples


def load_merged_samples(dataset_root: str, metadata_path: str) -> list:
    nutrition5k_samples = load_nutrition5k_samples(dataset_root, metadata_path)
    custom_samples = load_custom_food_samples()
    return nutrition5k_samples + custom_samples
