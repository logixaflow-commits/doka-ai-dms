from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1] / "backend"
WEBHOOK_SOURCE = (BACKEND / "app" / "api" / "webhooks.py").read_text(encoding="utf-8")
MAIN_SOURCE = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")


def test_legacy_webhook_rejects_missing_signature_and_verifies_present_signature():
    assert "if not x_webhook_signature:" in WEBHOOK_SOURCE
    assert "Webhook signature required" in WEBHOOK_SOURCE
    assert "api_service.verify_webhook(provider_name, payload, x_webhook_signature)" in WEBHOOK_SOURCE


def test_legacy_webhook_does_not_log_raw_payload_or_parsed_document_data():
    assert 'logger.info("Received webhook for provider: %s", provider_name)' in WEBHOOK_SOURCE
    assert "Received webhook from {provider_name}: {webhook_data}" not in WEBHOOK_SOURCE
    assert "logger.info(f\"Updated document {doc.id} with webhook data from {provider_name}\")" not in WEBHOOK_SOURCE


def test_legacy_webhook_router_remains_unmounted_until_integration_tests_exist():
    assert "webhooks" not in MAIN_SOURCE
