import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cloudflare_worker"))

import pytest

from storage_b2 import (
    B2PartReceipt,
    B2StorageConfig,
    B2StorageProvider,
    MultipartUpload,
    b2_multipart_composite_etag,
)
from storage_contracts_compat import SignedUpload, StorageObjectRef


def _hex_md5(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def _part(data: bytes, number: int) -> B2PartReceipt:
    md5_hex = _hex_md5(data)
    return B2PartReceipt(
        number,
        md5_hex,
        hashlib.sha256(data).hexdigest(),
        md5_hex,
        SignedUpload("PUT", "https://example.invalid", {}),
    )


class FakeFetcher:
    def __init__(self, final_etag: str, verified: dict):
        self.final_etag = final_etag
        self.verified = verified
        self.calls = []

    async def __call__(self, url, *, method="GET", headers=None, body=None, return_headers=False,
                       return_sha256=False, max_bytes=50 * 1024 * 1024, part_size_bytes=None):
        self.calls.append((method, url, headers, body, return_sha256, max_bytes, part_size_bytes))
        if method == "POST":
            return 200, f"<CompleteMultipartUploadResult><ETag>\"{self.final_etag}\"</ETag></CompleteMultipartUploadResult>"
        if method == "GET" and return_sha256:
            return 200, self.verified
        if method == "DELETE":
            return 204, ""
        raise AssertionError(f"unexpected fetch {method} {url}")


def _upload(size: int, sha: str) -> MultipartUpload:
    return MultipartUpload(
        "upload-123",
        StorageObjectRef("b2", "users/u/documents/key/file.bin", "u"),
        5 * 1024 * 1024,
        9999999999,
        size,
        sha,
        "application/octet-stream",
    )


def test_upload_part_records_client_md5_and_avoids_undocumented_checksum_headers():
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret"),
        FakeFetcher("", {}),
    )
    receipt = asyncio.run(provider.uploadPart(_upload(10, "a" * 64), 1, "b" * 64, "c" * 32))
    assert receipt.signed_request.headers == {}
    assert receipt.content_md5 == "c" * 32
    assert "x-amz-checksum-sha256" not in receipt.signed_request.headers


def test_complete_verifies_provider_composite_etag_and_readback_whole_and_part_hashes():
    data1, data2 = b"a" * (5 * 1024 * 1024), b"tail"
    parts = [_part(data1, 1), _part(data2, 2)]
    complete_data = data1 + data2
    composite = b2_multipart_composite_etag([p.etag for p in parts])
    expected_composite = hashlib.md5(
        bytes.fromhex(parts[0].etag) + bytes.fromhex(parts[1].etag), usedforsecurity=False
    ).hexdigest() + "-2"
    assert composite == expected_composite
    fetcher = FakeFetcher(composite, {
        "size_bytes": len(complete_data),
        "sha256": hashlib.sha256(complete_data).hexdigest(),
        "part_sha256s": [p.checksum for p in parts],
    })
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret", part_size_bytes=5 * 1024 * 1024),
        fetcher,
    )
    upload = _upload(len(complete_data), hashlib.sha256(complete_data).hexdigest())
    result = asyncio.run(provider.completeMultipartUpload(upload, parts))
    assert result.size_bytes == len(complete_data)
    assert result.sha256 == upload.expected_sha256
    assert [call[0] for call in fetcher.calls] == ["POST", "GET"]
    assert fetcher.calls[1][4] is True
    assert fetcher.calls[1][6] == upload.part_size_bytes


def test_complete_fails_closed_and_deletes_object_when_readback_hash_mismatches():
    data1, data2 = b"a" * (5 * 1024 * 1024), b"tail"
    parts = [_part(data1, 1), _part(data2, 2)]
    complete_data = data1 + data2
    composite = b2_multipart_composite_etag([p.etag for p in parts])
    fetcher = FakeFetcher(composite, {
        "size_bytes": len(complete_data),
        "sha256": "0" * 64,
        "part_sha256s": [p.checksum for p in parts],
    })
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret", part_size_bytes=5 * 1024 * 1024),
        fetcher,
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        asyncio.run(provider.completeMultipartUpload(_upload(len(complete_data), hashlib.sha256(complete_data).hexdigest()), parts))
    assert [call[0] for call in fetcher.calls] == ["POST", "GET", "DELETE"]


