"""Safe, optional observability integration for the local-first DMS.

Sentry is opt-in. Document contents, OCR text, filesystem paths, request bodies,
secrets, exception messages, and stack-frame locals are excluded from telemetry.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.config import settings


def _scrub_stacktrace(stacktrace: Any) -> None:
    if not isinstance(stacktrace, dict):
        return
    frames = stacktrace.get("frames")
    if not isinstance(frames, list):
        return
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        # Frame locals and source paths can expose document names and local usernames.
        frame.pop("vars", None)
        frame.pop("filename", None)
        frame.pop("abs_path", None)


def _scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Keep operational error metadata while stripping document/user payloads."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "cookies", "url", "query_string", "env", "fragment"):
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            # Allow only a non-sensitive content type; discard arbitrary headers.
            content_type = next(
                (value for key, value in headers.items() if key.lower() == "content-type"),
                None,
            )
            request["headers"] = {"Content-Type": content_type} if content_type else {}

    # Exception values frequently embed absolute document paths or filenames.
    exception = event.get("exception")
    if isinstance(exception, dict):
        values = exception.get("values")
        if isinstance(values, list):
            for value in values:
                if not isinstance(value, dict):
                    continue
                if "value" in value:
                    value["value"] = "[Filtered]"
                mechanism = value.get("mechanism")
                if isinstance(mechanism, dict):
                    mechanism.pop("data", None)
                _scrub_stacktrace(value.get("stacktrace"))

    threads = event.get("threads")
    if isinstance(threads, dict):
        values = threads.get("values")
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    _scrub_stacktrace(value.get("stacktrace"))

    # Log messages, transaction names, tags, and custom metadata can contain
    # user-supplied filenames or identifiers. Preserve level/logger/release only.
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        logentry.pop("message", None)
        logentry.pop("formatted", None)
        logentry.pop("params", None)
    for key in (
        "message", "transaction", "culprit", "tags", "user", "extra",
        "breadcrumbs", "contexts", "fingerprint", "modules",
    ):
        event.pop(key, None)

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
        logger.warning(f"Sentry initialization skipped: {type(exc).__name__}")
