from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
from typing import Iterable

import torch
from huggingface_hub import snapshot_download
from PIL import Image

from app.services.classifier import BaseFoodClassifier, ClassificationResult, TrainedFoodClassifier
from app.services.nutrition_service import NutritionService


FOODISH_DETECTION_NAMES = {
    "apple",
    "banana",
    "broccoli",
    "cake",
    "carrot",
    "donut",
    "hot_dog",
    "orange",
    "pizza",
    "sandwich",
}

DETECTION_LABEL_TO_PROFILE_LABEL = {
    "apple": "apple",
    "banana": "banana",
    "broccoli": "broccoli",
    "cake": "cake",
    "carrot": "carrot",
    "donut": "\u751c\u751c\u5708",
    "hot_dog": "hot_dog",
    "orange": "orange",
    "pizza": "pizza",
    "sandwich": "sandwich",
}


class YoloHuggingFaceFoodClassifier(BaseFoodClassifier):
    def __init__(
        self,
        profiles: dict[str, dict],
        detector_model: str,
        classifier_model: str,
        detection_confidence: float,
        max_detections: int,
        top_k: int,
        direct_accept_threshold: float,
        fallback_model_path: str | None = None,
    ) -> None:
        self.profiles = profiles
        self.detector_model_name = detector_model
        self.classifier_model_name = classifier_model
        self.detection_confidence = max(0.05, min(float(detection_confidence), 0.95))
        self.max_detections = max(1, int(max_detections))
        self.top_k = max(1, int(top_k))
        self.direct_accept_threshold = max(0.5, min(float(direct_accept_threshold), 0.99))
        self.model_name = "YOLO + HuggingFace Food"

        self._detector = None
        self._classifier = None
        self._fallback_classifier = None

        if fallback_model_path:
            try:
                self._fallback_classifier = TrainedFoodClassifier(
                    model_path=fallback_model_path,
                    profiles=profiles,
                )
            except Exception:
                self._fallback_classifier = None

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            predictions = self._predict_from_detections(image)
            if predictions:
                return predictions

            full_image_prediction = self._classify_image(image, base_confidence=0.72)
            if full_image_prediction is not None:
                return [full_image_prediction]

        if self._fallback_classifier is not None:
            return self._fallback_classifier.predict(image_bytes)

        return []

    def _predict_from_detections(self, image: Image.Image) -> list[ClassificationResult]:
        detector = self._get_detector()
        raw_results = detector(
            image,
            conf=self.detection_confidence,
            max_det=self.max_detections,
            verbose=False,
        )

        predictions: list[ClassificationResult] = []
        seen_signatures: set[tuple[str, tuple[int, int, int, int]]] = set()

        for result in raw_results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                label_name = self._resolve_detection_name(box)
                if label_name not in FOODISH_DETECTION_NAMES:
                    continue

                coordinates = tuple(int(round(value)) for value in box.xyxy[0].tolist())
                if coordinates in {()}:
                    continue
                if coordinates[2] - coordinates[0] < 32 or coordinates[3] - coordinates[1] < 32:
                    continue

                signature = (label_name, coordinates)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)

                crop = image.crop(coordinates)
                detection_score = float(box.conf.item())
                prediction = self._classify_image(
                    crop,
                    base_confidence=detection_score,
                    detection_label=label_name,
                )
                if prediction is not None:
                    predictions.append(prediction)

        predictions.sort(key=lambda item: item.confidence, reverse=True)
        return predictions

    def _classify_image(
        self,
        image: Image.Image,
        base_confidence: float,
        detection_label: str = "",
    ) -> ClassificationResult | None:
        classifier = self._get_classifier()
        raw_predictions = classifier(image, top_k=self.top_k)
        if isinstance(raw_predictions, dict):
            raw_predictions = [raw_predictions]

        alternatives: list[dict] = []
        aggregated_candidates: dict[str, dict[str, float | str]] = {}

        for prediction in raw_predictions:
            raw_label = str(prediction.get("label", "")).strip()
            mapped_label = NutritionService.resolve_lookup_label(raw_label)
            classification_score = float(prediction.get("score", 0.0))
            alternatives.append(
                {
                    "source": "general_hf",
                    "label": mapped_label or raw_label,
                    "raw_label": raw_label,
                    "confidence": round(classification_score, 4),
                }
            )
            if not mapped_label:
                continue
            bucket = aggregated_candidates.setdefault(
                mapped_label,
                {
                    "score": 0.0,
                    "best_score": 0.0,
                    "raw_label": raw_label,
                },
            )
            bucket["score"] = float(bucket["score"]) + classification_score
            if classification_score >= float(bucket["best_score"]):
                bucket["best_score"] = classification_score
                bucket["raw_label"] = raw_label

        if aggregated_candidates:
            best_label, candidate_values = sorted(
                aggregated_candidates.items(),
                key=lambda item: (float(item[1]["score"]), float(item[1]["best_score"])),
                reverse=True,
            )[0]
            best_raw_label = str(candidate_values["raw_label"])
            best_score = float(candidate_values["score"])
            if best_score >= self.direct_accept_threshold:
                return ClassificationResult(
                    label=best_label,
                    confidence=round(min(0.99, max(best_score, self.direct_accept_threshold)), 2),
                    portion_multiplier=1.0,
                    source="yolo_hf",
                    raw_label=best_raw_label,
                    decision_reason="hf_top1_direct_accept",
                    alternatives=alternatives,
                )
            if best_score >= 0.45:
                confidence = min(0.99, max(0.62, max((base_confidence + best_score) / 2, best_score * 0.88)))
                return ClassificationResult(
                    label=best_label,
                    confidence=round(confidence, 2),
                    portion_multiplier=1.0,
                    source="yolo_hf",
                    raw_label=best_raw_label,
                    decision_reason="hf_crop_match",
                    alternatives=alternatives,
                )

        detection_mapped_label = self._map_detection_label(detection_label)
        if detection_mapped_label:
            confidence = min(0.95, max(0.62, base_confidence))
            return ClassificationResult(
                label=detection_mapped_label,
                confidence=round(confidence, 2),
                portion_multiplier=1.0,
                source="yolo_detection",
                raw_label=detection_label,
                decision_reason="detection_label_fallback",
                alternatives=alternatives,
            )

        if self._fallback_classifier is not None:
            fallback_prediction = self._classify_with_local_model(image, base_confidence)
            if fallback_prediction is not None:
                fallback_prediction.alternatives = alternatives + (fallback_prediction.alternatives or [])
                return fallback_prediction

        return None

    def _classify_with_local_model(
        self,
        image: Image.Image,
        base_confidence: float,
    ) -> ClassificationResult | None:
        if self._fallback_classifier is None:
            return None

        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        fallback_predictions = self._fallback_classifier.predict(buffer.getvalue())
        if not fallback_predictions:
            return None

        best = fallback_predictions[0]
        confidence = min(0.95, max(0.58, (base_confidence + best.confidence) / 2))
        return ClassificationResult(
            label=best.label,
            confidence=round(confidence, 2),
            portion_multiplier=best.portion_multiplier,
            source="yolo_local_fallback",
            raw_label=best.raw_label or best.label,
            decision_reason="local_crop_fallback",
            alternatives=best.alternatives or [],
        )

    def _get_detector(self):
        if self._detector is None:
            if not os.getenv("YOLO_CONFIG_DIR"):
                hf_home = os.getenv("HF_HOME", "").strip()
                if hf_home:
                    yolo_config_dir = Path(hf_home).parent / "ultralytics"
                else:
                    yolo_config_dir = Path(__file__).resolve().parents[2] / ".cache" / "ultralytics"
                yolo_config_dir.mkdir(parents=True, exist_ok=True)
                os.environ["YOLO_CONFIG_DIR"] = str(yolo_config_dir)
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError(
                    "ultralytics is not installed. Install it to use MODEL_PROVIDER=yolo_hf."
                ) from exc

            self._detector = YOLO(self.detector_model_name)
        return self._detector

    def _get_classifier(self):
        if self._classifier is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "transformers is not installed. Install it to use MODEL_PROVIDER=yolo_hf."
                ) from exc

            device = 0 if torch.cuda.is_available() else -1
            resolved_model_path = self._resolve_classifier_source(self.classifier_model_name)
            self._classifier = pipeline(
                "image-classification",
                model=resolved_model_path,
                device=device,
            )
        return self._classifier

    def _resolve_detection_name(self, box) -> str:
        detector = self._get_detector()
        names = getattr(detector, "names", {})
        raw_name = names.get(int(box.cls.item()), "")
        return NutritionService.normalize_label_key(str(raw_name))

    @staticmethod
    def _map_detection_label(raw_label: str) -> str | None:
        if not raw_label:
            return None
        mapped = DETECTION_LABEL_TO_PROFILE_LABEL.get(raw_label)
        if mapped:
            return mapped
        return NutritionService.resolve_lookup_label(raw_label)

    @staticmethod
    def _resolve_classifier_source(model_name: str) -> str:
        if Path(model_name).exists():
            return model_name

        cache_roots = []
        hf_home = os.getenv("HF_HOME", "").strip()
        if hf_home:
            cache_roots.append(Path(hf_home) / "hub")

        backend_root = Path(__file__).resolve().parents[2]
        cache_roots.append(backend_root / ".cache" / "huggingface" / "hub")

        for root in cache_roots:
            cache_model_dir = root / f"models--{model_name.replace('/', '--')}" / "snapshots"
            if cache_model_dir.exists():
                snapshots = sorted(path for path in cache_model_dir.iterdir() if path.is_dir())
                if snapshots:
                    return str(snapshots[-1])

        try:
            return snapshot_download(repo_id=model_name, local_files_only=True)
        except Exception:
            return model_name