def test_complete_rejects_part_etag_mismatch_before_provider_completion():
    parts = [_part(b"part-one", 1), _part(b"part-two", 2)]
    parts[0] = B2PartReceipt(1, "f" * 32, parts[0].checksum, parts[0].content_md5, parts[0].signed_request)
    fetcher = FakeFetcher("", {})
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret"),
        fetcher,
    )
    with pytest.raises(ValueError, match="ETag does not match"):
        asyncio.run(provider.completeMultipartUpload(_upload(5 * 1024 * 1024 + 4, "a" * 64), parts))
    assert fetcher.calls == []


def test_complete_fails_closed_when_any_readback_part_sha256_mismatches():
    data1, data2 = b"a" * (5 * 1024 * 1024), b"tail"
    parts = [_part(data1, 1), _part(data2, 2)]
    complete_data = data1 + data2
    composite = b2_multipart_composite_etag([p.etag for p in parts])
    fetcher = FakeFetcher(composite, {
        "size_bytes": len(complete_data),
        "sha256": hashlib.sha256(complete_data).hexdigest(),
        "part_sha256s": ["0" * 64, parts[1].checksum],
    })
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret", part_size_bytes=5 * 1024 * 1024),
        fetcher,
    )
    with pytest.raises(ValueError, match="part SHA-256 mismatch"):
        asyncio.run(provider.completeMultipartUpload(_upload(len(complete_data), hashlib.sha256(complete_data).hexdigest()), parts))
    assert [call[0] for call in fetcher.calls] == ["POST", "GET", "DELETE"]


def test_failed_provider_completion_aborts_unfinished_multipart_upload():
    class FailedCompleteFetcher(FakeFetcher):
        async def __call__(self, url, *, method="GET", headers=None, body=None, return_headers=False,
                           return_sha256=False, max_bytes=50 * 1024 * 1024, part_size_bytes=None):
            self.calls.append((method, url, headers, body, return_sha256, max_bytes, part_size_bytes))
            if method == "POST":
                return 500, "provider error"
            if method == "DELETE":
                return 204, ""
            raise AssertionError(f"unexpected fetch {method} {url}")

    data1, data2 = b"a" * (5 * 1024 * 1024), b"tail"
    parts = [_part(data1, 1), _part(data2, 2)]
    fetcher = FailedCompleteFetcher("", {})
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret", part_size_bytes=5 * 1024 * 1024),
        fetcher,
    )
    with pytest.raises(RuntimeError, match="completion failed"):
        asyncio.run(provider.completeMultipartUpload(_upload(5 * 1024 * 1024 + 4, "a" * 64), parts))
    assert [call[0] for call in fetcher.calls] == ["POST", "DELETE"]


def test_provider_composite_etag_mismatch_deletes_completed_object():
    data1, data2 = b"a" * (5 * 1024 * 1024), b"tail"
    parts = [_part(data1, 1), _part(data2, 2)]
    complete_data = data1 + data2
    fetcher = FakeFetcher("0" * 32 + "-2", {
        "size_bytes": len(complete_data),
        "sha256": hashlib.sha256(complete_data).hexdigest(),
        "part_sha256s": [p.checksum for p in parts],
    })
    provider = B2StorageProvider(
        B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key", "secret", part_size_bytes=5 * 1024 * 1024),
        fetcher,
    )
    with pytest.raises(ValueError, match="composite ETag mismatch"):
        asyncio.run(provider.completeMultipartUpload(_upload(len(complete_data), hashlib.sha256(complete_data).hexdigest()), parts))
    assert [call[0] for call in fetcher.calls] == ["POST", "DELETE"]
