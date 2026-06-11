from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.services.classifier import ClassificationResult
from app.services.nutrition_service import NutritionService


GENERAL_LABEL_TO_PROFILE_LABEL = {
    "club_sandwich": "sandwich",
    "donut": NutritionService.resolve_lookup_label("donut") or "",
    "donuts": NutritionService.resolve_lookup_label("donuts") or "",
    "french_fries": "french_fries",
    "fried_chicken": NutritionService.resolve_lookup_label("fried_chicken") or "",
    "fried_rice": NutritionService.resolve_lookup_label("fried_rice") or "",
    "grilled_cheese_sandwich": "sandwich",
    "ice_cream": NutritionService.resolve_lookup_label("ice_cream") or "",
    "lobster_roll_sandwich": "sandwich",
    "omelet": "fried_egg",
    "omelette": "fried_egg",
    "spaghetti_bolognese": NutritionService.resolve_lookup_label("spaghetti_bolognese") or "",
    "spaghetti_carbonara": NutritionService.resolve_lookup_label("spaghetti_carbonara") or "",
    "waffle": NutritionService.resolve_lookup_label("waffle") or "",
    "waffles": NutritionService.resolve_lookup_label("waffles") or "",
}


class HuggingFaceFoodClassifier:
    def __init__(self, model_name: str, top_k: int = 3) -> None:
        self.model_name = model_name
        self.top_k = max(1, int(top_k))
        self.display_name = "HuggingFace Food Classifier"
        resolved_model_path = self._resolve_model_source(model_name)

        self._processor = self._load_processor(resolved_model_path)
        self._model = self._load_model(resolved_model_path)
        self._model.eval()

    def predict(self, image_bytes: bytes) -> list[ClassificationResult]:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            inputs = self._processor(images=image, return_tensors="pt")

        with torch.no_grad():
            logits = self._model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1)[0]
            topk = torch.topk(probabilities, k=min(self.top_k, probabilities.shape[-1]))

        aggregated: dict[str, dict] = {}
        for score, idx in zip(topk.values.tolist(), topk.indices.tolist()):
            raw_label = str(self._model.config.id2label[int(idx)]).strip()
            mapped_label = self._map_label(raw_label)
            if not mapped_label:
                continue

            bucket = aggregated.setdefault(
                mapped_label,
                {
                    "score": 0.0,
                    "best_score": 0.0,
                    "raw_label": raw_label,
                },
            )
            bucket["score"] += float(score)
            if float(score) >= bucket["best_score"]:
                bucket["best_score"] = float(score)
                bucket["raw_label"] = raw_label

        results = [
            ClassificationResult(
                label=label,
                confidence=round(min(0.99, values["score"]), 4),
                portion_multiplier=1.0,
                source="general_hf",
                raw_label=values["raw_label"],
            )
            for label, values in sorted(
                aggregated.items(),
                key=lambda item: (item[1]["score"], item[1]["best_score"]),
                reverse=True,
            )
        ]
        return results[: self.top_k]

    @classmethod
    def _map_label(cls, raw_label: str) -> str | None:
        normalized = NutritionService.normalize_label_key(raw_label)
        mapped = GENERAL_LABEL_TO_PROFILE_LABEL.get(normalized)
        if mapped:
            return mapped
        return NutritionService.resolve_lookup_label(raw_label)

    @staticmethod
    def _load_processor(model_name: str):
        try:
            return AutoImageProcessor.from_pretrained(model_name, local_files_only=True)
        except OSError:
            return AutoImageProcessor.from_pretrained(model_name)

    @staticmethod
    def _load_model(model_name: str):
        try:
            return AutoModelForImageClassification.from_pretrained(model_name, local_files_only=True)
        except OSError:
            return AutoModelForImageClassification.from_pretrained(model_name)

    @staticmethod
    def _resolve_model_source(model_name: str) -> str:
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
