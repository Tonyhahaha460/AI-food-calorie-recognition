from __future__ import annotations

from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


class MobileNetClassifier(nn.Module):
    def __init__(self, num_classes: int, pretrained: bool = True) -> None:
        super().__init__()
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        try:
            self.model = mobilenet_v3_small(weights=weights)
        except Exception:
            self.model = mobilenet_v3_small(weights=None)

        in_features = self.model.classifier[3].in_features
        self.model.classifier[3] = nn.Linear(in_features, num_classes)

    def freeze_features(self) -> None:
        for parameter in self.model.features.parameters():
            parameter.requires_grad = False

    def unfreeze_all(self) -> None:
        for parameter in self.model.parameters():
            parameter.requires_grad = True

    def forward(self, x):
        return self.model(x)
