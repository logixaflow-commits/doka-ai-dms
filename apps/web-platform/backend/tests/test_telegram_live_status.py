from app.api.routes import telegram


def test_live_status_reports_database_and_ocr_counts_without_claiming_storage_health():
    message, snapshot = telegram._format_live_status(
        {"status": "connected"},
        {"queued": 2, "processing": 1, "completed": 5, "failed": 1},
    )

    assert "Database: healthy" in message
    assert "OCR queue: 1 processing, 2 queued" in message
    assert "5 completed, 1 failed" in message
    assert "Storage: not checked by this command" in message
    assert snapshot == {
        "database": "healthy",
        "ocr_queue": {
            "queued": 2,
            "processing": 1,
            "completed": 5,
            "failed": 1,
        },
    }


def test_live_status_does_not_expose_raw_database_errors():
    message, snapshot = telegram._format_live_status(
        {"status": "error", "error": "postgresql://secret-user:secret-password@db.invalid"},
        None,
    )

    assert "Database: unavailable" in message
    assert "OCR queue: unavailable" in message
    assert "secret-password" not in message
    assert snapshot == {"database": "unavailable", "ocr_queue": None}
