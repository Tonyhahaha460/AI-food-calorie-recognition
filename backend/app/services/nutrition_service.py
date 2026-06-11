from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from app.data.food_profiles import (
    delete_dataset_image,
    list_dataset_images,
    load_food_profiles,
    save_dataset_image,
    save_food_profiles,
)


class FoodProfileError(Exception):
    pass


class NutritionService:
    EXTERNAL_LABEL_ALIASES = {
        "bento_box": "bento",
        "boiled_chicken": "雞腿",
        "braised_pork": "control_butchers",
        "caesar_salad": "凱薩沙拉",
        "cake": "cake",
        "cheesecake": "乳酪蛋糕",
        "chicken_drumstick": "雞腿",
        "chicken_fried_rice": "炒飯",
        "chicken_leg_bento": "雞腿便當",
        "chicken_over_rice": "雞肉飯",
        "chocolate_cake": "巧克力蛋糕",
        "cola": "cola",
        "club_sandwich": "sandwich",
        "creamy_cake": "鮮奶油蛋糕",
        "dumpling": "dumpling",
        "dumplings": "dumpling",
        "donut": "甜甜圈",
        "donuts": "甜甜圈",
        "fish_bento": "魚便當",
        "french_fries": "french_fries",
        "fried_chicken": "炸雞",
        "fried_chicken_drumstick": "雞腿",
        "fried_rice": "炒飯",
        "gyoza": "dumpling",
        "grilled_cheese_sandwich": "sandwich",
        "hamburger": "hamburger",
        "hot_dog": "hot_dog",
        "ice_cream": "冰淇淋",
        "kung_pao_chicken": "宮保雞丁",
        "lobster_roll_sandwich": "sandwich",
        "omelet": "fried_egg",
        "omelette": "fried_egg",
        "orange": "orange",
        "potsticker": "dumpling",
        "pork_bento": "排骨便當",
        "soy_sauce_chicken": "醬油雞",
        "spaghetti": "義大利麵",
        "spaghetti_bolognese": "義大利麵",
        "spaghetti_carbonara": "義大利麵",
        "strawberry_shortcake": "草莓蛋糕",
        "煎餃": "dumpling",
        "餃子": "dumpling",
        "scrambled_egg_with_tomato": "番茄炒蛋",
        "scrambled_eggs": "fried_egg",
        "three_cup_chicken": "三杯雞",
        "waffle": "鬆餅",
        "waffles": "鬆餅",
    }

    NUTRITION5K_LABEL_ALIASES = {
        "rice": ["white_rice"],
        "炒飯": ["fried_rice", "chicken_fried_rice"],
        "雞肉飯": ["chicken_white_rice", "white_rice_chicken_thighs"],
        "control_butchers": ["pork_white_rice", "white_rice_pork"],
        "pizza": ["pizza", "cheese_pizza"],
        "salad": ["caesar_salad"],
        "凱薩沙拉": ["caesar_salad", "chicken_caesar_salad"],
        "fried_egg": ["scrambled_eggs"],
        "番茄炒蛋": ["scrambled_eggs"],
        "orange": ["orange"],
        "apple": ["apple"],
        "broccoli": ["broccoli"],
        "carrot": ["carrot"],
        "義大利麵": ["spaghetti"],
        "鬆餅": ["waffles"],
        "魚便當": ["fish_white_rice"],
        "chicken_white_rice": ["chicken_white_rice"],
    }

    @staticmethod
    def get_all_profiles() -> dict:
        return load_food_profiles()

    @classmethod
    def get_labels(cls) -> list[str]:
        return list(cls.get_all_profiles().keys())

    @classmethod
    def get_default_label(cls) -> str:
        labels = cls.get_labels()
        return "bento" if "bento" in labels else labels[0]

    @staticmethod
    def normalize_label_key(value: str) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace("&", " and ")
        normalized = normalized.replace("/", " ")
        normalized = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", normalized)
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized)
        return normalized.strip("_")

    @classmethod
    def get_external_label_aliases(cls) -> dict[str, str]:
        aliases = dict(cls.EXTERNAL_LABEL_ALIASES)
        for label, profile in cls.get_all_profiles().items():
            aliases[cls.normalize_label_key(label)] = label
            display_name = str(profile.get("display_name", "")).strip()
            if display_name:
                aliases[cls.normalize_label_key(display_name)] = label
        return aliases

    @classmethod
    def resolve_lookup_label(cls, raw_label: str) -> str | None:
        profiles = cls.get_all_profiles()
        if raw_label in profiles:
            return raw_label

        aliases = cls.get_external_label_aliases()
        normalized = cls.normalize_label_key(raw_label)
        if not normalized:
            return None

        direct = aliases.get(normalized)
        if direct in profiles:
            return direct
        if direct:
            direct_alias = aliases.get(cls.normalize_label_key(direct))
            if direct_alias in profiles:
                return direct_alias

        singular = normalized[:-1] if normalized.endswith("s") else normalized
        resolved = aliases.get(singular)
        if resolved in profiles:
            return resolved
        if resolved:
            resolved_alias = aliases.get(cls.normalize_label_key(resolved))
            if resolved_alias in profiles:
                return resolved_alias

        repaired = cls._repair_mojibake_label(raw_label)
        if repaired and repaired != raw_label:
            return cls.resolve_lookup_label(repaired)

        return None

    @staticmethod
    def _repair_mojibake_label(value: str) -> str | None:
        text = str(value).strip()
        if not text:
            return None

        for encoding in ("cp1252", "latin1"):
            try:
                repaired = text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            if repaired and repaired != text:
                return repaired
        return None

    @classmethod
    def get_nutrition(cls, food_name: str) -> dict:
        profiles = cls.get_all_profiles()
        default_label = cls.get_default_label()
        resolved_label = cls.resolve_lookup_label(food_name) or food_name
        return deepcopy(profiles.get(resolved_label, profiles[default_label]))

    @classmethod
    def estimate_item(cls, food_name: str, portion_multiplier: float) -> dict:
        resolved_label = cls.resolve_lookup_label(food_name) or food_name
        profiles = cls.get_all_profiles()
        has_curated_profile = resolved_label in profiles
        profile = cls.get_nutrition(resolved_label)
        multiplier = max(0.5, min(portion_multiplier, 1.8))

        custom_nutrition_values = {
            "calories": float(profile["calories"]),
            "protein": float(profile["protein"]),
            "fat": float(profile["fat"]),
            "carbs": float(profile["carbs"]),
        }
        nutrition_values = dict(custom_nutrition_values)
        nutrition_source = "custom"

        if not has_curated_profile:
            nutrition5k_values = cls.lookup_nutrition5k_for_label(resolved_label)
            if nutrition5k_values is not None:
                nutrition_values = nutrition5k_values
                nutrition_source = "nutrition5k"

        return {
            "food_name": profile["display_name"],
            "estimated_portion": cls.format_portion(profile["default_portion_label"], multiplier),
            "nutrition": {
                "calories": round(nutrition_values["calories"] * multiplier),
                "protein": round(nutrition_values["protein"] * multiplier, 1),
                "fat": round(nutrition_values["fat"] * multiplier, 1),
                "carbs": round(nutrition_values["carbs"] * multiplier, 1),
            },
            "nutrition_source": nutrition_source,
        }

    @classmethod
    def lookup_nutrition5k_for_label(cls, food_name: str) -> dict[str, float] | None:
        lookup = cls._get_nutrition5k_lookup()
        resolved_label = cls.resolve_lookup_label(food_name) or food_name
        candidates = cls.NUTRITION5K_LABEL_ALIASES.get(resolved_label, [resolved_label])
        for candidate in candidates:
            record = lookup.get(candidate)
            if record and cls._is_complete_nutrition_record(record["nutrition"]):
                return dict(record["nutrition"])
        return None

    @staticmethod
    def _is_complete_nutrition_record(nutrition: dict[str, float]) -> bool:
        calories = float(nutrition.get("calories", 0.0))
        protein = float(nutrition.get("protein", 0.0))
        fat = float(nutrition.get("fat", 0.0))
        carbs = float(nutrition.get("carbs", 0.0))
        if calories <= 0:
            return False
        if protein == 0.0 and fat == 0.0 and carbs == 0.0:
            return False
        return True

    @staticmethod
    def _should_prefer_nutrition5k(
        custom_nutrition: dict[str, float],
        nutrition5k_nutrition: dict[str, float],
    ) -> bool:
        custom_calories = float(custom_nutrition.get("calories", 0.0))
        nutrition5k_calories = float(nutrition5k_nutrition.get("calories", 0.0))

        if custom_calories <= 0:
            return True

        calorie_ratio = nutrition5k_calories / custom_calories
        if calorie_ratio < 0.6 or calorie_ratio > 1.4:
            return False

        macro_energy = (
            float(nutrition5k_nutrition.get("protein", 0.0)) * 4
            + float(nutrition5k_nutrition.get("fat", 0.0)) * 9
            + float(nutrition5k_nutrition.get("carbs", 0.0)) * 4
        )
        if macro_energy > 0:
            macro_energy_ratio = nutrition5k_calories / macro_energy
            if macro_energy_ratio < 0.65 or macro_energy_ratio > 1.45:
                return False

        return True

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_nutrition5k_lookup() -> dict[str, dict]:
        metadata_path = Path(__file__).resolve().parents[1] / "data" / "nutrition5k_metadata.json"
        if not metadata_path.exists():
            return {}

        try:
            records = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

        grouped: dict[str, dict] = {}
        for item in records:
            label = str(item.get("label", "")).strip()
            display_name = str(item.get("display_name", "")).strip()
            nutrition = item.get("nutrition", {})
            if not label or not display_name:
                continue
            if not {"calories", "protein", "fat", "carbs"}.issubset(nutrition.keys()):
                continue

            bucket = grouped.setdefault(
                label,
                {
                    "display_name": display_name,
                    "count": 0,
                    "nutrition": {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0},
                },
            )
            bucket["count"] += 1
            bucket["nutrition"]["calories"] += float(nutrition["calories"])
            bucket["nutrition"]["protein"] += float(nutrition["protein"])
            bucket["nutrition"]["fat"] += float(nutrition["fat"])
            bucket["nutrition"]["carbs"] += float(nutrition["carbs"])

        lookup: dict[str, dict] = {}
        for label, bucket in grouped.items():
            count = max(1, int(bucket["count"]))
            lookup[label] = {
                "display_name": bucket["display_name"],
                "nutrition": {
                    "calories": bucket["nutrition"]["calories"] / count,
                    "protein": bucket["nutrition"]["protein"] / count,
                    "fat": bucket["nutrition"]["fat"] / count,
                    "carbs": bucket["nutrition"]["carbs"] / count,
                },
            }
        return lookup

    @classmethod
    def match_profile_from_regression(cls, nutrition: dict[str, float]) -> dict:
        candidates = cls._get_regression_match_candidates()
        if not candidates:
            raise FoodProfileError("No regression match candidates available.")

        best_candidate = candidates[0]
        best_distance = float("inf")

        for candidate in candidates:
            profile = candidate["nutrition"]
            distance = (
                abs(profile["calories"] - nutrition["calories"]) * 1.2
                + abs(profile["protein"] - nutrition["protein"]) * 2.5
                + abs(profile["fat"] - nutrition["fat"]) * 2.0
                + abs(profile["carbs"] - nutrition["carbs"]) * 1.8
            )
            if distance < best_distance:
                best_distance = distance
                best_candidate = candidate

        return {
            "label": best_candidate["label"],
            "food_name": best_candidate["display_name"],
            "parent_category": best_candidate.get("parent_category", ""),
            "parent_display_name": best_candidate.get("parent_display_name", ""),
            "source": best_candidate["source"],
            "match_distance": round(best_distance, 2),
            "estimated_portion": best_candidate["default_portion_label"],
            "nutrition": {
                "calories": round(float(nutrition["calories"])),
                "protein": round(float(nutrition["protein"]), 1),
                "fat": round(float(nutrition["fat"]), 1),
                "carbs": round(float(nutrition["carbs"]), 1),
            },
        }

    @classmethod
    def _get_regression_match_candidates(cls) -> list[dict]:
        return cls._get_custom_match_candidates() + cls._get_nutrition5k_match_candidates()

    @classmethod
    def _get_custom_match_candidates(cls) -> list[dict]:
        profiles = cls.get_all_profiles()
        candidates = []
        for label, profile in profiles.items():
            parent_label = profile.get("parent_category", "")
            parent_profile = profiles.get(parent_label, {}) if parent_label else {}
            candidates.append(
                {
                    "label": label,
                    "display_name": profile["display_name"],
                    "parent_category": parent_label,
                    "parent_display_name": parent_profile.get("display_name", parent_label),
                    "default_portion_label": profile["default_portion_label"],
                    "nutrition": {
                        "calories": float(profile["calories"]),
                        "protein": float(profile["protein"]),
                        "fat": float(profile["fat"]),
                        "carbs": float(profile["carbs"]),
                    },
                    "source": "custom",
                }
            )
        return candidates

    @classmethod
    def _get_nutrition5k_match_candidates(cls) -> list[dict]:
        lookup = cls._get_nutrition5k_lookup()
        candidates = []
        for label, item in lookup.items():
            candidates.append(
                {
                    "label": label,
                    "display_name": item["display_name"],
                    "default_portion_label": "1 份",
                    "parent_category": "",
                    "parent_display_name": "",
                    "source": "nutrition5k",
                    "nutrition": dict(item["nutrition"]),
                }
            )
        return candidates

    @staticmethod
    def format_portion(default_label: str, multiplier: float) -> str:
        if abs(multiplier - 1) < 0.08:
            return default_label
        return f"{multiplier:.1f} x {default_label}"

    @staticmethod
    def combine_totals(items: list[dict]) -> dict:
        totals = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for item in items:
            totals["calories"] += item["nutrition"]["calories"]
            totals["protein"] += item["nutrition"]["protein"]
            totals["fat"] += item["nutrition"]["fat"]
            totals["carbs"] += item["nutrition"]["carbs"]

        totals["protein"] = round(totals["protein"], 1)
        totals["fat"] = round(totals["fat"], 1)
        totals["carbs"] = round(totals["carbs"], 1)
        return totals

    @staticmethod
    def build_suggestion(total_nutrition: dict, item_count: int) -> str:
        calories = total_nutrition["calories"]
        protein = total_nutrition["protein"]
        carbs = total_nutrition["carbs"]

        if calories < 350:
            return "這餐比較清爽，若是正餐可以搭配蛋白質或蔬菜，讓營養更完整。"
        if calories <= 700 and protein >= 20:
            return "這餐熱量適中、蛋白質也不錯，整體算是均衡的一餐。"
        if carbs > 90:
            return "這餐碳水偏高，下一餐可以多補蔬菜或蛋白質，讓整體更平衡。"
        if item_count >= 3:
            return "這餐品項比較多，建議留意總份量，避免不知不覺吃過量。"
        return "這餐熱量偏高，若常吃這類餐點，建議搭配更多蔬菜或降低份量。"

    @staticmethod
    def format_profiles_for_response() -> list[dict]:
        profiles = load_food_profiles()
        return [
            {
                "label": label,
                "parent_category": profile.get("parent_category", ""),
                "image_count": len(list_dataset_images(label, profiles)),
                **profile,
            }
            for label, profile in profiles.items()
        ]

    @staticmethod
    def slugify_label(label: str) -> str:
        normalized = label.strip()
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = re.sub(r'[<>:"/\\|?*]+', "", normalized)
        normalized = normalized.strip("._ ")
        if not normalized:
            raise FoodProfileError("Category label cannot be empty or invalid.")
        return normalized

    @classmethod
    def validate_profile_payload(cls, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise FoodProfileError("Request body must be a JSON object.")

        raw_label = str(payload.get("label", "")).strip()
        display_name = str(payload.get("display_name", "")).strip()
        default_portion_label = str(payload.get("default_portion_label", "")).strip()
        parent_category = str(payload.get("parent_category", "")).strip()

        if not raw_label:
            raise FoodProfileError("Field 'label' is required.")
        if not display_name:
            raise FoodProfileError("Field 'display_name' is required.")
        if not default_portion_label:
            raise FoodProfileError("Field 'default_portion_label' is required.")

        label = cls.slugify_label(raw_label)
        nutrition_fields = {}
        for field in ("calories", "protein", "fat", "carbs"):
            value = payload.get(field)
            if value in (None, ""):
                raise FoodProfileError(f"Field '{field}' is required.")
            try:
                nutrition_fields[field] = float(value)
            except (TypeError, ValueError) as exc:
                raise FoodProfileError(f"Field '{field}' must be numeric.") from exc

        return {
            "label": label,
            "display_name": display_name,
            "default_portion_label": default_portion_label,
            "parent_category": cls.slugify_label(parent_category) if parent_category else "",
            **nutrition_fields,
        }

    @classmethod
    def create_profile(cls, payload: dict) -> dict:
        validated = cls.validate_profile_payload(payload)
        profiles = load_food_profiles()
        label = validated["label"]
        if label in profiles:
            raise FoodProfileError("This label already exists.")

        profiles[label] = {
            "display_name": validated["display_name"],
            "default_portion_label": validated["default_portion_label"],
            "parent_category": validated["parent_category"],
            "calories": validated["calories"],
            "protein": validated["protein"],
            "fat": validated["fat"],
            "carbs": validated["carbs"],
        }
        save_food_profiles(profiles)
        return {"label": label, **profiles[label]}

    @classmethod
    def update_profile(cls, label: str, payload: dict) -> dict:
        profiles = load_food_profiles()
        if label not in profiles:
            raise FoodProfileError("Unknown profile label.")

        validated = cls.validate_profile_payload({"label": label, **payload})
        profiles[label] = {
            "display_name": validated["display_name"],
            "default_portion_label": validated["default_portion_label"],
            "parent_category": validated["parent_category"],
            "calories": validated["calories"],
            "protein": validated["protein"],
            "fat": validated["fat"],
            "carbs": validated["carbs"],
        }
        save_food_profiles(profiles)
        return {"label": label, **profiles[label]}

    @classmethod
    def delete_profile(cls, label: str) -> None:
        profiles = load_food_profiles()
        if label not in profiles:
            raise FoodProfileError("Unknown profile label.")
        if len(profiles) <= 1:
            raise FoodProfileError("At least one profile must remain.")
        del profiles[label]
        save_food_profiles(profiles)

    @classmethod
    def add_training_images(cls, label: str, files: list) -> dict:
        profiles = load_food_profiles()
        if label not in profiles:
            raise FoodProfileError("Unknown profile label.")
        if not files:
            raise FoodProfileError("Please upload at least one image.")

        uploaded = []
        for file_storage in files:
            if file_storage is None or file_storage.filename == "":
                continue
            image_bytes = file_storage.read()
            if not image_bytes:
                continue
            filename = save_dataset_image(label, file_storage.filename, image_bytes, profiles)
            uploaded.append(filename)

        if not uploaded:
            raise FoodProfileError("Uploaded files were empty.")

        return {
            "label": label,
            "uploaded_count": len(uploaded),
            "image_count": len(list_dataset_images(label, profiles)),
            "files": uploaded,
        }

    @classmethod
    def add_training_image_bytes(cls, label: str, filename: str, image_bytes: bytes) -> dict:
        profiles = load_food_profiles()
        resolved_label = cls.resolve_lookup_label(label) or label
        if resolved_label not in profiles:
            raise FoodProfileError("Unknown profile label.")
        if not image_bytes:
            raise FoodProfileError("Uploaded file was empty.")

        saved_filename = save_dataset_image(resolved_label, filename or "feedback.jpg", image_bytes, profiles)
        return {
            "label": resolved_label,
            "uploaded_count": 1,
            "image_count": len(list_dataset_images(resolved_label, profiles)),
            "files": [saved_filename],
        }

    @classmethod
    def get_training_images(cls, label: str) -> dict:
        profiles = load_food_profiles()
        if label not in profiles:
            raise FoodProfileError("Unknown profile label.")

        files = list_dataset_images(label, profiles)
        return {"label": label, "files": files, "image_count": len(files)}

    @classmethod
    def delete_training_image(cls, label: str, filename: str) -> dict:
        profiles = load_food_profiles()
        if label not in profiles:
            raise FoodProfileError("Unknown profile label.")
        if not filename:
            raise FoodProfileError("Missing filename.")
        if not delete_dataset_image(label, filename, profiles):
            raise FoodProfileError("Image not found.")

        files = list_dataset_images(label, profiles)
        return {"label": label, "files": files, "image_count": len(files)}
