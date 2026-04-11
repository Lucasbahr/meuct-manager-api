import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_SIZE_BYTES = 5 * 1024 * 1024


def _storage_provider() -> str:
    # Keep backward compatibility for local/dev runs.
    return (os.getenv("STORAGE_PROVIDER") or "local").lower()


def _gcs_bucket_name() -> Optional[str]:
    return os.getenv("GCS_BUCKET_NAME")


def _upload_root() -> Path:
    root = os.getenv("UPLOAD_DIR", "uploads")
    p = Path(root).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def local_upload_root() -> Path:
    """Raiz local de uploads (também usada quando STORAGE_PROVIDER=local)."""
    return _upload_root()


def abs_photo_path(relative: str) -> Path:
    # Local-only path. In GCS mode we still keep this for tests/compat.
    return _upload_root() / relative.replace("\\", "/")


def _build_object_key(prefix: str, ext: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


def tenant_storage_segment(gym_id: int) -> str:
    """
    Prefixo por academia dentro do bucket (ou disco local).
    ``GCS_TENANT_PREFIX`` vazio desativa o segmento (somente legado / migração).
    """
    root = (os.getenv("GCS_TENANT_PREFIX") or "tenants").strip().strip("/")
    if not root:
        return ""
    return f"{root}/{int(gym_id)}"


def _validate_image(content: bytes, content_type: str) -> Tuple[str, str]:
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
    return ctype, ALLOWED_TYPES[ctype]


def _upload_to_gcs(object_key: str, content: bytes, content_type: str) -> None:
    bucket_name = _gcs_bucket_name()
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME não definido")

    # Lazy import so tests that run in local mode do not require GCS deps.
    from google.cloud import storage  # type: ignore

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    blob.upload_from_string(content, content_type=content_type)


def _download_from_gcs(object_key: str) -> bytes:
    bucket_name = _gcs_bucket_name()
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME não definido")

    from google.cloud import storage  # type: ignore

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    if not blob.exists():
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return blob.download_as_bytes()


def _delete_from_gcs(object_key: str) -> None:
    bucket_name = _gcs_bucket_name()
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME não definido")

    from google.cloud import storage  # type: ignore

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    try:
        blob.delete()
    except Exception:
        # Deleting a non-existing object should not break the API.
        pass


def save_photo(prefix: str, content: bytes, content_type: str) -> str:
    ctype, ext = _validate_image(content, content_type)
    object_key = _build_object_key(prefix=prefix, ext=ext)

    if _storage_provider() == "gcs":
        _upload_to_gcs(object_key, content=content, content_type=ctype)
        return object_key

    dest = abs_photo_path(object_key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return object_key


def get_photo_bytes(relative: str) -> Tuple[bytes, str]:
    if _storage_provider() == "gcs":
        data = _download_from_gcs(relative)
    else:
        path = abs_photo_path(relative)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Foto não encontrada")
        data = path.read_bytes()

    media_type, _ = mimetypes.guess_type(relative)
    return data, media_type or "application/octet-stream"


def delete_student_photo(relative: str | None) -> None:
    if not relative:
        return

    if _storage_provider() == "gcs":
        _delete_from_gcs(relative)
        return

    path = abs_photo_path(relative)
    if path.is_file():
        path.unlink()


def save_student_photo(
    gym_id: int, student_id: int, content: bytes, content_type: str
) -> str:
    seg = tenant_storage_segment(gym_id)
    inner = f"students/{student_id}"
    prefix = f"{seg}/{inner}" if seg else inner
    return save_photo(prefix=prefix, content=content, content_type=content_type)


def save_student_athlete_card_photo(
    gym_id: int, student_id: int, content: bytes, content_type: str
) -> str:
    seg = tenant_storage_segment(gym_id)
    inner = f"students/{student_id}/athlete_card"
    prefix = f"{seg}/{inner}" if seg else inner
    return save_photo(prefix=prefix, content=content, content_type=content_type)


def save_feed_photo(
    gym_id: int, feed_item_id: int, content: bytes, content_type: str
) -> str:
    seg = tenant_storage_segment(gym_id)
    inner = f"feed_items/{feed_item_id}"
    prefix = f"{seg}/{inner}" if seg else inner
    return save_photo(prefix=prefix, content=content, content_type=content_type)


def delete_feed_photo(relative: str | None) -> None:
    delete_student_photo(relative)
