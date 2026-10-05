from __future__ import annotations

from storage_contracts_compat import (
    B2_MULTIPART_THRESHOLD_BYTES, CLOUDINARY_DERIVATIVE_MAX_BYTES, SUPABASE_SOURCE_MAX_BYTES,
    SignedUpload, StorageArtifactType, StorageObjectRef, StorageProvider, StorageProviderName,
    StorageRouter, StoredObjectResult, UploadMetadata, UploadSession, owner_object_key, sha256_for_bytes,
)
