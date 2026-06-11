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


CHINESE_LABEL_TO_PROFILE_LABEL = {
    "Boiled chicken": "雞腿",
    "Braised Pork with Vermicelli": "control_butchers",
    "Braised pork": "control_butchers",
    "Cola Chicken wings": "炸雞",
    "Cucumber in Sauce": "salad",
    "Double cooked pork slices": "control_butchers",
    "Dumplings": "dumpling",
    "Fried Dumplings": "dumpling",
    "French fries": "french_fries",
    "Fried chicken drumsticks": "雞腿",
    "Kung Pao Chicken": "宮保雞丁",
    "Scrambled Egg with Leek": "fried_egg",
    "Scrambled Egg with cucumber": "fried_egg",
    "Scrambled egg with tomato": "番茄炒蛋",
    "Seaweed salad": "salad",
    "Soy sauce chicken": "醬油雞",
    "Steamed egg custard": "fried_egg",
    "Stewed Chicken with Three Cups Sauce": "三杯雞",
    "Sweet and sour spareribs": "control_butchers",
    "Tomato salad": "salad",
    "Yuba salad": "salad"
}


class ChineseFoodClassifier:
    def __init__(self, model_name: str, top_k: int = 3) -> None:
        self.model_name = model_name
        self.top_k = max(1, int(top_k))
        self.display_name = "Chinese Food Classifier"
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
            mapped_label = CHINESE_LABEL_TO_PROFILE_LABEL.get(raw_label) or NutritionService.resolve_lookup_label(raw_label)
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
                source="chinese",
                raw_label=values["raw_label"],
            )
            for label, values in sorted(
                aggregated.items(),
                key=lambda item: (item[1]["score"], item[1]["best_score"]),
                reverse=True,
            )
        ]
        return results[: self.top_k]

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
