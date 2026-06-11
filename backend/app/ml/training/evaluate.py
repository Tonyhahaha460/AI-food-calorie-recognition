from __future__ import annotations

import torch


def compute_regression_metrics(predictions: torch.Tensor, targets: torch.Tensor) -> dict[str, float]:
    mae = torch.mean(torch.abs(predictions - targets), dim=0)
    rmse = torch.sqrt(torch.mean((predictions - targets) ** 2, dim=0))

    return {
        "calories_mae": float(mae[0].item()),
        "protein_mae": float(mae[1].item()),
        "fat_mae": float(mae[2].item()),
        "carbs_mae": float(mae[3].item()),
        "calories_rmse": float(rmse[0].item()),
        "protein_rmse": float(rmse[1].item()),
        "fat_rmse": float(rmse[2].item()),
        "carbs_rmse": float(rmse[3].item()),
    }


def compute_classification_metrics(logits: torch.Tensor, targets: torch.Tensor) -> dict[str, float]:
    predicted = torch.argmax(logits, dim=1)
    accuracy = torch.mean((predicted == targets).float())
    return {"top1_accuracy": float(accuracy.item())}
