from __future__ import annotations

import os
from typing import Any

import httpx

from app.services.cloud_storage import StorageError, StorageNotConfigured, build_object_storage


class CloudDocumentError(RuntimeError):
    pass


class CloudDocumentService:
    def __init__(self, *, project_url: str, api_key: str, access_token: str) -> None:
        if not all([project_url, api_key, access_token]):
            raise StorageNotConfigured("Supabase Data API configuration is incomplete.")
        self.base_url = project_url.rstrip("/")
        self.api_key = api_key
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def list_documents(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.base_url}/rest/v1/doka_documents",
            headers={**self._headers(), "Accept": "application/json"},
            params={"select": "*", "order": "created_at.desc", "limit": limit, "offset": offset},
            timeout=15.0,
        )
        if response.status_code >= 300:
            raise CloudDocumentError(f"Document listing failed ({response.status_code}).")
        return response.json()

    def create_document(self, *, owner_id: str, object_key: str, filename: str, content_type: str, size_bytes: int, sha256: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "owner_id": owner_id,
            "object_key": object_key,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "status": "active",
            "metadata": metadata or {},
        }
        response = httpx.post(
            f"{self.base_url}/rest/v1/doka_documents",
            headers={**self._headers(), "Prefer": "return=representation"},
            json=payload,
            timeout=15.0,
        )
        if response.status_code >= 300:
            raise CloudDocumentError(f"Document metadata creation failed ({response.status_code}).")
        rows = response.json()
        if not rows:
            raise CloudDocumentError("Document metadata creation returned no row.")
        return rows[0]

    def delete_document(self, *, owner_id: str, document_id: str) -> None:
        response = httpx.delete(
            f"{self.base_url}/rest/v1/doka_documents",
            headers=self._headers(),
            params={"id": f"eq.{document_id}", "owner_id": f"eq.{owner_id}"},
            timeout=15.0,
        )
        if response.status_code >= 300:
            raise CloudDocumentError(f"Document metadata deletion failed ({response.status_code}).")


def build_cloud_document_service(access_token: str) -> CloudDocumentService:
    return CloudDocumentService(
        project_url=os.getenv("SUPABASE_URL", ""),
        api_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
        access_token=access_token,
    )
