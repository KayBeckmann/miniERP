"""Paperless-ngx REST-Adapter.

Verwendet den konfigurierten Token-Benutzer. Custom-Fields-Schreiben
schlägt lautlos fehl, falls der Benutzer keine Admin-Rechte hat.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def _headers() -> dict[str, str]:
    return {"Authorization": f"Token {settings.PAPERLESS_TOKEN}"}


async def upload_document(
    filename: str, content: bytes, mime_type: str = "application/pdf"
) -> int:
    """Lädt ein Dokument hoch und gibt die document_id zurück."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.PAPERLESS_URL}/api/documents/post_document/",
            headers=_headers(),
            files={"document": (filename, content, mime_type)},
        )
    response.raise_for_status()
    # Paperless gibt beim Async-Upload einen Task-Token zurück
    # oder bei kleineren Dateien direkt die document_id
    data = response.json()
    if isinstance(data, int):
        return data
    # Task-basierter Upload: task-id wird zurückgegeben
    return data  # type: ignore[return-value]


async def get_document(document_id: int) -> dict[str, Any]:
    """Holt Metadaten + OCR-Inhalt eines Dokuments."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.PAPERLESS_URL}/api/documents/{document_id}/",
            headers=_headers(),
        )
    response.raise_for_status()
    return response.json()


async def get_document_content(document_id: int) -> str:
    """Gibt den OCR-Text eines Dokuments zurück."""
    doc = await get_document(document_id)
    return doc.get("content", "")


async def set_custom_fields(document_id: int, fields: dict[str, str]) -> bool:
    """Setzt Custom Fields auf einem Dokument. Gibt False zurück wenn keine Rechte."""
    # Erst Custom Fields-IDs ermitteln
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            cf_resp = await client.get(
                f"{settings.PAPERLESS_URL}/api/custom_fields/",
                headers=_headers(),
            )
        if cf_resp.status_code != 200:
            return False

        existing: dict[str, int] = {
            cf["name"]: cf["id"]
            for cf in cf_resp.json().get("results", [])
        }

        custom_fields_payload = []
        for name, value in fields.items():
            if name in existing:
                custom_fields_payload.append({
                    "field": existing[name],
                    "value": value,
                })

        if not custom_fields_payload:
            return False

        async with httpx.AsyncClient(timeout=15.0) as client:
            patch_resp = await client.patch(
                f"{settings.PAPERLESS_URL}/api/documents/{document_id}/",
                headers={**_headers(), "Content-Type": "application/json"},
                json={"custom_fields": custom_fields_payload},
            )
        return patch_resp.status_code in (200, 204)
    except Exception:
        return False


async def find_document_by_task(task_id: str) -> int | None:
    """Sucht die document_id aus einem Paperless-Upload-Task."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.PAPERLESS_URL}/api/tasks/?task_id={task_id}",
            headers=_headers(),
        )
    if resp.status_code != 200:
        return None
    results = resp.json()
    if isinstance(results, list) and results:
        return results[0].get("related_document")
    return None
