from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app
from app.services.predictor import PredictorService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run fixed demo image validation against the current prediction pipeline."
    )
    parser.add_argument(
        "--manifest",
        default="test_cases/demo_cases.json",
        help="Path to the validation manifest JSON. Relative paths resolve from backend/.",
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Validation manifest not found: {manifest_path}\n"
            "Copy backend/test_cases/demo_cases.sample.json to demo_cases.json and fill in your test images."
        )

    with manifest_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Validation manifest must be a JSON array.")

    return data


def resolve_image_path(manifest_path: Path, image_path: str) -> Path:
    path = Path(image_path)
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def build_file_storage(image_path: Path) -> FileStorage:
    content_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    return FileStorage(
        stream=BytesIO(image_path.read_bytes()),
        filename=image_path.name,
        content_type=content_type,
    )


def matches_expected(result: dict[str, Any], expected_any_of: list[str]) -> tuple[bool, bool]:
    expected = [normalize_text(item) for item in expected_any_of if str(item).strip()]
    if not expected:
        return True, True

    items = result.get("items", [])
    first_item = items[0] if items else {}
    main_pool = [
        first_item.get("food_name", ""),
        first_item.get("raw_prediction_label", ""),
    ]
    candidate_pool = main_pool + [
        alternative.get("raw_label") or alternative.get("label") or ""
        for alternative in first_item.get("alternatives", [])
    ]

    normalized_main = [normalize_text(value) for value in main_pool if value]
    normalized_candidates = [normalize_text(value) for value in candidate_pool if value]

    main_match = any(
        any(expected_label in candidate or candidate in expected_label for candidate in normalized_main)
        for expected_label in expected
    )
    candidate_match = any(
        any(expected_label in candidate or candidate in expected_label for candidate in normalized_candidates)
        for expected_label in expected
    )

    return main_match, candidate_match


def run_case(predictor: PredictorService, manifest_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    image_path = resolve_image_path(manifest_path, case.get("image_path", ""))
    if not image_path.exists():
        return {
            "name": case.get("name") or image_path.name,
            "status": "missing",
            "message": f"Image not found: {image_path}",
        }

    result = predictor.predict(build_file_storage(image_path))
    main_match, candidate_match = matches_expected(result, case.get("expected_any_of", []))

    items = result.get("items", [])
    first_item = items[0] if items else {}
    status = "pass" if main_match else "candidate_only" if candidate_match else "fail"

    return {
        "name": case.get("name") or image_path.stem,
        "status": status,
        "image_path": str(image_path),
        "expected_any_of": case.get("expected_any_of", []),
        "food_name": first_item.get("food_name"),
        "raw_prediction_label": first_item.get("raw_prediction_label"),
        "confidence": first_item.get("confidence"),
        "prediction_source": first_item.get("prediction_source"),
        "total_calories": result.get("total_calories"),
    }


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (BACKEND_ROOT / manifest_path).resolve()

    manifest = load_manifest(manifest_path)
    app = create_app()
    predictor = PredictorService(app.config)

    results = [run_case(predictor, manifest_path, case) for case in manifest]
    pass_count = sum(1 for item in results if item["status"] == "pass")
    candidate_count = sum(1 for item in results if item["status"] == "candidate_only")
    fail_count = sum(1 for item in results if item["status"] == "fail")
    missing_count = sum(1 for item in results if item["status"] == "missing")

    print("Fixed Validation Summary")
    print(
        json.dumps(
            {
                "case_count": len(results),
                "pass_count": pass_count,
                "candidate_only_count": candidate_count,
                "fail_count": fail_count,
                "missing_count": missing_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    for item in results:
        print(
            json.dumps(
                item,
                ensure_ascii=False,
                indent=2,
            )
        )

    return 0 if fail_count == 0 and missing_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
