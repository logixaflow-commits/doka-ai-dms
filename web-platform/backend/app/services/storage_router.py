from __future__ import annotations

from shared.storage_contracts import (
    B2_MULTIPART_THRESHOLD_BYTES, CLOUDINARY_DERIVATIVE_MAX_BYTES, SUPABASE_SOURCE_MAX_BYTES,
    SignedUpload, StorageArtifactType, StorageObjectRef, StorageProvider, StorageProviderName,
    StorageRouter, StoredObjectResult, UploadMetadata, UploadSession, owner_object_key, sha256_for_bytes,
)
