from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageStat

from app.ml.models.mobilenet_classifier import MobileNetClassifier
from app.ml.training.transforms import build_eval_transform
from app.services.nutrition_service import NutritionService
from app.services.training_service import DEVICE, MealCNN, tensor_from_bytes


@dataclass
class ClassificationResult:
    label: str
    confidence: float
    portion_multiplier: float
    source: str = ""
    raw_label: str = ""
    decision_reason: str = ""
    alternatives: list[dict] | None = None


class BaseFoodClassifier:
    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        raise NotImplementedError


class MockFoodClassifier(BaseFoodClassifier):
    def __init__(self, profiles: dict[str, dict]) -> None:
        if not profiles:
            raise ValueError("At least one food profile is required.")
        self.profiles = profiles
        self.labels = list(profiles.keys())

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        resized = image.resize((224, 224))
        stat = ImageStat.Stat(resized)
        avg_r, avg_g, avg_b = stat.mean
        brightness = sum(stat.mean) / 3
        channel_span = max(stat.mean) - min(stat.mean)

        base_scores = {
            "rice": brightness * 0.95 + (255 - channel_span) * 0.35,
            "cake": avg_b * 0.68 + brightness * 0.75,
            "ramen": avg_r * 0.92 + avg_g * 0.38 + brightness * 0.1,
            "sushi": avg_b * 0.88 + (255 - channel_span) * 0.28,
            "hamburger": avg_r * 0.94 + avg_g * 0.32 + (255 - brightness) * 0.2,
            "pizza": avg_r * 1.14 + brightness * 0.12,
            "salad": avg_g * 1.28 + channel_span,
            "steak": avg_r * 1.06 + (255 - brightness) * 0.42,
            "sandwich": brightness * 0.7 + avg_g * 0.33,
            "french_fries": avg_r * 0.82 + brightness * 0.48,
            "fried_egg": brightness * 1.02 + avg_r * 0.18,
        }

        scores = {}
        for index, label in enumerate(self.labels):
            if label in base_scores:
                scores[label] = base_scores[label]
            else:
                scores[label] = brightness * 0.68 + channel_span * 0.22 + (index + 1) * 0.05

        families = {}
        for label, profile in self.profiles.items():
            root = profile.get("parent_category") or label
            families.setdefault(root, []).append(label)

        family_scores = {
            root: max(scores.get(member, 0) for member in members) for root, members in families.items()
        }
        best_root, best_root_score = max(family_scores.items(), key=lambda item: item[1])
        ranked_family = sorted(
            [(label, scores[label]) for label in families[best_root]],
            key=lambda item: item[1],
            reverse=True,
        )

        denominator = sum(score for _, score in ranked_family[:2]) or 1.0
        child_candidates = [
            (label, score)
            for label, score in ranked_family
            if self.profiles[label].get("parent_category") == best_root
        ]
        if child_candidates:
            child_label, child_score = child_candidates[0]
            child_confidence = min(0.98, max(0.62, 0.55 + (child_score / denominator) * 0.72))
            return [
                ClassificationResult(
                    label=child_label,
                    confidence=round(child_confidence, 2),
                    portion_multiplier=1.0,
                )
            ]

        root_confidence = min(0.97, max(0.6, 0.56 + best_root_score / (best_root_score + 120)))
        return [
            ClassificationResult(
                label=best_root,
                confidence=round(root_confidence, 2),
                portion_multiplier=1.0,
            )
        ]


