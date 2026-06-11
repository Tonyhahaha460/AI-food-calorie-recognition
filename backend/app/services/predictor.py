from __future__ import annotations

from base64 import b64encode
from typing import Any

from PIL import Image

from app.ml.inference.infer_regression import MobileNetRegressionInference
from app.services.auto_food_classifier import AutoFoodClassifier
from app.services.classifier import (
    ClassificationResult,
    FallbackFoodClassifier,
    MockFoodClassifier,
    TrainedFoodClassifier,
    YoloClassificationFoodClassifier,
)
from app.services.history_service import HistoryService
from app.services.hybrid_food_classifier import HybridFoodClassifier
from app.services.nutrition_service import NutritionService
from app.services.yolo_hf_classifier import YoloHuggingFaceFoodClassifier
from app.utils.image_utils import allowed_file, normalize_image_bytes


class PredictionError(Exception):
    pass


UNCERTAIN_FOOD_NAME = "\u5f85\u78ba\u8a8d\u9910\u9ede"
UNCERTAIN_PORTION = "\u5f85\u78ba\u8a8d"
UNCERTAIN_MESSAGE = (
    "\u9019\u5f35\u7167\u7247\u76ee\u524d\u6c92\u6709\u8fa8\u8b58\u51fa\u8db3\u5920\u53ef\u4fe1\u7684"
    "\u98df\u7269\u540d\u7a31\uff0c\u5efa\u8b70\u6539\u62cd\u55ae\u4e00\u9053\u83dc\u6216\u66f4\u6e05"
    "\u695a\u7684\u89d2\u5ea6\u3002"
)


