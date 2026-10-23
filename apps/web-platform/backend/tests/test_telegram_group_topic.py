import pytest

from app.api.routes import telegram


def _configure_target(monkeypatch, *, enabled="true", chat_id="-1003992125718", topic_id="18"):
    monkeypatch.setenv("TELEGRAM_ENABLED", enabled)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", chat_id)
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", topic_id)


def test_telegram_context_accepts_only_configured_group_topic(monkeypatch):
    _configure_target(monkeypatch)

    assert telegram._telegram_context_allowed(-1003992125718, 18)
    assert telegram._telegram_context_allowed("-1003992125718", 18)
    assert not telegram._telegram_context_allowed(-1003992125719, 18)
    assert not telegram._telegram_context_allowed(-1003992125718, 19)
    assert not telegram._telegram_context_allowed(-1003992125718, None)


@pytest.mark.parametrize(
    ("enabled", "chat_id", "topic_id"),
    [
        ("false", "-1003992125718", "18"),
        ("true", "", "18"),
        ("true", "-1003992125718", ""),
        ("true", "-1003992125718", "general"),
    ],
)
def test_telegram_context_fails_closed_when_target_is_not_configured(
    monkeypatch, enabled, chat_id, topic_id
):
    _configure_target(
        monkeypatch,
        enabled=enabled,
        chat_id=chat_id,
        topic_id=topic_id,
    )

    assert not telegram._telegram_context_allowed(-1003992125718, 18)
