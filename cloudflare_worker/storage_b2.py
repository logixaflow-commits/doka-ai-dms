"""Backblaze B2 S3-compatible direct-upload and multipart adapter."""
from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote, urlencode, urlsplit

from cloudflare_worker.storage_contracts_compat import (
    B2_MULTIPART_THRESHOLD_BYTES,
    SignedUpload,
    StorageObjectRef,
    StoredObjectResult,
    UploadMetadata,
    UploadSession,
    owner_object_key,
)


@dataclass(frozen=True)
class B2StorageConfig:
    endpoint: str
    bucket: str
    key_id: str
    application_key: str
    region: str = "us-east-005"
    signed_url_ttl_seconds: int = 900
    part_size_bytes: int = 100 * 1024 * 1024


@dataclass(frozen=True)
class MultipartUpload:
    upload_id: str
    object_ref: StorageObjectRef
    part_size_bytes: int
    expires_at: int


@dataclass(frozen=True)
class B2PartReceipt:
    part_number: int
    etag: str
    checksum: str
    signed_request: SignedUpload


class B2StorageProvider:
    name = "b2"

    def __init__(self, config: B2StorageConfig, fetcher):
        if not all((config.endpoint, config.bucket, config.key_id, config.application_key)):
            raise ValueError("B2 configuration is incomplete")
        if config.part_size_bytes < 5 * 1024 * 1024:
            raise ValueError("B2 multipart part size must be at least 5 MiB")
        self.config = config
        self.fetcher = fetcher

    def _canonical_uri(self, object_key: str) -> str:
        return "/" + quote(self.config.bucket, safe="-_.~") + "/" + quote(object_key, safe="/-_.~")

    def _signing_key(self, date: str) -> bytes:
        secret = self.config.application_key.encode()
        k_date = hmac.new(b"AWS4" + secret, date.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, self.config.region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, b"s3", hashlib.sha256).digest()
        return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()

    def _presign(self, object_key: str, *, method: str, query: dict[str, str] | None = None, headers: dict[str, str] | None = None, expires_seconds: int | None = None) -> str:
        headers = {k.lower(): str(v).strip() for k, v in (headers or {}).items()}
        host = urlsplit(self.config.endpoint).netloc
        headers["host"] = host
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        short_date = now.strftime("%Y%m%d")
        credential_scope = f"{short_date}/{self.config.region}/s3/aws4_request"
        signed_headers = ";".join(sorted(headers))
        params = dict(query or {})
        params.update({
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.config.key_id}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(min(max(1, expires_seconds if expires_seconds is not None else self.config.signed_url_ttl_seconds), 604800)),
            "X-Amz-SignedHeaders": signed_headers,
        })
        canonical_query = "&".join(f"{quote(str(k), safe='-_.~')}={quote(str(params[k]), safe='-_.~')}" for k in sorted(params))
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
        canonical_request = "\n".join([
            method.upper(),
            self._canonical_uri(object_key),
            canonical_query,
            canonical_headers,
            signed_headers,
            "UNSIGNED-PAYLOAD",
        ])
        scope = credential_scope
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])
        signature = hmac.new(self._signing_key(short_date), string_to_sign.encode(), hashlib.sha256).hexdigest()
        params["X-Amz-Signature"] = signature
        final_query = "&".join(f"{quote(str(k), safe='-_.~')}={quote(str(params[k]), safe='-_.~')}" for k in sorted(params))
        return self.config.endpoint.rstrip("/") + self._canonical_uri(object_key) + "?" + final_query

    def _object_url(self, key: str) -> str:
        return self.config.endpoint.rstrip("/") + self._canonical_uri(key)

    async def create_upload_session(self, metadata: UploadMetadata) -> UploadSession:
        metadata.validate()
        if metadata.artifact_type.value != "source":
            raise ValueError("B2 source provider only accepts original/source objects")
        if metadata.size_bytes <= 50 * 1024 * 1024:
            raise ValueError("B2 is reserved for source objects above 50 MiB")
        key = owner_object_key(metadata)
        url = self._presign(
            key,
            method="PUT",
            headers={
                "content-type": metadata.content_type,
                "x-amz-meta-sha256": metadata.sha256.lower(),
            },
        )
        return UploadSession(
            provider=self.name,
            object_ref=StorageObjectRef(self.name, key, metadata.owner_id),
            expires_at=int(time.time()) + min(max(60, self.config.signed_url_ttl_seconds), 604800),
            upload=SignedUpload(
                method="PUT",
                url=url,
                headers={"content-type": metadata.content_type, "x-amz-meta-sha256": metadata.sha256.lower()},
            ),
            session_id=f"b2:{metadata.owner_id}:{metadata.sha256.lower()}",
        )

    async def initiateMultipartUpload(self, metadata: UploadMetadata) -> MultipartUpload:
        metadata.validate()
        if metadata.size_bytes <= B2_MULTIPART_THRESHOLD_BYTES:
            raise ValueError("B2 multipart is required only for objects above 5 GiB")
        key = owner_object_key(metadata)
        url = self._presign(key, method="POST", query={"uploads": ""}, headers={"content-type": metadata.content_type})
        status, body = await self.fetcher(url, method="POST", headers={"content-type": metadata.content_type})
        if status >= 300:
            raise RuntimeError("B2 multipart initiation failed")
        upload_id = self._xml_text(body, "UploadId")
        if not upload_id:
            raise RuntimeError("B2 did not return a multipart upload ID")
        return MultipartUpload(
            upload_id=upload_id,
            object_ref=StorageObjectRef(self.name, key, metadata.owner_id),
            part_size_bytes=self.config.part_size_bytes,
            expires_at=int(time.time()) + min(max(300, self.config.signed_url_ttl_seconds), 604800),
        )

    async def uploadPart(self, upload: MultipartUpload, part_number: int, checksum: str, signed_request=None) -> B2PartReceipt:
        if not 1 <= int(part_number) <= 10000:
            raise ValueError("B2 part number must be between 1 and 10000")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", checksum or ""):
            raise ValueError("part checksum must be SHA-256")
        headers = {"x-amz-checksum-sha256": checksum.lower()}
        url = self._presign(
            upload.object_ref.object_key,
            method="PUT",
            query={"partNumber": str(part_number), "uploadId": upload.upload_id},
            headers=headers,
        )
        return B2PartReceipt(part_number, "", checksum.lower(), SignedUpload("PUT", url, headers=headers))

    async def completeMultipartUpload(self, upload: MultipartUpload, parts: list[B2PartReceipt]) -> StoredObjectResult:
        if not parts:
            raise ValueError("At least one B2 multipart part is required")
        ordered = sorted(parts, key=lambda part: part.part_number)
        if [part.part_number for part in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("B2 multipart parts must be contiguous and ordered")
        body = "<CompleteMultipartUpload>" + "".join(
            f"<Part><PartNumber>{p.part_number}</PartNumber><ETag>{p.etag}</ETag></Part>" for p in ordered
        ) + "</CompleteMultipartUpload>"
        url = self._presign(upload.object_ref.object_key, method="POST", query={"uploadId": upload.upload_id}, headers={"content-type": "application/xml"})
        status, _ = await self.fetcher(url, method="POST", headers={"content-type": "application/xml"}, body=body)
        if status >= 300:
            raise RuntimeError("B2 multipart completion failed")
        return await self.head(upload.object_ref)

    async def abortMultipartUpload(self, upload: MultipartUpload) -> None:
        url = self._presign(upload.object_ref.object_key, method="DELETE", query={"uploadId": upload.upload_id})
        status, _ = await self.fetcher(url, method="DELETE")
        if status >= 300 and status != 404:
            raise RuntimeError("B2 multipart abort failed")

    async def complete_upload(self, session: UploadSession, client_result: dict) -> StoredObjectResult:
        result = await self.head(session.object_ref)
        expected_size = int(client_result.get("size_bytes", result.size_bytes))
        expected_sha = str(client_result.get("sha256", result.sha256)).lower()
        if result.size_bytes != expected_size or result.sha256 != expected_sha:
            raise ValueError("B2 upload failed authoritative size/SHA-256 verification")
        return result

    async def head(self, object_ref: StorageObjectRef) -> StoredObjectResult:
        url = self._presign(object_ref.object_key, method="HEAD")
        status, headers = await self.fetcher(url, method="HEAD", return_headers=True)
        if status >= 300:
            raise RuntimeError("B2 object metadata lookup failed")
        if not isinstance(headers, dict):
            raise RuntimeError("B2 object metadata response was invalid")
        size = int(headers.get("content-length") or headers.get("Content-Length") or 0)
        digest = str(headers.get("x-amz-meta-sha256") or headers.get("X-Amz-Meta-Sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError("B2 object is missing authoritative SHA-256 metadata")
        return StoredObjectResult(object_ref, size, digest, str(headers.get("content-type") or "application/octet-stream"))

    async def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 300) -> str:
        if not 1 <= expires_seconds <= 3600:
            raise ValueError("Download URL expiry must be between 1 second and 1 hour")
        return self._presign(object_ref.object_key, method="GET", expires_seconds=expires_seconds)

    async def delete(self, object_ref: StorageObjectRef) -> None:
        url = self._presign(object_ref.object_key, method="DELETE")
        status, _ = await self.fetcher(url, method="DELETE")
        if status >= 300 and status != 404:
            raise RuntimeError("B2 object delete failed")

    @staticmethod
    def _xml_text(payload, tag: str) -> str:
        if isinstance(payload, bytes):
            root = ET.fromstring(payload)
        else:
            root = ET.fromstring(str(payload).encode())
        node = root.find(f".//{{*}}{tag}")
        if node is None:
            node = root.find(f".//{tag}")
        return node.text.strip() if node is not None and node.text else ""
