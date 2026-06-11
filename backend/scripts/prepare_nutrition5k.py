from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ml.datasets.nutrition5k_dataset import build_nutrition5k_metadata


def main() -> None:
    dataset_root = Path("dataset/nutrition5k")
    output_path = Path("app/data/nutrition5k_metadata.json")

    summary = build_nutrition5k_metadata(
        dataset_root=str(dataset_root),
        output_path=str(output_path),
        image_variant="realsense_overhead",
    )

    print(f"Prepared Nutrition5k metadata at {output_path}")
    print(summary)


if __name__ == "__main__":
    main()