class TrainedFoodClassifier(BaseFoodClassifier):
    def __init__(self, model_path: str, profiles: dict[str, dict]) -> None:
        self.profiles = profiles
        resolved = Path(model_path)
        if not resolved.is_absolute():
            resolved = Path(__file__).resolve().parents[2] / resolved
        if not resolved.exists():
            raise FileNotFoundError(f"Trained model not found: {resolved}")

        with resolved.open("rb") as file:
            self.model_data = pickle.load(file)

        self.backend = self.model_data.get("backend", "legacy")
        self.model_name = self.model_data.get("model_name", "Trained Image Classifier")
        self.class_labels = self.model_data.get("class_labels", [])

        if self.backend == "mobilenet_classifier":
            self.model = MobileNetClassifier(num_classes=len(self.class_labels), pretrained=False).to(DEVICE)
            self.model.load_state_dict(self.model_data["state_dict"])
            self.model.eval()
            self.transform = build_eval_transform()
        elif self.backend == "torch_cnn":
            self.model = MealCNN(class_count=len(self.class_labels)).to(DEVICE)
            self.model.load_state_dict(self.model_data["state_dict"])
            self.model.eval()
        else:
            self.pipeline = self.model_data["pipeline"]

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        if self.backend == "mobilenet_classifier":
            return self._predict_mobilenet(image_bytes)
        if self.backend == "torch_cnn":
            return self._predict_torch(image_bytes)
        return self._predict_legacy(image_bytes)

    def _predict_mobilenet(self, image_bytes: bytes) -> list[ClassificationResult]:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image_tensor = self.transform(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            logits = self.model(image_tensor)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]

        best_index = int(np.argmax(probabilities))
        predicted_label = self.class_labels[best_index]
        confidence = float(probabilities[best_index])
        return self._build_results(predicted_label, confidence)

    def _predict_torch(self, image_bytes: bytes) -> list[ClassificationResult]:
        image_tensor = tensor_from_bytes(image_bytes).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = self.model(image_tensor)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]

        best_index = int(np.argmax(probabilities))
        predicted_label = self.class_labels[best_index]
        confidence = float(probabilities[best_index])
        return self._build_results(predicted_label, confidence)

    def _predict_legacy(self, image_bytes: bytes) -> list[ClassificationResult]:
        from app.services.training_service import extract_features

        features = extract_features(image_bytes).reshape(1, -1)
        predicted_label = self.pipeline.predict(features)[0]
        probabilities = self.pipeline.predict_proba(features)[0]
        class_names = list(self.pipeline.classes_)
        probability_map = dict(zip(class_names, probabilities))
        confidence = float(probability_map.get(predicted_label, float(np.max(probabilities))))
        return self._build_results(predicted_label, confidence)

    @staticmethod
    def _build_results(predicted_label: str, confidence: float) -> list[ClassificationResult]:
        return [
            ClassificationResult(
                label=predicted_label,
                confidence=round(max(0.62, min(confidence, 0.99)), 2),
                portion_multiplier=1.0,
                source="general",
                raw_label=predicted_label,
            )
        ]


class YoloClassificationFoodClassifier(BaseFoodClassifier):
    def __init__(self, model_path: str, profiles: dict[str, dict], top_k: int = 5) -> None:
        self.profiles = profiles
        self.top_k = max(1, int(top_k))
        self.model_name = "UEC-Food100 + Food-101 YOLOv8 Classifier"

        resolved = Path(model_path)
        if not resolved.is_absolute():
            resolved = Path(__file__).resolve().parents[2] / resolved
        if not resolved.exists():
            raise FileNotFoundError(f"YOLO classification model not found: {resolved}")

        if not os.getenv("YOLO_CONFIG_DIR"):
            yolo_config_dir = Path(__file__).resolve().parents[2] / ".cache" / "ultralytics"
            yolo_config_dir.mkdir(parents=True, exist_ok=True)
            os.environ["YOLO_CONFIG_DIR"] = str(yolo_config_dir)

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("ultralytics is not installed. Install it to use MODEL_PROVIDER=yolo_cls.") from exc

        self.model = YOLO(str(resolved))

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            raw_results = self.model(image, verbose=False)

        if not raw_results:
            return []

        result = raw_results[0]
        probabilities = getattr(result, "probs", None)
        if probabilities is None:
            return []

        indexes = [int(index) for index in probabilities.top5[: self.top_k]]
        confidences = [float(value) for value in probabilities.top5conf[: self.top_k]]
        names = getattr(result, "names", {}) or getattr(self.model, "names", {})

        alternatives = []
        mapped_results: list[ClassificationResult] = []

        for index, confidence in zip(indexes, confidences):
            raw_label = str(names.get(index, index))
            mapped_label = NutritionService.resolve_lookup_label(raw_label)
            alternatives.append(
                {
                    "source": "yolo_cls",
                    "label": mapped_label or raw_label,
                    "raw_label": raw_label,
                    "confidence": round(confidence, 4),
                    "rank": len(alternatives) + 1,
                }
            )
            if mapped_label:
                mapped_results.append(
                    ClassificationResult(
                        label=mapped_label,
                        confidence=round(max(0.0, min(confidence, 0.99)), 2),
                        portion_multiplier=1.0,
                        source="yolo_cls",
                        raw_label=raw_label,
                        decision_reason="all_food_classification",
                    )
                )

        if mapped_results:
            mapped_results[0].alternatives = alternatives
            return mapped_results[:1]

        if alternatives:
            best = alternatives[0]
            return [
                ClassificationResult(
                    label=str(best["raw_label"]),
                    confidence=min(float(best["confidence"]), 0.5),
                    portion_multiplier=1.0,
                    source="yolo_cls",
                    raw_label=str(best["raw_label"]),
                    decision_reason="unmapped_all_food_classification",
                    alternatives=alternatives,
                )
            ]

        return []


