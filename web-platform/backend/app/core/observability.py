"""Safe, optional observability integration for the local-first DMS.

Sentry is opt-in. Document contents, OCR text, sensitive filesystem paths,
request bodies, and secrets are intentionally excluded from telemetry.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.config import settings


def _scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Remove potentially sensitive request data before an event is sent."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie", "x-api-key", "x-auth-token"}:
                    headers.pop(key, None)

    # URL paths and query strings can contain private document names or identifiers.
    if isinstance(request, dict):
        request.pop("url", None)
        request.pop("query_string", None)
        request.pop("env", None)

    # Do not attach user identity, arbitrary breadcrumbs, runtime contexts,
    # or custom extras from the document plane.
    event.pop("user", None)
    event.pop("extra", None)
    event.pop("breadcrumbs", None)
    event.pop("contexts", None)
    return event


def init_observability() -> None:
    """Initialize Sentry only when explicitly configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled: SENTRY_DSN is not configured.")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[FastApiIntegration()],
            send_default_pii=False,
            traces_sample_rate=0.0,
            before_send=_scrub_event,
        )
        logger.info("Sentry enabled with document-data-safe event scrubbing.")
    except Exception as exc:
        # Observability must never prevent the local DMS from starting.
        logger.warning(f"Sentry initialization skipped: {exc}")
