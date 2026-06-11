from __future__ import annotations

import argparse
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATASET = PROJECT_ROOT / "local_assets" / "backend" / "dataset"
SPLIT_DATASET = PROJECT_ROOT / "local_assets" / "backend" / "training_sets" / "downloaded_food_yolo_cls"
SOURCE_MODEL = (
    PROJECT_ROOT
    / "backend"
    / "runs"
    / "all_food_cls"
    / "uec_food101_yolov8n_cls-3"
    / "weights"
    / "best.pt"
)
RUNS_PROJECT = PROJECT_ROOT / "backend" / "runs" / "downloaded_food_cls"
RUN_NAME = "downloaded_web_images_yolov8n_cls"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
IGNORED_DIR_NAMES = {"nutrition5k", "training_sets", "downloaded_food_yolo_cls"}


@dataclass(frozen=True)
class ClassImages:
    label: str
    files: list[Path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare downloaded local food images and train a YOLOv8 classification model."
    )
    parser.add_argument("--source", type=Path, default=SOURCE_DATASET, help="Root folder containing category folders.")
    parser.add_argument("--split", type=Path, default=SPLIT_DATASET, help="Generated YOLO classification split folder.")
    parser.add_argument("--model", type=Path, default=SOURCE_MODEL, help="Starting classification model.")
    parser.add_argument("--project", type=Path, default=RUNS_PROJECT, help="YOLO runs output folder.")
    parser.add_argument("--name", default=RUN_NAME, help="YOLO run name.")
    parser.add_argument("--epochs", type=int, default=30, help="Training epochs.")
    parser.add_argument("--imgsz", type=int, default=320, help="Training image size.")
    parser.add_argument("--batch", type=int, default=8, help="Batch size.")
    parser.add_argument("--min-images", type=int, default=2, help="Minimum images required per class.")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed.")
    parser.add_argument(
        "--all-images",
        action="store_true",
        help="Use all image names. By default only safely downloaded web_*.jpg images are used.",
    )
    return parser.parse_args()


def is_inside_ignored_dir(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def is_valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def label_from_folder(source_root: Path, image_path: Path) -> str:
    relative_parent = image_path.parent.relative_to(source_root)
    return "__".join(relative_parent.parts)


def collect_class_images(source_root: Path, use_all_images: bool, min_images: int) -> list[ClassImages]:
    grouped: dict[str, list[Path]] = {}
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if is_inside_ignored_dir(path.relative_to(source_root)):
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not use_all_images and not path.name.lower().startswith("web_"):
            continue
        if not is_valid_image(path):
            print(f"skip invalid image: {path}")
            continue
        label = label_from_folder(source_root, path)
        grouped.setdefault(label, []).append(path)

    classes = [
        ClassImages(label=label, files=sorted(files))
        for label, files in sorted(grouped.items())
        if len(files) >= min_images
    ]
    return classes


def recreate_split_root(split_root: Path) -> None:
    if split_root.exists():
        shutil.rmtree(split_root)
    (split_root / "train").mkdir(parents=True, exist_ok=True)
    (split_root / "val").mkdir(parents=True, exist_ok=True)


def copy_split(classes: list[ClassImages], split_root: Path, val_ratio: float, seed: int) -> tuple[int, int]:
    rng = random.Random(seed)
    train_total = 0
    val_total = 0
    for class_images in classes:
        files = list(class_images.files)
        rng.shuffle(files)
        val_count = max(1, round(len(files) * val_ratio))
        val_count = min(val_count, len(files) - 1)
        val_files = files[:val_count]
        train_files = files[val_count:]

        for split_name, split_files in (("train", train_files), ("val", val_files)):
            class_dir = split_root / split_name / class_images.label
            class_dir.mkdir(parents=True, exist_ok=True)
            for index, source_file in enumerate(split_files, start=1):
                target = class_dir / f"{class_images.label}_{index:04d}{source_file.suffix.lower()}"
                shutil.copy2(source_file, target)

        train_total += len(train_files)
        val_total += len(val_files)
    return train_total, val_total


def write_summary(split_root: Path, classes: list[ClassImages], train_total: int, val_total: int) -> None:
    lines = [
        "label,image_count",
        *[f"{item.label},{len(item.files)}" for item in classes],
        "",
        f"train_total,{train_total}",
        f"val_total,{val_total}",
    ]
    (split_root / "class_counts.csv").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_root = args.source.resolve()
    split_root = args.split.resolve()
    model_path = args.model.resolve()
    project_path = args.project.resolve()

    if not source_root.exists():
        raise FileNotFoundError(f"Source dataset does not exist: {source_root}")
    if not model_path.exists():
        raise FileNotFoundError(f"Starting model does not exist: {model_path}")

    classes = collect_class_images(source_root, args.all_images, args.min_images)
    if not classes:
        raise RuntimeError(
            f"No classes have at least {args.min_images} usable images. "
            "Download more images or lower --min-images."
        )

    recreate_split_root(split_root)
    train_total, val_total = copy_split(classes, split_root, args.val_ratio, args.seed)
    write_summary(split_root, classes, train_total, val_total)

    print(f"Prepared dataset: {split_root}")
    print(f"Classes used: {len(classes)}")
    print(f"Train images: {train_total}")
    print(f"Val images: {val_total}")
    print(f"Starting model: {model_path}")

    model = YOLO(str(model_path))
    results = model.train(
        data=str(split_root),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(project_path),
        name=args.name,
        exist_ok=False,
        device=0,
        workers=0,
        amp=False,
        plots=False,
    )

    metrics = model.val(data=str(split_root), imgsz=args.imgsz, batch=args.batch, device=0, workers=0, plots=False)
    print(f"Top-1 Accuracy: {metrics.top1:.4f}")
    print(f"Top-5 Accuracy: {metrics.top5:.4f}")
    print(f"Training run: {results.save_dir}")
    print(f"Best model: {Path(results.save_dir) / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
