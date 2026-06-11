from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4


from werkzeug.utils import secure_filename


FOOD_PROFILES_PATH = Path(__file__).with_name("food_profiles.json")
INVALID_WINDOWS_FILENAME_CHARS = '<>:"/\\|?*'


def _resolve_dataset_root() -> Path:
    configured = os.getenv("FOOD_DATASET_ROOT", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = FOOD_PROFILES_PATH.parent.parent.parent.parent / path
    else:
        path = FOOD_PROFILES_PATH.parent.parent.parent / "dataset"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_food_profiles() -> dict:
    with FOOD_PROFILES_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not data:
        raise ValueError("food_profiles.json must contain at least one food profile.")

    return data


def _get_dataset_leaf_name(label: str, profile: dict) -> str:
    label_text = str(label).strip()
    if not label_text:
        raise ValueError("Profile label cannot be empty.")

    if any(char in INVALID_WINDOWS_FILENAME_CHARS for char in label_text):
        display_name = str(profile.get("display_name", "")).strip()
        if display_name:
            return display_name

    return label_text


def save_food_profiles(data: dict) -> None:
    with FOOD_PROFILES_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_dataset_dir(label: str, profiles: dict | None = None) -> Path:
    profiles = profiles or load_food_profiles()
    profile = profiles.get(label, {})
    parent_category = profile.get("parent_category", "")
    dataset_root = _resolve_dataset_root()
    leaf_name = _get_dataset_leaf_name(label, profile)

    if parent_category:
        path = dataset_root / parent_category / leaf_name
    else:
        path = dataset_root / leaf_name

    path.mkdir(parents=True, exist_ok=True)
    return path


def list_dataset_images(label: str, profiles: dict | None = None) -> list[str]:
    directory = get_dataset_dir(label, profiles)
    return sorted(
        [
            file.name
            for file in directory.iterdir()
            if file.is_file() and file.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
    )


def save_dataset_image(label: str, filename: str, image_bytes: bytes, profiles: dict | None = None) -> str:
    directory = get_dataset_dir(label, profiles)
    safe_name = secure_filename(filename) or "image.jpg"
    final_name = f"{uuid4().hex}_{safe_name}"
    output_path = directory / final_name
    output_path.write_bytes(image_bytes)
    return final_name


def delete_dataset_image(label: str, filename: str, profiles: dict | None = None) -> bool:
    directory = get_dataset_dir(label, profiles)
    target = directory / filename
    if not target.exists() or not target.is_file():
        return False
    target.unlink()
    return True
