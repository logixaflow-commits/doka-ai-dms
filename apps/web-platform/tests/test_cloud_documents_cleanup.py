from app.api.routes.cloud_documents import _cleanup_failed_upload


class FakeStorage:
    def __init__(self):
        self.deleted = []

    def delete(self, key):
        self.deleted.append(key)


def test_failed_upload_does_not_delete_preexisting_object():
    storage = FakeStorage()

    _cleanup_failed_upload(
        storage,
        "users/user-1/documents/hash/report.pdf",
        upload_completed=False,
    )

    assert storage.deleted == []


def test_metadata_failure_cleans_up_object_created_by_this_request():
    storage = FakeStorage()

    _cleanup_failed_upload(
        storage,
        "users/user-1/documents/hash/report.pdf",
        upload_completed=True,
    )

    assert storage.deleted == ["users/user-1/documents/hash/report.pdf"]


def test_cleanup_failure_does_not_mask_original_upload_error():
    class BrokenStorage:
        def delete(self, key):
            raise RuntimeError("storage cleanup unavailable")

    # Cleanup is best-effort and must not replace the original API failure.
    _cleanup_failed_upload(
        BrokenStorage(),
        "users/user-1/documents/hash/report.pdf",
        upload_completed=True,
    )
