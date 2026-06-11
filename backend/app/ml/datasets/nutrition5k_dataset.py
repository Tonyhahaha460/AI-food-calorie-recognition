from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NutritionSample:
    image_path: Path
    label: str
    nutrition: dict[str, float]
    source: str
    split: str = "train"
    dish_id: str | None = None
    display_name: str | None = None
    default_portion_label: str = "1 份"
    parent_category: str = ""
    parent_display_name: str = ""


def load_nutrition5k_samples(dataset_root: str, metadata_path: str) -> list[NutritionSample]:
    root = Path(dataset_root)
    metadata_file = Path(metadata_path)
    if not metadata_file.exists():
        return []

    raw = json.loads(metadata_file.read_text(encoding="utf-8"))
    samples = []
    for item in raw:
        relative_image = item.get("image_path", "")
        if not relative_image:
            continue

        image_path = root / relative_image
        if not image_path.exists():
            continue

        nutrition = item.get("nutrition", {})
        if not {"calories", "protein", "fat", "carbs"}.issubset(nutrition.keys()):
            continue

        samples.append(
            NutritionSample(
                image_path=image_path,
                label=item.get("label", "nutrition5k_item"),
                nutrition={
                    "calories": float(nutrition["calories"]),
                    "protein": float(nutrition["protein"]),
                    "fat": float(nutrition["fat"]),
                    "carbs": float(nutrition["carbs"]),
                },
                source="nutrition5k",
                split=item.get("split", "train"),
                dish_id=item.get("dish_id"),
                display_name=item.get("display_name") or item.get("label"),
                default_portion_label=item.get("default_portion_label", "1 份"),
                parent_category=item.get("parent_category", ""),
                parent_display_name=item.get("parent_display_name", ""),
            )
        )

    return samples


def build_nutrition5k_metadata(
    dataset_root: str,
    output_path: str,
    image_variant: str = "realsense_overhead",
) -> dict[str, int | str]:
    root = Path(dataset_root)
    metadata_dir = root / "metadata"
    split_dir = root / "dish_ids" / "splits"
    imagery_root = _resolve_imagery_root(root, image_variant)

    if not metadata_dir.exists():
        raise FileNotFoundError(f"Nutrition5k metadata directory not found: {metadata_dir}")
    if not split_dir.exists():
        raise FileNotFoundError(f"Nutrition5k split directory not found: {split_dir}")
    if not imagery_root.exists():
        raise FileNotFoundError(f"Nutrition5k imagery directory not found: {imagery_root}")

    train_ids = _load_split_ids(split_dir / "rgb_train_ids.txt")
    test_ids = _load_split_ids(split_dir / "rgb_test_ids.txt")

    records: list[dict[str, object]] = []
    metadata_files = sorted(metadata_dir.glob("dish_metadata_*.csv"))
    for metadata_file in metadata_files:
        cafe_name = metadata_file.stem.replace("dish_metadata_", "")
        with metadata_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 6:
                    continue

                dish_id = row[0].strip()
                if not dish_id:
                    continue

                rgb_path = imagery_root / dish_id / "rgb.png"
                if not rgb_path.exists():
                    continue

                nutrition = _parse_total_nutrition(row)
                if nutrition is None:
                    continue

                ingredients = _parse_ingredients(row[6:])
                display_name = _build_display_name(ingredients, dish_id)
                split = "test" if dish_id in test_ids else "train" if dish_id in train_ids else "unspecified"

                records.append(
                    {
                        "dish_id": dish_id,
                        "label": _slugify_label(display_name, dish_id),
                        "display_name": display_name,
                        "image_path": rgb_path.relative_to(root).as_posix(),
                        "split": split,
                        "source": "nutrition5k",
                        "cafe": cafe_name,
                        "default_portion_label": "1 份",
                        "mass_grams": _safe_float(row[1]),
                        "nutrition": nutrition,
                        "ingredients": ingredients[:5],
                    }
                )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "record_count": len(records),
        "train_count": sum(1 for item in records if item["split"] == "train"),
        "test_count": sum(1 for item in records if item["split"] == "test"),
        "unspecified_count": sum(1 for item in records if item["split"] == "unspecified"),
        "image_variant": image_variant,
    }


def _resolve_imagery_root(root: Path, image_variant: str) -> Path:
    nested = root / "imagery" / image_variant
    direct = root / image_variant
    if nested.exists():
        return nested
    return direct


def _load_split_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _parse_total_nutrition(row: list[str]) -> dict[str, float] | None:
    calories = _safe_float(row[2])
    fat = _safe_float(row[3])
    carbs = _safe_float(row[4])
    protein = _safe_float(row[5])
    if calories is None or fat is None or carbs is None or protein is None:
        return None
    return {
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }


def _parse_ingredients(columns: list[str]) -> list[dict[str, float | str]]:
    ingredients = []
    step = 7
    for index in range(0, len(columns), step):
        chunk = columns[index : index + step]
        if len(chunk) < step:
            continue

        ingredient_id = chunk[0].strip()
        ingredient_name = chunk[1].strip()
        if not ingredient_id or not ingredient_name:
            continue

        ingredients.append(
            {
                "ingredient_id": ingredient_id,
                "name": ingredient_name,
                "grams": _safe_float(chunk[2]) or 0.0,
                "calories": _safe_float(chunk[3]) or 0.0,
                "fat": _safe_float(chunk[4]) or 0.0,
                "carbs": _safe_float(chunk[5]) or 0.0,
                "protein": _safe_float(chunk[6]) or 0.0,
            }
        )

    ingredients.sort(key=lambda item: (float(item["grams"]), float(item["calories"])), reverse=True)
    return ingredients


def _build_display_name(ingredients: list[dict[str, float | str]], dish_id: str) -> str:
    if not ingredients:
        return dish_id

    top_names = [str(item["name"]) for item in ingredients[:2] if item.get("name")]
    if not top_names:
        return dish_id
    return " + ".join(top_names)


def _slugify_label(display_name: str, dish_id: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
    return cleaned or dish_id


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
