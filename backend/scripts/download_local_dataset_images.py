from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_DOWNLOAD_BYTES = 4_000_000
MAX_IMAGE_SIDE = 1024
USER_AGENT = "ai-food-journal-test"


PATH_TERMS = {
    "chocolate_cake/cake": ["chocolate cake food"],
    "rice/control_butchers": ["braised pork rice food", "lu rou fan rice"],
}


EXTRA_SUBCATEGORIES = {
    "dumpling": ["水餃", "煎餃", "小籠包"],
    "fried_rice": ["蛋炒飯", "蝦仁炒飯", "火腿炒飯"],
    "hot_dog": ["原味熱狗", "起司熱狗", "辣味熱狗"],
    "三杯雞": ["家常三杯雞", "三杯雞便當", "三杯雞套餐"],
    "炸雞": ["炸雞翅", "炸雞腿", "雞塊"],
    "宮保雞丁": ["宮保雞丁", "宮保雞丁飯", "宮保雞丁便當"],
    "醬油雞": ["醬油雞", "醬油雞飯", "醬油雞腿"],
    "雞腿": ["烤雞腿", "滷雞腿", "香煎雞腿"],
}


NAME_TERMS = {
    "\u6392\u9aa8\u4fbf\u7576": ["pork chop bento", "pork cutlet bento"],
    "\u9b5a\u4fbf\u7576": ["fish bento", "fish lunch box"],
    "\u7112\u8089\u4fbf\u7576": ["braised pork bento", "pork belly bento"],
    "\u96de\u817f\u4fbf\u7576": ["chicken leg bento", "chicken drumstick bento"],
    "\u9bd6\u9b5a\u4fbf\u7576": ["mackerel bento", "grilled mackerel bento"],
    "\u5de7\u514b\u529b\u86cb\u7cd5": ["chocolate cake food"],
    "\u4e73\u916a\u86cb\u7cd5": ["cheesecake food"],
    "\u62b9\u8336\u86cb\u7cd5": ["matcha cake food"],
    "\u8349\u8393\u86cb\u7cd5": ["strawberry cake food"],
    "\u9bae\u5976\u6cb9\u86cb\u7cd5": ["cream cake food"],
    "\u5e03\u4e01": ["pudding dessert"],
    "\u51b0\u6dc7\u6dcb": ["ice cream dessert"],
    "\u751c\u751c\u5708": ["donut food", "doughnut food"],
    "\u9b06\u9905": ["waffle food"],
    "\u67f3\u6a59\u6c41": ["orange juice drink"],
    "\u73cd\u73e0\u5976\u8336": ["bubble tea drink", "boba milk tea"],
    "\u7d05\u8336\u62ff\u9435": ["black tea latte", "milk tea latte"],
    "\u7f8e\u5f0f\u5496\u5561": ["americano coffee", "black coffee"],
    "\u539f\u5473\u85af\u689d": ["french fries food"],
    "\u8d77\u53f8\u85af\u689d": ["cheese fries food"],
    "\u6372\u6372\u85af\u689d": ["curly fries food"],
    "\u534a\u719f\u86cb": ["soft boiled egg food"],
    "\u8377\u5305\u86cb": ["fried egg food"],
    "\u756a\u8304\u7092\u86cb": ["tomato scrambled eggs"],
    "\u96d9\u86cb": ["two fried eggs food"],
    "\u725b\u8089\u6f22\u5821": ["beef hamburger food"],
    "\u8d77\u53f8\u6f22\u5821": ["cheeseburger food"],
    "\u96de\u817f\u6f22\u5821": ["chicken burger food"],
    "\u725b\u8089\u9eb5": ["beef noodle soup"],
    "\u70cf\u9f8d\u9eb5": ["udon noodles food"],
    "\u4e7e\u9eb5": ["dry noodles food"],
    "\u7fa9\u5927\u5229\u9eb5": ["spaghetti pasta food"],
    "\u590f\u5a01\u5937\u62ab\u85a9": ["hawaiian pizza food"],
    "\u6d77\u9bae\u62ab\u85a9": ["seafood pizza food"],
    "\u746a\u683c\u9e97\u7279\u62ab\u85a9": ["margherita pizza food"],
    "\u5473\u564c\u62c9\u9eb5": ["miso ramen"],
    "\u8c5a\u9aa8\u62c9\u9eb5": ["tonkotsu ramen"],
    "\u91ac\u6cb9\u62c9\u9eb5": ["shoyu ramen"],
    "\u725b\u8089\u71f4\u98ef": ["beef rice bowl food"],
    "\u767d\u98ef": ["steamed white rice bowl"],
    "\u5496\u54e9\u98ef": ["curry rice food"],
    "\u7092\u98ef": ["fried rice food"],
    "\u6392\u9aa8\u98ef": ["pork chop rice food"],
    "\u6ef7\u8089\u98ef": ["lu rou fan food", "braised pork rice"],
    "\u96de\u8089\u98ef": ["chicken rice food"],
    "\u548c\u98a8\u6c99\u62c9": ["japanese salad food"],
    "\u51f1\u85a9\u6c99\u62c9": ["caesar salad food"],
    "\u96de\u80f8\u6c99\u62c9": ["chicken breast salad"],
    "\u706b\u817f\u4e09\u660e\u6cbb": ["ham sandwich food"],
    "\u86cb\u6c99\u62c9\u4e09\u660e\u6cbb": ["egg salad sandwich"],
    "\u9baa\u9b5a\u4e09\u660e\u6cbb": ["tuna sandwich food"],
    "\u808b\u773c\u725b\u6392": ["ribeye steak food"],
    "\u6c99\u6717\u725b\u6392": ["sirloin steak food"],
    "\u83f2\u529b\u725b\u6392": ["filet mignon steak"],
    "\u7389\u5b50\u58fd\u53f8": ["tamago sushi"],
    "\u9baa\u9b5a\u58fd\u53f8": ["tuna sushi"],
    "\u9bad\u9b5a\u58fd\u53f8": ["salmon sushi"],
    "\u4e09\u676f\u96de": ["three cup chicken food"],
    "\u5bae\u4fdd\u96de\u4e01": ["kung pao chicken food"],
    "\u70b8\u96de": ["fried chicken food"],
    "\u91ac\u6cb9\u96de": ["soy sauce chicken food"],
    "\u96de\u817f": ["chicken drumstick food", "chicken leg food"],
    "\u6c34\u9903": ["boiled dumplings food", "chinese dumplings food"],
    "\u714e\u9903": ["pan fried dumplings food", "potstickers food"],
    "\u5c0f\u7c60\u5305": ["xiao long bao food", "soup dumplings food"],
    "\u86cb\u7092\u98ef": ["egg fried rice food"],
    "\u8766\u4ec1\u7092\u98ef": ["shrimp fried rice food"],
    "\u706b\u817f\u7092\u98ef": ["ham fried rice food"],
    "\u539f\u5473\u71b1\u72d7": ["hot dog food"],
    "\u8d77\u53f8\u71b1\u72d7": ["cheese hot dog food"],
    "\u8fa3\u5473\u71b1\u72d7": ["spicy hot dog food"],
    "\u5bb6\u5e38\u4e09\u676f\u96de": ["three cup chicken food"],
    "\u4e09\u676f\u96de\u4fbf\u7576": ["three cup chicken bento"],
    "\u4e09\u676f\u96de\u5957\u9910": ["three cup chicken meal"],
    "\u70b8\u96de\u7fc5": ["fried chicken wings food"],
    "\u70b8\u96de\u817f": ["fried chicken drumstick food"],
    "\u96de\u584a": ["chicken nuggets food", "fried chicken pieces"],
    "\u5bae\u4fdd\u96de\u4e01\u98ef": ["kung pao chicken rice"],
    "\u5bae\u4fdd\u96de\u4e01\u4fbf\u7576": ["kung pao chicken bento"],
    "\u91ac\u6cb9\u96de\u98ef": ["soy sauce chicken rice"],
    "\u91ac\u6cb9\u96de\u817f": ["soy sauce chicken drumstick"],
    "\u70e4\u96de\u817f": ["roast chicken leg food", "grilled chicken drumstick"],
    "\u6ef7\u96de\u817f": ["braised chicken leg food"],
    "\u9999\u714e\u96de\u817f": ["pan fried chicken leg food"],
}


