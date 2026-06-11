from __future__ import annotations

from io import BytesIO
from pathlib import Path

import torch
from PIL import Image

from app.ml.models.mobilenet_regressor import MobileNetRegressor
from app.ml.training.transforms import build_eval_transform


class MobileNetRegressionInference:
    def __init__(self, model_path: str) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_absolute():
            self.model_path = Path(__file__).resolve().parents[3] / model_path
        if not self.model_path.exists():
            raise FileNotFoundError(f"Regression model not found: {self.model_path}")

        checkpoint = torch.load(self.model_path, map_location="cpu")
        self.model = MobileNetRegressor(pretrained=False)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        self.transform = build_eval_transform()
        self.model_name = checkpoint.get("model_name", "MobileNet Regression")

    def predict_nutrition(self, image_bytes: bytes) -> dict[str, float]:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            tensor = self.transform(image).unsqueeze(0)

        with torch.no_grad():
            output = self.model(tensor)
            if isinstance(output, dict):
                output = output["nutrition"]
            output = output[0]

        return {
            "calories": max(0.0, round(float(output[0].item()), 1)),
            "protein": max(0.0, round(float(output[1].item()), 1)),
            "fat": max(0.0, round(float(output[2].item()), 1)),
            "carbs": max(0.0, round(float(output[3].item()), 1)),
        }
