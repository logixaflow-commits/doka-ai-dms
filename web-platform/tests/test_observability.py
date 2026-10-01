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
            "url": "https://api.example.test/api/documents/name",
            "query_string": "key=value",
            "env": {"INTERNAL_SETTING": "hidden"},
        },
        "breadcrumbs": [{"message": "document opened"}],
        "contexts": {"document": {"path": "private-path"}},
        "user": {"id": "user-123"},
        "extra": {"payload": "hidden"},
    }

    scrubbed = _scrub_event(event, {})

    assert "data" not in scrubbed["request"]
    assert "cookies" not in scrubbed["request"]
    assert "Authorization" not in scrubbed["request"]["headers"]
    assert "Cookie" not in scrubbed["request"]["headers"]
    assert "url" not in scrubbed["request"]
    assert "query_string" not in scrubbed["request"]
    assert "env" not in scrubbed["request"]
    assert scrubbed["request"]["headers"]["Content-Type"] == "application/json"
    assert "breadcrumbs" not in scrubbed
    assert "contexts" not in scrubbed
    assert "user" not in scrubbed
    assert "extra" not in scrubbed