@dataclass
class Candidate:
    url: str
    provider: str
    title: str
    page_url: str = ""


def request_json(url: str, params: dict[str, str | int]) -> dict:
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def commons_candidates(term: str, limit: int) -> Iterable[Candidate]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{term} filetype:bitmap",
        "gsrnamespace": 6,
        "gsrlimit": min(50, limit),
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": 900,
    }
    try:
        data = request_json("https://commons.wikimedia.org/w/api.php", params)
    except Exception:
        return []

    pages = data.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime", ""))
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        url = str(info.get("thumburl") or info.get("url") or "")
        if not url:
            continue
        title = str(page.get("title", term))
        page_title = urllib.parse.quote(title.replace(" ", "_"))
        results.append(
            Candidate(
                url=url,
                provider="wikimedia_commons",
                title=title,
                page_url=f"https://commons.wikimedia.org/wiki/{page_title}",
            )
        )
    return results


def openverse_candidates(term: str, limit: int) -> Iterable[Candidate]:
    results = []
    seen_urls: set[str] = set()
    page_size = 50
    max_pages = max(1, min(6, (limit + page_size - 1) // page_size + 2))
    for page in range(1, max_pages + 1):
        params = {
            "q": term,
            "page": page,
            "page_size": page_size,
            "mature": "false",
        }
        try:
            data = request_json("https://api.openverse.engineering/v1/images/", params)
        except Exception:
            continue

        for item in data.get("results", []):
            title = str(item.get("title") or term)
            page_url = str(item.get("foreign_landing_url") or "")
            mime = str(item.get("mime_type") or "")
            candidate_urls = [
                str(item.get("thumbnail") or ""),
                str(item.get("url") or ""),
            ]
            for url in candidate_urls:
                if not url or url in seen_urls:
                    continue
                guessed_mime = mime or str(mimetypes.guess_type(url)[0] or "")
                if guessed_mime and guessed_mime not in {"image/jpeg", "image/png", "image/webp"}:
                    continue
                seen_urls.add(url)
                results.append(
                    Candidate(
                        url=url,
                        provider="openverse",
                        title=title,
                        page_url=page_url,
                    )
                )
            if len(results) >= limit:
                return results
        if not data.get("results"):
            break
        time.sleep(0.2)
    return results


def download_bytes(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if content_type and not content_type.startswith("image/"):
                return None
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if len(data) > MAX_DOWNLOAD_BYTES:
        return None
    return data


def normalize_image(data: bytes) -> tuple[bytes, str] | None:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                background = Image.new("RGB", image.size, "white")
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")
            else:
                image = image.convert("RGB")
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            output = BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            normalized = output.getvalue()
    except Exception:
        return None
    digest = hashlib.sha256(normalized).hexdigest()
    return normalized, digest


def current_images(folder: Path) -> list[Path]:
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]


def existing_hashes(folder: Path) -> set[str]:
    hashes = set()
    for path in current_images(folder):
        try:
            hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            pass
    return hashes


def leaf_folders(root: Path) -> list[Path]:
    folders = []
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        relative_parts = path.relative_to(root).parts
        if "nutrition5k" in relative_parts:
            continue
        if not any(child.is_dir() for child in path.iterdir()):
            folders.append(path)
    return sorted(folders, key=lambda item: item.as_posix())


def ensure_extra_subcategories(root: Path) -> None:
    for parent, children in EXTRA_SUBCATEGORIES.items():
        parent_dir = root / parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        for child in children:
            (parent_dir / child).mkdir(parents=True, exist_ok=True)


def terms_for_folder(root: Path, folder: Path) -> list[str]:
    relative = folder.relative_to(root).as_posix()
    if relative in PATH_TERMS:
        return PATH_TERMS[relative]
    name = folder.name
    if name in NAME_TERMS:
        return NAME_TERMS[name]
    normalized = name.replace("_", " ").replace("-", " ")
    parent = folder.parent.name.replace("_", " ").replace("-", " ")
    terms = [f"{normalized} food"]
    if parent and parent != root.name and parent.lower() not in normalized.lower():
        terms.append(f"{normalized} {parent} food")
    return terms


def safe_slug(folder: Path) -> str:
    slug = folder.name.encode("ascii", "ignore").decode("ascii").lower()
    slug = "".join(char if char.isalnum() else "_" for char in slug).strip("_")
    return slug or hashlib.sha1(folder.name.encode("utf-8")).hexdigest()[:10]


def save_manifest_row(manifest: Path, row: dict[str, str]) -> None:
    exists = manifest.exists()
    with manifest.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "downloaded_at",
                "folder",
                "file",
                "provider",
                "title",
                "source_url",
                "page_url",
                "sha256",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def fill_folder(root: Path, folder: Path, target_count: int, manifest: Path) -> tuple[int, int]:
    existing = current_images(folder)
    needed = max(0, target_count - len(existing))
    if needed == 0:
        return len(existing), 0

    hashes = existing_hashes(folder)
    added = 0
    seen_urls: set[str] = set()
    slug = safe_slug(folder)
    terms = terms_for_folder(root, folder)
    providers = (commons_candidates, openverse_candidates)

    for term in terms:
        for provider in providers:
            candidates = provider(term, max(60, needed * 4))
            for candidate in candidates:
                if candidate.url in seen_urls:
                    continue
                seen_urls.add(candidate.url)
                data = download_bytes(candidate.url)
                if not data:
                    continue
                normalized = normalize_image(data)
                if normalized is None:
                    continue
                image_bytes, digest = normalized
                if digest in hashes:
                    continue
                index = len(current_images(folder)) + 1
                output = folder / f"web_{slug}_{index:03d}.jpg"
                try:
                    output.write_bytes(image_bytes)
                except OSError:
                    continue
                hashes.add(digest)
                added += 1
                save_manifest_row(
                    manifest,
                    {
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "folder": folder.relative_to(root).as_posix(),
                        "file": output.name,
                        "provider": candidate.provider,
                        "title": candidate.title,
                        "source_url": candidate.url,
                        "page_url": candidate.page_url,
                        "sha256": digest,
                    },
                )
                if len(current_images(folder)) >= target_count:
                    return len(current_images(folder)), added
                time.sleep(0.1)
    return len(current_images(folder)), added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[2] / "local_assets" / "backend" / "dataset"),
    )
    parser.add_argument("--target", type=int, default=20)
    parser.add_argument("--only", default="", help="Only folders containing this text.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest = root / "downloaded_image_sources.csv"
    ensure_extra_subcategories(root)
    folders = leaf_folders(root)
    if args.only:
        folders = [folder for folder in folders if args.only in folder.relative_to(root).as_posix()]

    summary = []
    for folder in folders:
        before = len(current_images(folder))
        count, added = fill_folder(root, folder, args.target, manifest)
        relative = folder.relative_to(root).as_posix()
        summary.append({"folder": relative, "before": before, "after": count, "added": added})
        print(f"{relative}: {before} -> {count} (+{added})", flush=True)

    missing = [row for row in summary if row["after"] < args.target]
    print(json.dumps({"folders": len(summary), "missing": missing}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
