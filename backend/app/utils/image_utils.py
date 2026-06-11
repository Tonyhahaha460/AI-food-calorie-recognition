from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def normalize_image_bytes(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((512, 512))

        output = BytesIO()
        image.save(output, format="JPEG", quality=90)
        return output.getvalue()
