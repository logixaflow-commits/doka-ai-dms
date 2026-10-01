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


def test_sentry_scrubber_removes_exception_paths_messages_and_frame_locals():
    event = {
        "exception": {
            "values": [{
                "type": "FileNotFoundError",
                "value": "missing /home/alice/private/contracts/client.pdf",
                "stacktrace": {
                    "frames": [{
                        "filename": "/home/alice/private/contracts/client.pdf",
                        "abs_path": "/home/alice/private/contracts/client.pdf",
                        "vars": {"document_text": "private content"},
                        "function": "read_document",
                    }]
                },
            }]
        },
        "logentry": {"message": "Failed to open client.pdf", "params": ["private"]},
        "message": "private filename",
        "transaction": "/documents/client.pdf",
        "tags": {"filename": "client.pdf", "user_id": "user-1"},
    }

    scrubbed = _scrub_event(event, {})
    exception = scrubbed["exception"]["values"][0]
    frame = exception["stacktrace"]["frames"][0]

    assert exception["type"] == "FileNotFoundError"
    assert exception["value"] == "[Filtered]"
    assert "filename" not in frame
    assert "abs_path" not in frame
    assert "vars" not in frame
    assert frame["function"] == "read_document"
    assert scrubbed["logentry"] == {}
    assert "message" not in scrubbed
    assert "transaction" not in scrubbed
    assert "tags" not in scrubbed
