from __future__ import annotations

from torch import nn


def build_regression_loss():
    return nn.SmoothL1Loss()
