from __future__ import annotations

from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


class MobileNetRegressor(nn.Module):
    def __init__(self, pretrained: bool = True, output_dim: int = 4, num_classes: int = 1) -> None:
        super().__init__()
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        try:
            backbone = mobilenet_v3_small(weights=weights)
        except Exception:
            backbone = mobilenet_v3_small(weights=None)

        self.features = backbone.features
        self.avgpool = backbone.avgpool
        hidden_dim = backbone.classifier[0].in_features
        self.regressor = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.Hardswish(),
            nn.Linear(128, output_dim),
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def freeze_backbone(self) -> None:
        for parameter in self.features.parameters():
            parameter.requires_grad = False

    def unfreeze_backbone(self) -> None:
        for parameter in self.features.parameters():
            parameter.requires_grad = True

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = x.flatten(1)
        return {
            "nutrition": self.regressor(x),
            "logits": self.classifier(x),
        }