class PredictorService:
    def __init__(self, config) -> None:
        self.config = config
        self.classifier = self._get_classifier()
        self.regression_inference = self._get_regression_inference()

    def _build_hybrid_classifier(self, profiles: dict[str, dict]) -> HybridFoodClassifier:
        return HybridFoodClassifier(
            profiles=profiles,
            general_model_path=self.config["TRAINED_MODEL_PATH"],
            general_hf_model_name=self.config["HF_IMAGE_CLASSIFIER_MODEL"],
            chinese_model_name=self.config["CHINESE_FOOD_MODEL_NAME"],
            chinese_confidence_threshold=self.config["CHINESE_CONFIDENCE_THRESHOLD"],
            general_confidence_threshold=self.config["GENERAL_CONFIDENCE_THRESHOLD"],
            score_margin=self.config["HYBRID_SCORE_MARGIN"],
            general_top_k=self.config["HF_CLASSIFIER_TOP_K"],
            chinese_top_k=self.config["CHINESE_TOP_K"],
            local_priority_threshold=self.config["LOCAL_PRIORITY_THRESHOLD"],
        )

    def _get_classifier(self):
        model_provider = self.config["MODEL_PROVIDER"]
        profiles = NutritionService.get_all_profiles()

        if model_provider == "mock":
            return MockFoodClassifier(profiles=profiles)

        if model_provider in {"trained", "food_classifier"}:
            return TrainedFoodClassifier(
                model_path=self.config["TRAINED_MODEL_PATH"],
                profiles=profiles,
            )

        if model_provider in {"yolo_cls", "all_food_classifier"}:
            primary_yolo_classifier = YoloClassificationFoodClassifier(
                model_path=self.config["ALL_FOOD_CLASSIFIER_MODEL_PATH"],
                profiles=profiles,
                top_k=self.config["HF_CLASSIFIER_TOP_K"],
            )
            secondary_yolo_classifier = YoloClassificationFoodClassifier(
                model_path=self.config["SECONDARY_FOOD_CLASSIFIER_MODEL_PATH"],
                profiles=profiles,
                top_k=self.config["HF_CLASSIFIER_TOP_K"],
            )
            hybrid_fallback_classifier = self._build_hybrid_classifier(profiles)
            secondary_fallback_classifier = FallbackFoodClassifier(
                primary_classifier=secondary_yolo_classifier,
                fallback_classifier=hybrid_fallback_classifier,
                primary_min_confidence=self.config["SECONDARY_YOLO_CLS_MIN_ACCEPTED_CONFIDENCE"],
                primary_min_margin=self.config["SECONDARY_YOLO_CLS_MIN_CONFIDENCE_MARGIN"],
            )
            return FallbackFoodClassifier(
                primary_classifier=primary_yolo_classifier,
                fallback_classifier=secondary_fallback_classifier,
                primary_min_confidence=self.config["YOLO_CLS_MIN_ACCEPTED_CONFIDENCE"],
                primary_min_margin=self.config["YOLO_CLS_MIN_CONFIDENCE_MARGIN"],
            )

        if model_provider in {"hybrid_food_classifier", "hybrid_classifier"}:
            return self._build_hybrid_classifier(profiles)

        if model_provider in {"yolo_hf", "yolo_huggingface"}:
            return YoloHuggingFaceFoodClassifier(
                profiles=profiles,
                detector_model=self.config["YOLO_MODEL_NAME"],
                classifier_model=self.config["HF_IMAGE_CLASSIFIER_MODEL"],
                detection_confidence=self.config["YOLO_DETECTION_CONFIDENCE"],
                max_detections=self.config["YOLO_MAX_DETECTIONS"],
                top_k=self.config["HF_CLASSIFIER_TOP_K"],
                direct_accept_threshold=self.config["YOLO_HF_DIRECT_ACCEPT_THRESHOLD"],
                fallback_model_path=self.config["TRAINED_MODEL_PATH"],
            )

        if model_provider in {"auto_food_classifier", "auto_classifier"}:
            hybrid_classifier = self._build_hybrid_classifier(profiles)
            yolo_classifier = YoloHuggingFaceFoodClassifier(
                profiles=profiles,
                detector_model=self.config["YOLO_MODEL_NAME"],
                classifier_model=self.config["HF_IMAGE_CLASSIFIER_MODEL"],
                detection_confidence=self.config["YOLO_DETECTION_CONFIDENCE"],
                max_detections=self.config["YOLO_MAX_DETECTIONS"],
                top_k=self.config["HF_CLASSIFIER_TOP_K"],
                direct_accept_threshold=self.config["YOLO_HF_DIRECT_ACCEPT_THRESHOLD"],
                fallback_model_path=None,
            )
            return AutoFoodClassifier(
                hybrid_classifier=hybrid_classifier,
                yolo_classifier=yolo_classifier,
                min_detection_confidence=self.config["AUTO_DETECTION_MIN_CONFIDENCE"],
                single_item_accept_confidence=self.config["AUTO_SINGLE_ITEM_ACCEPT_CONFIDENCE"],
                min_multi_item_count=self.config["AUTO_MULTI_ITEM_COUNT"],
            )

        if model_provider == "mobilenet_regression":
            return None

        raise PredictionError(f"Unsupported MODEL_PROVIDER: {model_provider}")

    def _get_regression_inference(self):
        if self.config["MODEL_PROVIDER"] != "mobilenet_regression":
            return None
        return MobileNetRegressionInference(
            model_path=self.config["MOBILENET_REGRESSION_MODEL_PATH"],
        )

    def predict(self, file_storage, history_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not allowed_file(file_storage.filename, self.config["ALLOWED_EXTENSIONS"]):
            raise PredictionError("Only JPG and PNG images are supported.")

        image_bytes = file_storage.read()
        if not image_bytes:
            raise PredictionError("Uploaded file is empty.")

        try:
            normalized_bytes = normalize_image_bytes(image_bytes)
        except (OSError, ValueError, Image.DecompressionBombError):
            raise PredictionError("Invalid image file. Please upload a valid JPG or PNG image.")

        if self.config["MODEL_PROVIDER"] == "mobilenet_regression":
            return self._predict_with_regression(normalized_bytes, history_context or {})

        return self._predict_with_classifier(normalized_bytes, history_context or {})

    def _predict_with_classifier(self, normalized_bytes: bytes, history_context: dict[str, Any]) -> dict[str, Any]:
        if self.classifier is None:
            raise PredictionError("Classification model is not initialized.")

        predictions = self.classifier.predict(normalized_bytes)
        items: list[dict[str, Any]] = []
        accepted_items: list[dict[str, Any]] = []

        if not predictions:
            items.append(self._build_no_prediction_item())
        else:
            for prediction in predictions:
                item = self._build_item_from_prediction(prediction)
                items.append(item)
                if not item.get("is_uncertain"):
                    accepted_items.append(item)

        totals = self._build_totals(accepted_items)
        has_uncertain_items = any(item.get("is_uncertain") for item in items)
        response = {
            "items": items,
            "total_calories": totals["calories"],
            "total_nutrition": totals,
            "suggestion": self._build_classifier_suggestion(totals, items),
            "image_preview": self._to_data_url(normalized_bytes),
            "analysis_mode": "classification_lookup",
            "model_name": getattr(self.classifier, "model_name", "Food Classifier"),
            "has_uncertain_items": has_uncertain_items,
        }
        history_record = HistoryService.add_record(
            {
                "image_preview": response["image_preview"],
                "items": items,
                "total_calories": response["total_calories"],
                "suggestion": response["suggestion"],
            },
            history_context,
        )
        response["history_record_id"] = history_record.get("history_record_id")
        return response

    def _build_item_from_prediction(self, prediction: ClassificationResult) -> dict[str, Any]:
        base_item = {
            "confidence": prediction.confidence,
            "prediction_source": prediction.source or "",
            "raw_prediction_label": prediction.raw_label or "",
            "decision_reason": prediction.decision_reason or "",
            "alternatives": prediction.alternatives or [],
        }

        min_confidence = self.config["MIN_ACCEPTED_CONFIDENCE"]
        if prediction.source == "yolo_cls":
            min_confidence = self.config.get("YOLO_CLS_MIN_ACCEPTED_CONFIDENCE", min_confidence)

        if prediction.confidence < min_confidence:
            base_item.update(
                {
                    "food_name": UNCERTAIN_FOOD_NAME,
                    "estimated_portion": UNCERTAIN_PORTION,
                    "nutrition": {
                        "calories": None,
                        "protein": None,
                        "fat": None,
                        "carbs": None,
                    },
                    "is_uncertain": True,
                    "uncertain_message": UNCERTAIN_MESSAGE,
                }
            )
            return base_item

        estimated = NutritionService.estimate_item(prediction.label, prediction.portion_multiplier)
        base_item.update(
            {
                "food_name": estimated["food_name"],
                "estimated_portion": estimated["estimated_portion"],
                "nutrition": estimated["nutrition"],
                "nutrition_source": estimated.get("nutrition_source", ""),
                "is_uncertain": False,
            }
        )
        return base_item

    def _build_no_prediction_item(self) -> dict[str, Any]:
        return {
            "food_name": UNCERTAIN_FOOD_NAME,
            "confidence": 0.0,
            "estimated_portion": UNCERTAIN_PORTION,
            "nutrition": {
                "calories": None,
                "protein": None,
                "fat": None,
                "carbs": None,
            },
            "prediction_source": "",
            "raw_prediction_label": "",
            "decision_reason": "no_prediction",
            "alternatives": [],
            "is_uncertain": True,
            "uncertain_message": UNCERTAIN_MESSAGE,
        }

    @staticmethod
    def _build_totals(items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            return {
                "calories": None,
                "protein": None,
                "fat": None,
                "carbs": None,
            }
        return NutritionService.combine_totals(items)

    @staticmethod
    def _build_classifier_suggestion(totals: dict[str, Any], items: list[dict[str, Any]]) -> str:
        certain_items = [item for item in items if not item.get("is_uncertain")]
        if not certain_items:
            return (
                "\u9019\u6b21\u6c92\u6709\u6210\u529f\u8fa8\u8b58\u51fa\u53ef\u4fe1\u7684\u9910\u9ede\uff0c"
                "\u5efa\u8b70\u6539\u62cd\u55ae\u4e00\u9053\u83dc\u3001\u5149\u7dda\u66f4\u7a69\u5b9a\uff0c"
                "\u6216\u907f\u514d\u904e\u591a\u80cc\u666f\u5e72\u64fe\u3002"
            )
        if any(item.get("is_uncertain") for item in items):
            return (
                "\u9019\u5f35\u7167\u7247\u88e1\u6709\u90e8\u5206\u5167\u5bb9\u4ecd\u5728\u4f4e\u4fe1\u5fc3"
                "\u7bc4\u570d\uff0c\u5efa\u8b70\u53ea\u62cd\u4e3b\u98df\u6216\u62c9\u8fd1\u4e3b\u9ad4\uff0c"
                "\u7d50\u679c\u6703\u66f4\u7a69\u5b9a\u3002"
            )
        return NutritionService.build_suggestion(totals, len(certain_items))

    def _predict_with_regression(self, normalized_bytes: bytes, history_context: dict[str, Any]) -> dict[str, Any]:
        if self.regression_inference is None:
            raise PredictionError("Regression model is not initialized.")

        predicted_nutrition = self.regression_inference.predict_nutrition(normalized_bytes)
        matched = NutritionService.match_profile_from_regression(predicted_nutrition)
        item = {
            "food_name": "AI \u71df\u990a\u4f30\u7b97",
            "confidence": 0.9,
            "estimated_portion": matched["estimated_portion"],
            "nutrition": matched["nutrition"],
            "closest_match_name": matched["food_name"],
            "closest_parent_name": matched.get("parent_display_name", ""),
            "closest_match_source": matched.get("source", ""),
            "match_distance": matched.get("match_distance"),
        }
        totals = NutritionService.combine_totals([item])
        response = {
            "items": [item],
            "total_calories": totals["calories"],
            "total_nutrition": totals,
            "suggestion": NutritionService.build_suggestion(totals, 1),
            "image_preview": self._to_data_url(normalized_bytes),
            "model_name": self.regression_inference.model_name,
            "analysis_mode": "regression",
        }
        history_record = HistoryService.add_record(
            {
                "image_preview": response["image_preview"],
                "items": response["items"],
                "total_calories": response["total_calories"],
                "suggestion": response["suggestion"],
            },
            history_context,
        )
        response["history_record_id"] = history_record.get("history_record_id")
        return response

    @staticmethod
    def _to_data_url(image_bytes: bytes) -> str:
        return f"data:image/jpeg;base64,{b64encode(image_bytes).decode('utf-8')}"
