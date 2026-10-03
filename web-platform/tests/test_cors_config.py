import pytest

from app.main import parse_cors_origins


def test_cors_origins_accepts_explicit_http_and_https_origins():
    assert parse_cors_origins("http://localhost:5173, https://doka.example.com/") == [
        "http://localhost:5173",
        "https://doka.example.com",
    ]


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "http://localhost:5173,*",
        "",
        "https://example.com/path",
        "https://example.com?next=/",
        "ftp://example.com",
        "https://user:password@example.com",
        "https://example.com:99999",
        "null",
    ],
)
def test_cors_origins_rejects_wildcard_and_non_origin_values(value):
    with pytest.raises(ValueError):
        parse_cors_origins(value)


def test_cors_origins_deduplicates_equivalent_trailing_slash_entries():
    assert parse_cors_origins("https://doka.example.com/,https://doka.example.com") == [
        "https://doka.example.com"
    ]
