"""
Estrutura de armazenamento por academia (tenant) no bucket compartilhado.

- Prefixo lógico alinhado a ``tenant_storage_segment`` em ``student_photo``.
- Ao criar um gym, marcadores podem ser gravados para fixar pastas no GCS/disco.
"""

from __future__ import annotations

import os
from typing import List

from app.services.student_photo import local_upload_root, tenant_storage_segment


def should_provision_on_gym_create() -> bool:
    return os.getenv("GCS_PROVISION_TENANT_ON_CREATE", "").lower() in (
        "1",
        "true",
        "yes",
    )


def _marker_keys_for_gym(gym_id: int) -> List[str]:
    base = tenant_storage_segment(gym_id)
    if not base:
        return []
    return [
        f"{base}/students/.keep",
        f"{base}/feed_items/.keep",
        f"{base}/marketplace/.keep",
    ]


def provision_tenant_storage(gym_id: int) -> None:
    """
    Cria a hierarquia inicial do tenant (marcadores). Em modo local, cria diretórios.
    Em GCS, grava blobs vazios.
    """
    if not should_provision_on_gym_create():
        return

    keys = _marker_keys_for_gym(gym_id)
    if not keys:
        return

    provider = (os.getenv("STORAGE_PROVIDER") or "local").lower()
    if provider == "gcs":
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not bucket_name:
            return
        from google.cloud import storage  # type: ignore

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        for key in keys:
            blob = bucket.blob(key)
            if not blob.exists():
                blob.upload_from_string(b"", content_type="application/octet-stream")
        return

    root = local_upload_root()
    for key in keys:
        path = root / key.replace("\\", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b"")
