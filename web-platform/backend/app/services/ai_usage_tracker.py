from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_TODAY_DATE = datetime.now(timezone.utc).date().isoformat()
_CALLS_TODAY: Dict[str, int] = {}
_TOTAL_CALLS: Dict[str, int] = {}
_ERRORS_TODAY: Dict[str, int] = {}
_EXHAUSTED_PROVIDERS: set[str] = set()
_LAST_USED: Dict[str, str] = {}


def _check_and_reset_day():
    global _TODAY_DATE, _CALLS_TODAY, _ERRORS_TODAY
    current_day = datetime.now(timezone.utc).date().isoformat()
    if current_day != _TODAY_DATE:
        _TODAY_DATE = current_day
        _CALLS_TODAY.clear()
        _ERRORS_TODAY.clear()
        _EXHAUSTED_PROVIDERS.clear()


def record_ai_usage(provider: str, task: str = "chat", success: bool = True, error: Optional[str] = None):
    p = provider.lower()
    now_str = datetime.now(timezone.utc).isoformat()
    exhausted_newly = False
    with _LOCK:
        _check_and_reset_day()
        _TOTAL_CALLS[p] = _TOTAL_CALLS.get(p, 0) + 1
        _CALLS_TODAY[p] = _CALLS_TODAY.get(p, 0) + 1
        _LAST_USED[p] = now_str
        if not success:
            _ERRORS_TODAY[p] = _ERRORS_TODAY.get(p, 0) + 1
            if error and ("429" in error or "quota" in error.lower() or "rate" in error.lower()):
                if p not in _EXHAUSTED_PROVIDERS:
                    exhausted_newly = True
                _EXHAUSTED_PROVIDERS.add(p)

    if exhausted_newly:
        _dispatch_quota_alert("Doka-AI-DMS", p, error or "HTTP 429 Rate Limit / Quota Exhausted")


def mark_provider_exhausted(provider: str):
    p = provider.lower()
    exhausted_newly = False
    with _LOCK:
        if p not in _EXHAUSTED_PROVIDERS:
            exhausted_newly = True
        _EXHAUSTED_PROVIDERS.add(p)
    if exhausted_newly:
        _dispatch_quota_alert("Doka-AI-DMS", p, "Provider marked exhausted")


def _dispatch_quota_alert(project: str, provider: str, reason: str):
    import threading

    def _send():
        try:
            import httpx
            token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
            topic_id = os.getenv("TELEGRAM_TOPIC_ID", "").strip()
            if not token or not chat_id:
                return
            msg = (
                f"⚠️ <b>[AI Quota Exhaustion Alert]</b>\n\n"
                f"• <b>Project:</b> {project}\n"
                f"• <b>Provider:</b> <code>{provider.upper()}</code>\n"
                f"• <b>Reason:</b> {reason}\n"
                f"• <b>Status:</b> Auto-switched to next candidate in Fallback Chain."
            )
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML",
            }
            if topic_id:
                payload["message_thread_id"] = int(topic_id)
            with httpx.Client(timeout=10.0) as client:
                client.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def get_ai_usage_summary(project_name: str = "Doka-AI-DMS") -> Dict[str, Any]:
    with _LOCK:
        _check_and_reset_day()

        providers_config = {
            "groq": bool(os.getenv("GROQ_API_KEY", "").strip() and not os.getenv("GROQ_API_KEY", "").startswith("your_")),
            "gemini": bool(os.getenv("GEMINI_API_KEY", "").strip() and not os.getenv("GEMINI_API_KEY", "").startswith("your_")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY", "").strip() and not os.getenv("OPENROUTER_API_KEY", "").startswith("your_")),
            "mistral": bool(os.getenv("MISTRAL_API_KEY", "").strip() and not os.getenv("MISTRAL_API_KEY", "").startswith("your_")),
            "cohere": bool(os.getenv("COHERE_API_KEY", "").strip() and not os.getenv("COHERE_API_KEY", "").startswith("your_")),
            "voyage": bool(os.getenv("VOYAGE_API_KEY", "").strip() and not os.getenv("VOYAGE_API_KEY", "").startswith("your_")),
            "nvidia": bool(os.getenv("NVIDIA_API_KEY", "").strip() and not os.getenv("NVIDIA_API_KEY", "").startswith("your_")),
            "cloudflare": bool(os.getenv("CLOUDFLARE_API_KEY", "").strip() and not os.getenv("CLOUDFLARE_API_KEY", "").startswith("your_")),
        }

        provider_stats = {}
        for prov, configured in providers_config.items():
            if not configured:
                status = "unconfigured"
            elif prov in _EXHAUSTED_PROVIDERS:
                status = "exhausted (quota/429)"
            else:
                status = "active"

            provider_stats[prov] = {
                "configured": configured,
                "status": status,
                "calls_today": _CALLS_TODAY.get(prov, 0),
                "total_calls": _TOTAL_CALLS.get(prov, 0),
                "errors_today": _ERRORS_TODAY.get(prov, 0),
                "last_used": _LAST_USED.get(prov, None),
            }

        return {
            "project": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": _TODAY_DATE,
            "total_calls_today": sum(_CALLS_TODAY.values()),
            "active_chains": {
                "chat_priority": ["groq", "gemini", "openrouter", "mistral", "cohere", "nvidia"],
                "rag_priority": ["voyage", "cohere"],
            },
            "providers": provider_stats,
        }
