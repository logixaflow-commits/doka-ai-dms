"""
Office DMS - Unified AI Service
Free-first multi-provider AI orchestration with automatic fallback.
AI is optional: local/rule-based processing remains the default.
"""
import json
from typing import Optional, Dict, Any, List, Callable, Awaitable
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class UnifiedAIService:
    """Unified AI service with ordered providers and failure fallback."""

    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {}
        self._init_providers()

    def _init_providers(self):
        configured = {
            "gemini": (settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
            "openrouter": (settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL),
            "groq": (settings.GROQ_API_KEY, settings.GROQ_MODEL),
            "openai": (settings.OPENAI_API_KEY, settings.OPENAI_MODEL),
        }
        for name, (api_key, model) in configured.items():
            if api_key and not api_key.startswith("your_"):
                self.providers[name] = {
                    "api_key": api_key,
                    "model": model,
                    "enabled": True,
                }

        if self.providers:
            logger.info("AI providers configured: %s", self.get_available_providers())
        else:
            logger.info("No AI providers configured; local processing remains active")

    def get_available_providers(self) -> List[str]:
        """Return configured providers in the user's preferred order."""
        ordered = [p for p in settings.AI_PROVIDER_ORDER if p in self.providers]
        remaining = [p for p in self.providers if p not in ordered]
        return ordered + remaining

    def _provider_limit(self) -> int:
        configured = settings.AI_PROVIDER_MAX_ATTEMPTS
        return configured if configured > 0 else len(self.get_available_providers())

    async def _with_fallback(
        self,
        operation: str,
        call: Callable[[str], Awaitable[Any]],
        providers: Optional[List[str]] = None,
    ) -> Any:
        """Try providers in order; on quota/network/model failure continue to the next."""
        if not settings.AI_ENABLED:
            raise RuntimeError("AI is disabled; use local/rule-based processing")
        if not getattr(settings, "AI_EXTERNAL_PROCESSING_CONSENT", False):
            raise RuntimeError("External AI processing consent is required before sending document content to a provider.")

        candidates = providers or self.get_available_providers()
        candidates = candidates[: self._provider_limit()]
        if not candidates:
            raise RuntimeError("No AI providers are configured")

        errors = []
        for provider in candidates:
            try:
                result = await call(provider)
                logger.info("AI operation '%s' completed with provider '%s'", operation, provider)
                return result
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                logger.warning("AI provider '%s' failed for '%s'; trying next provider", provider, operation)

        raise RuntimeError(f"All configured AI providers failed for '{operation}': " + " | ".join(errors))

    async def call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        provider = self.providers.get("openai")
        if not provider:
            raise ValueError("OpenAI provider not available")
        return await self._call_openai(provider, prompt, system_prompt)

    async def _call_openai(self, provider: Dict[str, Any], prompt: str, system_prompt: Optional[str]) -> str:
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"},
                json={"model": provider["model"], "messages": messages, "temperature": 0.2, "max_tokens": 1200},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        provider = self.providers.get("gemini")
        if not provider:
            raise ValueError("Gemini provider not available")
        return await self._call_gemini(provider, prompt, system_prompt)

    async def _call_gemini(self, provider: Dict[str, Any], prompt: str, system_prompt: Optional[str]) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        async with httpx.AsyncClient(timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={provider['api_key']}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200},
                },
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def call_openrouter(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        provider = self.providers.get("openrouter")
        if not provider:
            raise ValueError("OpenRouter provider not available")
        return await self._call_openrouter(provider, prompt, system_prompt)

    async def _call_openrouter(self, provider: Dict[str, Any], prompt: str, system_prompt: Optional[str]) -> str:
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://enterprise-dms.local",
                    "X-Title": "Enterprise DMS",
                },
                json={"model": provider["model"], "messages": messages, "temperature": 0.2, "max_tokens": 1200},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def call_groq(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        provider = self.providers.get("groq")
        if not provider:
            raise ValueError("Groq provider not available")
        return await self._call_groq(provider, prompt, system_prompt)

    async def _call_groq(self, provider: Dict[str, Any], prompt: str, system_prompt: Optional[str]) -> str:
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"},
                json={"model": provider["model"], "messages": messages, "temperature": 0.2, "max_tokens": 1200},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def analyze_document(self, text: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a document with an explicit provider or free-first fallback chain."""
        system_prompt = (
            "You are a document classification assistant for an office DMS. "
            "Analyze the supplied document text. Return JSON only with keys: "
            "category, confidence, key_entities, suspicious, suspicious_reason. "
            "Do not invent values; use null or empty lists when unknown."
        )

        async def call(prov: str):
            if prov == "gemini":
                raw = await self.call_gemini(text, system_prompt)
            elif prov == "openrouter":
                raw = await self.call_openrouter(text, system_prompt)
            elif prov == "groq":
                raw = await self.call_groq(text, system_prompt)
            elif prov == "openai":
                raw = await self.call_openai(text, system_prompt)
            else:
                raise ValueError(f"Unsupported AI provider: {prov}")
            return json.loads(raw)

        providers = [provider] if provider else None
        return await self._with_fallback("document_analysis", call, providers)

    async def get_embedding(self, text: str, provider: str = "huggingface") -> List[float]:
        """Embeddings are optional; semantic search must have a local fallback."""
        if not settings.AI_ENABLED:
            raise RuntimeError("AI is disabled; use local/rule-based processing")
        if not getattr(settings, "AI_EXTERNAL_PROCESSING_CONSENT", False):
            raise RuntimeError("External AI processing consent is required before sending document content to a provider.")
        if provider != "huggingface" or not settings.HUGGINGFACE_API_KEY:
            raise ValueError("Hugging Face embeddings are not configured")
        cfg = {"api_key": settings.HUGGINGFACE_API_KEY, "model": settings.HUGGINGFACE_MODEL}
        async with httpx.AsyncClient(timeout=settings.AI_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{cfg['model']}",
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                json={"inputs": text},
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data and isinstance(data[0], list):
                return data[0]
            return data

    async def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare embeddings; callers should fall back to local TF-IDF if this fails."""
        try:
            emb1, emb2 = await self.get_embedding(text1), await self.get_embedding(text2)
            import numpy as np
            denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)
            return float(np.dot(emb1, emb2) / denom) if denom else 0.0
        except Exception as exc:
            logger.warning("Embedding similarity failed: %s", exc)
            return 0.0


ai_service = UnifiedAIService()
