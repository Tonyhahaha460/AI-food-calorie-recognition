from __future__ import annotations

from pathlib import Path

from app.data.food_profiles import get_dataset_dir, list_dataset_images, load_food_profiles
from app.ml.datasets.nutrition5k_dataset import NutritionSample


def load_custom_food_samples(dataset_root: str | None = None) -> list[NutritionSample]:
    profiles = load_food_profiles()
    samples: list[NutritionSample] = []

    for label, profile in profiles.items():
        filenames = list_dataset_images(label, profiles)
        if not filenames:
            continue

        directory = get_dataset_dir(label, profiles)
        parent_label = profile.get("parent_category", "")
        parent_profile = profiles.get(parent_label, {}) if parent_label else {}
        for filename in filenames:
            samples.append(
                NutritionSample(
                    image_path=Path(directory) / filename,
                    label=label,
                    nutrition={
                        "calories": float(profile["calories"]),
                        "protein": float(profile["protein"]),
                        "fat": float(profile["fat"]),
                        "carbs": float(profile["carbs"]),
                    },
                    source="custom",
                    split="custom",
                    dish_id=label,
                    display_name=profile.get("display_name", label),
                    default_portion_label=profile.get("default_portion_label", "1 份"),
                    parent_category=parent_label,
                    parent_display_name=parent_profile.get("display_name", parent_label),
                )
            )

    return samples
