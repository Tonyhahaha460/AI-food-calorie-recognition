from __future__ import annotations

from app.data.food_profiles import list_dataset_images
from app.services.chinese_food_classifier import ChineseFoodClassifier
from app.services.classifier import BaseFoodClassifier, ClassificationResult, TrainedFoodClassifier
from app.services.huggingface_food_classifier import HuggingFaceFoodClassifier


class HybridFoodClassifier(BaseFoodClassifier):
    def __init__(
        self,
        profiles: dict[str, dict],
        general_model_path: str,
        general_hf_model_name: str,
        chinese_model_name: str,
        chinese_confidence_threshold: float,
        general_confidence_threshold: float,
        score_margin: float,
        general_top_k: int,
        chinese_top_k: int,
        local_priority_threshold: float,
    ) -> None:
        self.local_classifier = TrainedFoodClassifier(
            model_path=general_model_path,
            profiles=profiles,
        )
        self.general_classifier = HuggingFaceFoodClassifier(
            model_name=general_hf_model_name,
            top_k=general_top_k,
        )
        self.chinese_classifier = ChineseFoodClassifier(
            model_name=chinese_model_name,
            top_k=chinese_top_k,
        )
        self.chinese_confidence_threshold = float(chinese_confidence_threshold)
        self.general_confidence_threshold = float(general_confidence_threshold)
        self.score_margin = float(score_margin)
        self.local_priority_threshold = float(local_priority_threshold)
        self.local_priority_labels = {
            label for label in profiles if list_dataset_images(label, profiles)
        }
        self.model_name = "Chinese + HuggingFace + Local Hybrid Food Classifier"

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        chinese_predictions = self.chinese_classifier.predict(image_bytes)
        hf_general_predictions = self.general_classifier.predict(image_bytes)
        local_predictions = self.local_classifier.predict(image_bytes)
        general_predictions = self._select_general_predictions(
            hf_general_predictions=hf_general_predictions,
            local_predictions=local_predictions,
        )

        chinese_top = chinese_predictions[0] if chinese_predictions else None
        general_top = general_predictions[0] if general_predictions else None

        if chinese_top and general_top and chinese_top.label == general_top.label:
            merged_confidence = max(chinese_top.confidence, general_top.confidence)
            return [
                ClassificationResult(
                    label=chinese_top.label,
                    confidence=round(min(0.99, merged_confidence + 0.05), 2),
                    portion_multiplier=1.0,
                    source="hybrid",
                    raw_label=chinese_top.raw_label,
                    decision_reason="models_agree",
                    alternatives=self._build_alternatives(
                        chinese_predictions,
                        hf_general_predictions,
                        local_predictions,
                    ),
                )
            ]

        consensus_prediction = self._build_consensus_prediction(
            chinese_predictions,
            general_predictions,
            local_predictions,
            hf_general_predictions,
        )
        if consensus_prediction is not None:
            return [consensus_prediction]

        if chinese_top and chinese_top.confidence >= self.chinese_confidence_threshold:
            return [
                ClassificationResult(
                    label=chinese_top.label,
                    confidence=round(min(0.99, chinese_top.confidence), 2),
                    portion_multiplier=1.0,
                    source="chinese",
                    raw_label=chinese_top.raw_label,
                    decision_reason="high_chinese_confidence",
                    alternatives=self._build_alternatives(
                        chinese_predictions,
                        hf_general_predictions,
                        local_predictions,
                    ),
                )
            ]

        if general_top and general_top.confidence >= self.general_confidence_threshold:
            return [
                ClassificationResult(
                    label=general_top.label,
                    confidence=general_top.confidence,
                    portion_multiplier=1.0,
                    source="general",
                    raw_label=general_top.raw_label or general_top.label,
                    decision_reason="high_general_confidence",
                    alternatives=self._build_alternatives(
                        chinese_predictions,
                        hf_general_predictions,
                        local_predictions,
                    ),
                )
            ]

        if chinese_top and general_top:
            if chinese_top.confidence >= general_top.confidence + self.score_margin:
                chosen = chinese_top
                source = "chinese"
                reason = "chinese_margin_win"
            else:
                chosen = general_top
                source = "general"
                reason = "general_margin_win"
            return [
                ClassificationResult(
                    label=chosen.label,
                    confidence=round(max(chosen.confidence, 0.62), 2),
                    portion_multiplier=1.0,
                    source=source,
                    raw_label=chosen.raw_label or chosen.label,
                    decision_reason=reason,
                    alternatives=self._build_alternatives(
                        chinese_predictions,
                        hf_general_predictions,
                        local_predictions,
                    ),
                )
            ]

        if chinese_top:
            chinese_top.decision_reason = "only_chinese_available"
            chinese_top.alternatives = self._build_alternatives(
                chinese_predictions,
                hf_general_predictions,
                local_predictions,
            )
            return [chinese_top]

        if general_top:
            general_top.decision_reason = "only_general_available"
            general_top.alternatives = self._build_alternatives(
                chinese_predictions,
                hf_general_predictions,
                local_predictions,
            )
            return [general_top]

        return self.local_classifier.predict(image_bytes)

    def _select_general_predictions(
        self,
        hf_general_predictions: list[ClassificationResult],
        local_predictions: list[ClassificationResult],
    ) -> list[ClassificationResult]:
        hf_top = hf_general_predictions[0] if hf_general_predictions else None
        local_top = local_predictions[0] if local_predictions else None

        if hf_top and local_top and hf_top.label == local_top.label:
            return [
                ClassificationResult(
                    label=hf_top.label,
                    confidence=round(min(0.99, max(hf_top.confidence, local_top.confidence) + 0.03), 2),
                    portion_multiplier=1.0,
                    source="general",
                    raw_label=hf_top.raw_label or local_top.raw_label or hf_top.label,
                    decision_reason="hf_local_agree",
                )
            ]

        if (
            local_top
            and local_top.label in self.local_priority_labels
            and local_top.confidence >= self.local_priority_threshold
        ):
            return [
                ClassificationResult(
                    label=local_top.label,
                    confidence=local_top.confidence,
                    portion_multiplier=1.0,
                    source="general_local",
                    raw_label=local_top.raw_label or local_top.label,
                    decision_reason="local_priority_label",
                )
            ]

        if hf_general_predictions:
            return hf_general_predictions
        return local_predictions

    def _build_consensus_prediction(
        self,
        chinese_predictions: list[ClassificationResult],
        general_predictions: list[ClassificationResult],
        local_predictions: list[ClassificationResult],
        hf_general_predictions: list[ClassificationResult],
    ) -> ClassificationResult | None:
        grouped: dict[str, dict] = {}

        for source_name, predictions, limit in (
            ("chinese", chinese_predictions, 3),
            ("general", general_predictions, 3),
            ("local", local_predictions, 1),
        ):
            for prediction in predictions[:limit]:
                bucket = grouped.setdefault(
                    prediction.label,
                    {
                        "sources": set(),
                        "combined_score": 0.0,
                        "best_score": 0.0,
                        "raw_label": prediction.raw_label or prediction.label,
                    },
                )
                bucket["sources"].add(source_name)
                bucket["combined_score"] += float(prediction.confidence)
                if float(prediction.confidence) >= float(bucket["best_score"]):
                    bucket["best_score"] = float(prediction.confidence)
                    bucket["raw_label"] = prediction.raw_label or prediction.label

        candidates = [
            (label, values)
            for label, values in grouped.items()
            if len(values["sources"]) >= 2 and float(values["combined_score"]) >= 0.72
        ]
        if not candidates:
            return None

        label, values = sorted(
            candidates,
            key=lambda item: (float(item[1]["combined_score"]), float(item[1]["best_score"])),
            reverse=True,
        )[0]

        confidence = min(
            0.99,
            max(
                float(values["best_score"]) + 0.08,
                float(values["combined_score"]) / max(1, len(values["sources"])) + 0.08,
            ),
        )
        return ClassificationResult(
            label=label,
            confidence=round(confidence, 2),
            portion_multiplier=1.0,
            source="hybrid_consensus",
            raw_label=str(values["raw_label"]),
            decision_reason="cross_model_consensus",
            alternatives=self._build_alternatives(
                chinese_predictions,
                hf_general_predictions,
                local_predictions,
            ),
        )

    @staticmethod
    def _build_alternatives(
        chinese_predictions: list[ClassificationResult],
        hf_general_predictions: list[ClassificationResult],
        local_predictions: list[ClassificationResult],
    ) -> list[dict]:
        alternatives: list[dict] = []
        for prediction in chinese_predictions[:3]:
            alternatives.append(
                {
                    "source": "chinese",
                    "label": prediction.label,
                    "raw_label": prediction.raw_label,
                    "confidence": prediction.confidence,
                }
            )
        for prediction in hf_general_predictions[:3]:
            alternatives.append(
                {
                    "source": prediction.source or "general_hf",
                    "label": prediction.label,
                    "raw_label": prediction.raw_label,
                    "confidence": prediction.confidence,
                }
            )
        for prediction in local_predictions[:1]:
            alternatives.append(
                {
                    "source": prediction.source or "general_local",
                    "label": prediction.label,
                    "raw_label": prediction.raw_label,
                    "confidence": prediction.confidence,
                }
            )
        return alternatives
