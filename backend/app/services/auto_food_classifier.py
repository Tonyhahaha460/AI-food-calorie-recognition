from __future__ import annotations

from app.services.classifier import BaseFoodClassifier, ClassificationResult
from app.services.hybrid_food_classifier import HybridFoodClassifier
from app.services.yolo_hf_classifier import YoloHuggingFaceFoodClassifier


YOLO_PREFERRED_SINGLE_LABELS = {
    "apple",
    "banana",
    "cake",
    "cola",
    "french_fries",
    "hot_dog",
    "orange",
    "pizza",
    "sandwich",
    "\u751c\u751c\u5708",
}


class AutoFoodClassifier(BaseFoodClassifier):
    def __init__(
        self,
        hybrid_classifier: HybridFoodClassifier,
        yolo_classifier: YoloHuggingFaceFoodClassifier,
        min_detection_confidence: float,
        single_item_accept_confidence: float,
        min_multi_item_count: int,
    ) -> None:
        self.hybrid_classifier = hybrid_classifier
        self.yolo_classifier = yolo_classifier
        self.min_detection_confidence = float(min_detection_confidence)
        self.single_item_accept_confidence = float(single_item_accept_confidence)
        self.min_multi_item_count = max(1, int(min_multi_item_count))
        self.model_name = "YOLO + Chinese + HuggingFace Auto Food Classifier"

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        try:
            yolo_predictions = self._dedupe_predictions(self.yolo_classifier.predict(image_bytes))
        except Exception:
            yolo_predictions = []
        confident_yolo_predictions = [
            prediction
            for prediction in yolo_predictions
            if prediction.confidence >= self.min_detection_confidence
        ]
        strong_yolo_predictions = [
            prediction for prediction in confident_yolo_predictions if self._is_strong_yolo_prediction(prediction)
        ]

        if len(strong_yolo_predictions) >= self.min_multi_item_count:
            for prediction in strong_yolo_predictions:
                prediction.source = prediction.source or "auto_yolo"
                prediction.decision_reason = prediction.decision_reason or "yolo_multifood"
            return strong_yolo_predictions

        if len(confident_yolo_predictions) == 1:
            top_prediction = confident_yolo_predictions[0]
            if (
                top_prediction.confidence >= self.single_item_accept_confidence
                or self._is_strong_yolo_prediction(top_prediction)
                or top_prediction.label in YOLO_PREFERRED_SINGLE_LABELS
            ):
                top_prediction.source = top_prediction.source or "auto_yolo"
                top_prediction.decision_reason = "yolo_single_food"
                return [top_prediction]

        hybrid_predictions = self.hybrid_classifier.predict(image_bytes)
        if hybrid_predictions:
            return hybrid_predictions

        return strong_yolo_predictions

    @staticmethod
    def _dedupe_predictions(predictions: list[ClassificationResult]) -> list[ClassificationResult]:
        best_by_label: dict[str, ClassificationResult] = {}
        for prediction in predictions:
            existing = best_by_label.get(prediction.label)
            if existing is None or prediction.confidence > existing.confidence:
                best_by_label[prediction.label] = prediction
        return sorted(best_by_label.values(), key=lambda item: item.confidence, reverse=True)

    @staticmethod
    def _is_strong_yolo_prediction(prediction: ClassificationResult) -> bool:
        return prediction.decision_reason in {
            "hf_top1_direct_accept",
            "hf_crop_match",
            "local_crop_fallback",
            "yolo_single_food",
            "yolo_multifood",
        }
