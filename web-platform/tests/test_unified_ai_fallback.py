import pytest

from app.core.config import settings
from app.services.unified_ai_service import UnifiedAIService


@pytest.mark.asyncio
async def test_ai_fallback_uses_next_provider(monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_CONSENT", True)
    monkeypatch.setattr(settings, "AI_PROVIDER_ORDER", ["gemini", "openrouter", "groq"])
    monkeypatch.setattr(settings, "AI_PROVIDER_MAX_ATTEMPTS", 0)

    service = UnifiedAIService()
    service.providers = {"gemini": {}, "openrouter": {}, "groq": {}}
    calls = []

    async def call(provider):
        calls.append(provider)
        if provider == "gemini":
            raise RuntimeError("quota")
        return {"provider": provider}

    result = await service._with_fallback("test", call)
    assert result == {"provider": "openrouter"}
    assert calls == ["gemini", "openrouter"]


@pytest.mark.asyncio
async def test_ai_stays_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    service = UnifiedAIService()
    with pytest.raises(RuntimeError, match="AI is disabled"):
        await service._with_fallback("test", lambda _: None)


@pytest.mark.asyncio
async def test_external_ai_requires_separate_explicit_consent(monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_CONSENT", False)
    service = UnifiedAIService()
    service.providers = {"openai": {"api_key": "test", "model": "test"}}
    called = False

    async def call(_provider):
        nonlocal called
        called = True
        return "should not run"

    with pytest.raises(RuntimeError, match="consent is required"):
        await service._with_fallback("sensitive-document", call)
    assert called is False
