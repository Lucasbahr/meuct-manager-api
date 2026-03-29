import os
import uuid
from pathlib import Path

from fastapi import HTTPException

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_SIZE_BYTES = 5 * 1024 * 1024


def upload_root() -> Path:
    root = os.getenv("UPLOAD_DIR", "uploads")
    p = Path(root).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def abs_photo_path(relative: str) -> Path:
    return upload_root() / relative.replace("\\", "/")


def save_student_photo(student_id: int, content: bytes, content_type: str) -> str:
    ctype = (content_type or "").lower().split(";")[0].strip()
    if ctype not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido. Use JPEG, PNG ou WebP.",
        )
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Arquivo muito grande (máximo 5MB).",
        )
    ext = ALLOWED_TYPES[ctype]
    relative = f"students/{student_id}/{uuid.uuid4().hex}{ext}"
    dest = abs_photo_path(relative)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return relative


def delete_student_photo(relative: str | None) -> None:
    if not relative:
        return
    path = abs_photo_path(relative)
    if path.is_file():
        path.unlink()