class FallbackFoodClassifier(BaseFoodClassifier):
    def __init__(
        self,
        primary_classifier: BaseFoodClassifier,
        fallback_classifier: BaseFoodClassifier,
        primary_min_confidence: float,
        primary_min_margin: float,
        fallback_override_confidence: float = 0.72,
    ) -> None:
        self.primary_classifier = primary_classifier
        self.fallback_classifier = fallback_classifier
        self.primary_min_confidence = float(primary_min_confidence)
        self.primary_min_margin = float(primary_min_margin)
        self.fallback_override_confidence = float(fallback_override_confidence)
        self.model_name = f"{primary_classifier.model_name} + fallback"

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        primary_predictions = self.primary_classifier.predict(image_bytes)
        primary_top = primary_predictions[0] if primary_predictions else None
        visual_prediction = self._predict_simple_visual_food(image_bytes)

        try:
            fallback_predictions = self.fallback_classifier.predict(image_bytes)
        except Exception:
            fallback_predictions = []

        fallback_top = fallback_predictions[0] if fallback_predictions else None
        consensus_prediction = self._build_primary_fallback_consensus(primary_top, fallback_top)
        if consensus_prediction is not None:
            return [consensus_prediction]

        if visual_prediction and self._should_visual_override_primary(visual_prediction, primary_top):
            return [visual_prediction]

        if primary_top and self._should_accept_primary(primary_top):
            return primary_predictions

        if visual_prediction:
            return [visual_prediction]

        if fallback_predictions:
            return fallback_predictions
        return primary_predictions

    @staticmethod
    def _canonical_label(prediction: ClassificationResult | None) -> str | None:
        if prediction is None:
            return None
        return NutritionService.resolve_lookup_label(prediction.label) or prediction.label

    def _build_primary_fallback_consensus(
        self,
        primary_top: ClassificationResult | None,
        fallback_top: ClassificationResult | None,
    ) -> ClassificationResult | None:
        if primary_top is None or fallback_top is None:
            return None
        primary_label = self._canonical_label(primary_top)
        fallback_label = self._canonical_label(fallback_top)
        if not primary_label or primary_label != fallback_label:
            return None
        if primary_top.decision_reason not in {
            "all_food_classification",
            "unmapped_all_food_classification",
        }:
            return None

        confidence = min(
            0.99,
            max(float(primary_top.confidence), float(fallback_top.confidence)) + 0.05,
        )
        alternatives = []
        alternatives.extend(primary_top.alternatives or [])
        alternatives.extend(fallback_top.alternatives or [])
        return ClassificationResult(
            label=primary_label,
            confidence=round(confidence, 2),
            portion_multiplier=1.0,
            source="yolo_hybrid_consensus",
            raw_label=primary_top.raw_label or fallback_top.raw_label,
            decision_reason="primary_fallback_agree",
            alternatives=alternatives,
        )

    def _should_use_fallback(
        self,
        primary_top: ClassificationResult | None,
        fallback_top: ClassificationResult | None,
    ) -> bool:
        if fallback_top is None:
            return False
        if primary_top is None:
            return True
        if fallback_top.label == primary_top.label:
            return float(fallback_top.confidence) > float(primary_top.confidence)
        return float(fallback_top.confidence) >= self.fallback_override_confidence

    def _should_accept_primary(self, prediction: ClassificationResult) -> bool:
        if prediction.decision_reason != "all_food_classification":
            return False
        if float(prediction.confidence) < self.primary_min_confidence:
            return False

        alternatives = prediction.alternatives or []
        if len(alternatives) < 2:
            return True

        selected_index = next(
            (
                index
                for index, alternative in enumerate(alternatives)
                if str(alternative.get("raw_label", "")) == str(prediction.raw_label)
            ),
            0,
        )
        top_confidence = float(alternatives[0].get("confidence", prediction.confidence))
        selected_confidence = float(
            alternatives[selected_index].get("confidence", prediction.confidence)
        )
        if selected_index > 0:
            return top_confidence - selected_confidence <= self.primary_min_margin

        second_confidence = float(alternatives[1].get("confidence", 0.0))
        return top_confidence - second_confidence >= self.primary_min_margin

    def _has_usable_prediction(
        self,
        primary_top: ClassificationResult | None,
        fallback_top: ClassificationResult | None,
    ) -> bool:
        if primary_top and self._should_accept_primary(primary_top):
            return True
        if fallback_top and float(fallback_top.confidence) >= self.fallback_override_confidence:
            return True
        return False

    @staticmethod
    def _should_visual_override_primary(
        visual_prediction: ClassificationResult,
        primary_top: ClassificationResult | None,
    ) -> bool:
        if primary_top is None:
            return True
        if visual_prediction.decision_reason not in {
            "single_red_fruit_visual_fallback",
            "orange_fruit_visual_fallback",
        }:
            return False
        primary_label = NutritionService.resolve_lookup_label(primary_top.label) or primary_top.label
        visual_label = NutritionService.resolve_lookup_label(visual_prediction.label) or visual_prediction.label
        if primary_label == visual_label:
            return False
        dessert_or_bread_labels = {
            "bagel",
            "bread",
            "cake",
            "cheesecake",
            "cup_cakes",
            "donut",
            "donuts",
            "macarons",
            "甜甜圈",
        }
        if float(primary_top.confidence) <= 0.55:
            return True
        return str(primary_label) in dessert_or_bread_labels and float(primary_top.confidence) <= 0.72

    @staticmethod
    def _predict_simple_visual_food(image_bytes: bytes) -> ClassificationResult | None:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB").resize((160, 160))
            pixels = list(image.getdata())

        object_pixels = [
            (r, g, b)
            for r, g, b in pixels
            if min(r, g, b) < 245 and max(r, g, b) - min(r, g, b) > 25
        ]
        if not object_pixels:
            return None

        object_ratio = len(object_pixels) / len(pixels)
        red_pixels = [
            (r, g, b)
            for r, g, b in object_pixels
            if r > 115 and r > g * 1.12 and r > b * 1.18
        ]
        orange_pixels = [
            (r, g, b)
            for r, g, b in object_pixels
            if r > 120 and 65 < g < 190 and b < 130 and r > g * 1.05 and g > b * 1.2
        ]
        deep_orange_pixels = [
            (r, g, b)
            for r, g, b in object_pixels
            if r > 145 and 50 < g < 180 and b < 120 and r > g * 1.15
        ]
        green_pixels = [
            (r, g, b)
            for r, g, b in object_pixels
            if g > 90 and g > r * 1.12 and g > b * 1.12
        ]
        red_ratio = len(red_pixels) / len(object_pixels)
        orange_ratio = len(orange_pixels) / len(object_pixels)
        deep_orange_ratio = len(deep_orange_pixels) / len(object_pixels)
        green_ratio = len(green_pixels) / len(object_pixels)
        white_background_ratio = sum(
            1 for r, g, b in pixels if r > 235 and g > 235 and b > 235
        ) / len(pixels)

        has_light_or_single_object_background = white_background_ratio >= 0.20 or object_ratio <= 0.35
        if (
            0.18 <= object_ratio <= 0.78
            and red_ratio >= 0.65
            and orange_ratio / max(red_ratio, 0.01) <= 0.55
            and green_ratio <= 0.05
            and has_light_or_single_object_background
        ):
            return ClassificationResult(
                label="apple",
                confidence=0.86,
                portion_multiplier=1.0,
                source="visual_fallback",
                raw_label="apple",
                decision_reason="single_red_fruit_visual_fallback",
            )
        is_orange_with_leaf_or_stem = (
            0.30 <= object_ratio <= 0.85
            and (orange_ratio >= 0.45 or deep_orange_ratio >= 0.42)
            and (green_ratio >= 0.03 or deep_orange_ratio >= 0.55)
            and white_background_ratio <= 0.15
        )
        is_full_frame_orange_cluster = (
            object_ratio >= 0.62
            and red_ratio >= 0.55
            and (orange_ratio >= 0.48 or deep_orange_ratio >= 0.45)
            and green_ratio <= 0.12
            and white_background_ratio <= 0.05
        )
        if is_orange_with_leaf_or_stem or is_full_frame_orange_cluster:
            return ClassificationResult(
                label="orange",
                confidence=0.84,
                portion_multiplier=1.0,
                source="visual_fallback",
                raw_label="orange",
                decision_reason="orange_fruit_visual_fallback",
            )
        return None
