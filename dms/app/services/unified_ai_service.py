"""
Office DMS - Unified AI Service
Supports multiple AI providers: OpenAI, Gemini, Hugging Face, OpenRouter, Groq
"""
import os
import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class UnifiedAIService:
    """Unified AI service supporting multiple providers."""

    def __init__(self):
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize available AI providers."""
        # OpenAI
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            self.providers['openai'] = {
                'api_key': settings.OPENAI_API_KEY,
                'model': settings.OPENAI_MODEL,
                'enabled': True
            }
            logger.info("✓ OpenAI provider initialized")

        # Gemini
        if settings.GEMINI_API_KEY:
            self.providers['gemini'] = {
                'api_key': settings.GEMINI_API_KEY,
                'model': settings.GEMINI_MODEL,
                'enabled': True
            }
            logger.info("✓ Gemini provider initialized")

        # Hugging Face
        if settings.HUGGINGFACE_API_KEY:
            self.providers['huggingface'] = {
                'api_key': settings.HUGGINGFACE_API_KEY,
                'model': settings.HUGGINGFACE_MODEL,
                'enabled': True
            }
            logger.info("✓ Hugging Face provider initialized")

        # OpenRouter
        if settings.OPENROUTER_API_KEY:
            self.providers['openrouter'] = {
                'api_key': settings.OPENROUTER_API_KEY,
                'model': settings.OPENROUTER_MODEL,
                'enabled': True
            }
            logger.info("✓ OpenRouter provider initialized")

        # Groq
        if settings.GROQ_API_KEY:
            self.providers['groq'] = {
                'api_key': settings.GROQ_API_KEY,
                'model': settings.GROQ_MODEL,
                'enabled': True
            }
            logger.info("✓ Groq provider initialized")

        if not self.providers:
            logger.warning("No AI providers initialized")

    def get_available_providers(self) -> List[str]:
        """Get list of available AI providers."""
        return [name for name, config in self.providers.items() if config['enabled']]

    async def call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call OpenAI API."""
        provider = self.providers.get('openai')
        if not provider:
            raise ValueError("OpenAI provider not available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                }

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": provider['model'],
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )

                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Gemini API."""
        provider = self.providers.get('gemini')
        if not provider:
            raise ValueError("Gemini provider not available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Content-Type": "application/json"}

                # Combine system prompt and user prompt for Gemini
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={provider['api_key']}",
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 1000
                        }
                    }
                )

                response.raise_for_status()
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def call_huggingface(self, text: str, task: str = "feature-extraction") -> List[float]:
        """Call Hugging Face API for embeddings or classification."""
        provider = self.providers.get('huggingface')
        if not provider:
            raise ValueError("Hugging Face provider not available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                }

                response = await client.post(
                    f"https://api-inference.huggingface.co/models/{provider['model']}",
                    headers=headers,
                    json={"inputs": text}
                )

                response.raise_for_status()
                data = response.json()

                # Handle different response types
                if isinstance(data, list) and isinstance(data[0], list):
                    return data[0]  # Embeddings
                elif isinstance(data, list) and isinstance(data[0], dict):
                    # Classification result
                    return data
                else:
                    return data

        except Exception as e:
            logger.error(f"Hugging Face API error: {e}")
            raise

    async def call_openrouter(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call OpenRouter API."""
        provider = self.providers.get('openrouter')
        if not provider:
            raise ValueError("OpenRouter provider not available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://enterprise-dms.local",
                    "X-Title": "Enterprise DMS"
                }

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": provider['model'],
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )

                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise

    async def call_groq(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Groq API for ultra-fast inference."""
        provider = self.providers.get('groq')
        if not provider:
            raise ValueError("Groq provider not available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                }

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": provider['model'],
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )

                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    async def analyze_document(self, text: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Analyze document text using AI for classification and insights."""
        if provider and provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")

        # Use specified provider or try available ones
        providers_to_try = [provider] if provider else self.get_available_providers()

        for prov in providers_to_try:
            try:
                system_prompt = """You are a document classification expert for logistics documents.
                Analyze the document and provide:
                1. Category (Invoice, BL, NRC, FDA, License, etc.)
                2. Confidence score (0.0-1.0)
                3. Key entities (supplier, amount, dates, etc.)
                4. Is suspicious (yes/no) and reason

                Respond in JSON format."""

                if prov == 'openai':
                    result = await self.call_openai(text, system_prompt)
                elif prov == 'gemini':
                    result = await self.call_gemini(text, system_prompt)
                elif prov == 'openrouter':
                    result = await self.call_openrouter(text, system_prompt)
                elif prov == 'groq':
                    result = await self.call_groq(text, system_prompt)
                else:
                    continue

                # Parse JSON response
                import json
                return json.loads(result)

            except Exception as e:
                logger.warning(f"Failed to use provider {prov}: {e}")
                continue

        raise Exception("All AI providers failed")

    async def get_embedding(self, text: str, provider: str = "huggingface") -> List[float]:
        """Get text embedding for semantic search."""
        if provider == "huggingface":
            return await self.call_huggingface(text, task="feature-extraction")
        else:
            raise ValueError(f"Embeddings not supported for provider: {provider}")

    async def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare semantic similarity between two texts."""
        try:
            emb1 = await self.get_embedding(text1)
            emb2 = await self.get_embedding(text2)

            # Calculate cosine similarity
            import numpy as np
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)

        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            return 0.0


# Global instance
ai_service = UnifiedAIService()