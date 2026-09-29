from app.core.observability import _scrub_event


def test_sentry_scrubber_removes_sensitive_request_data():
    event = {
        "request": {
            "data": {"document_text": "secret"},
            "cookies": {"session": "secret"},
            "headers": {
                "Authorization": "Bearer secret",
                "Cookie": "secret",
                "Content-Type": "application/json",
            },
        },
        "breadcrumbs": [{"message": "document opened"}],
        "contexts": {"document": {"path": "D:/sensitive/file.pdf"}},
    }

    scrubbed = _scrub_event(event, {})

    assert "data" not in scrubbed["request"]
    assert "cookies" not in scrubbed["request"]
    assert "Authorization" not in scrubbed["request"]["headers"]
    assert "Cookie" not in scrubbed["request"]["headers"]
    assert scrubbed["request"]["headers"]["Content-Type"] == "application/json"
    assert "breadcrumbs" not in scrubbed
    assert "contexts" not in scrubbed
