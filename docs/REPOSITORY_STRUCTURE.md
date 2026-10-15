# Repository Structure — Doka AI DMS

> **Repository:** [logixaflow-commits/doka-ai-dms](https://github.com/logixaflow-commits/doka-ai-dms)  
> **Branch inspected:** `main`  
> **Generated:** 2026-10-15  
> **Inventory scope:** Git-tracked paths in the GitHub `main` tree, including hidden, archived, legacy, test, evidence, workflow, and documentation paths.

## What this document guarantees

The directory tree below is generated from GitHub's recursive Git tree API, not manually guessed. The API response used for the source inventory was not truncated. This document is included in the displayed tree as well.

- **Tracked file paths listed:** 704
- **Directories represented:** 87
- **Local ignored/untracked files:** Not included; GitHub's committed tree cannot show files that exist only on someone's computer.
- **Runtime or provider-side resources:** Not included unless represented by tracked repository files.

A path's presence proves that it exists in the inspected Git tree; it does not prove that it is currently imported, deployed, or used at runtime. Archived and legacy content is retained in this inventory for completeness.

## Complete repository tree

```text
doka-ai-dms/
├── .github/
│   ├── workflows/
│   │   ├── cloudflare-worker-deploy.yml
│   │   ├── codeql.yml
│   │   ├── dependency-review.yml
│   │   ├── doka-quality.yml
│   │   ├── historical-secret-scan.yml
│   │   ├── live-infra-smoke.yml
│   │   ├── local-core-check.yml
│   │   ├── myanmar-ocr-regression.yml
│   │   └── vercel-production.yml
│   └── dependabot.yml
├── archive/
│   ├── deployment-configs/
│   │   └── render.yaml
│   ├── legacy/
│   │   ├── phase0/
│   │   │   └── search_tuning.md
│   │   ├── AI_PROVIDER_MATRIX.md
│   │   ├── ARCHITECTURE.md
│   │   ├── cloud-storage-architecture-design.md
│   │   ├── cloud-storage-routing-plan.md
│   │   ├── CONTRIBUTING.md
│   │   ├── docs-SECURITY.md
│   │   ├── DOKA_AI_PRIVACY_AND_PROVIDER_DESIGN.md
│   │   ├── DOKA_CLOUD_API_CONTRACTS.md
│   │   ├── DOKA_CLOUD_DATA_MIGRATION.md
│   │   ├── DOKA_CLOUDFLARE_WORKERS_SETUP.md
│   │   ├── DOKA_DOCUMENTATION_INDEX.md
│   │   ├── DOKA_ENTERPRISE_RBAC_DESIGN.md
│   │   ├── DOKA_ENVIRONMENT_MATRIX.md
│   │   ├── DOKA_FASTAPI_CLOUD_DEPLOYMENT.md
│   │   ├── DOKA_FREE_CLOUD_ARCHITECTURE.md
│   │   ├── DOKA_GO_LIVE_CHECKLIST.md
│   │   ├── DOKA_OCR_BENCHMARK.md
│   │   ├── DOKA_PHASE_A_TO_E_STATUS.md
│   │   ├── DOKA_REMEDIATION_EXECUTION_LOG.md
│   │   ├── DOKA_SECRETS_AND_API_KEYS.md
│   │   ├── DOKA_SENTRY_AND_CLOUDFLARE_SETUP.md
│   │   ├── DOKA_STORAGE_MIGRATION_ROLLBACK.md
│   │   ├── DOKA_SUPABASE_SECURITY_REVIEW.md
│   │   ├── DOKA_UNIFIED_REMEDIATION_ROADMAP.md
│   │   ├── ENVIRONMENT_MATRIX.md
│   │   ├── EXTERNAL_SERVICE_INTEGRATION_MAP.md
│   │   ├── infrastructure-monitoring-README.md
│   │   ├── infrastructure-README.md
│   │   ├── MASTER_ROADMAP.md
│   │   ├── MASTER-ROADMAP.md
│   │   ├── mobile-README.md
│   │   ├── PERSONAL_LOCAL_RUNBOOK.md
│   │   ├── PHASE_A_AUDIT.md
│   │   ├── phase0_acceptance_report.md
│   │   ├── QUICKSTART.md
│   │   ├── README.md
│   │   ├── REPOSITORY_STRUCTURE.md
│   │   ├── SECURITY.md
│   │   ├── TOOLS.md
│   │   ├── UI.md
│   │   ├── web-platform-backend-LOCAL_TESTING_GUIDE.md
│   │   ├── web-platform-backend-README.md
│   │   ├── web-platform-backend-tests-README.md
│   │   ├── web-platform-docs-README.md
│   │   ├── web-platform-frontend-README.md
│   │   ├── web-platform-README.md
│   │   └── web-platform-tests-README.md
│   └── legacy-enterprise/
│       ├── backend/
│       │   ├── config.yaml
│       │   └── main_legacy.py
│       ├── frontend/
│       │   ├── core/
│       │   │   ├── config_validator.py
│       │   │   └── rate_limiter.py
│       │   ├── info.md
│       │   └── main.py
│       ├── root/
│       │   ├── pytest.ini
│       │   └── requirements.txt
│       ├── scripts/
│       │   ├── backup.py
│       │   ├── deploy.bat
│       │   ├── deploy.sh
│       │   ├── health-check.sh
│       │   ├── ingest_existing_social.py
│       │   ├── init_minio.py
│       │   ├── migrate_social_features.py
│       │   ├── production_backup.sh
│       │   ├── production_restore.sh
│       │   ├── quick-start.bat
│       │   ├── quick-start.sh
│       │   ├── README.md
│       │   ├── scan_secrets.sh
│       │   ├── setup.bat
│       │   └── setup.sh
│       └── README.md
├── cloudflare_worker/
│   ├── migrations/
│   │   ├── 0001_doka_cloud_baseline.sql
│   │   ├── 0002_authorization_integrity.sql
│   │   ├── 0003_job_tenant_integrity.sql
│   │   └── manifest.json
│   ├── shared/
│   │   ├── contracts/
│   │   │   └── cloud-document.schema.json
│   │   ├── __init__.py
│   │   └── storage_contracts.py
│   ├── turso_migrations/
│   │   └── 0001_sync_receipts.sql
│   ├── __init__.py
│   ├── b2_quota.py
│   ├── build.py
│   ├── d1.py
│   ├── jobs.py
│   ├── main.py
│   ├── outbox.py
│   ├── qstash.py
│   ├── storage_b2.py
│   ├── storage_cloudinary.py
│   ├── storage_contracts_compat.py
│   ├── storage_google_drive.py
│   ├── storage_router.py
│   ├── storage_runtime.py
│   ├── storage_supabase.py
│   └── stream_hash.py
├── docs/
│   ├── legacy/
│   │   ├── root/
│   │   │   ├── AI_INTEGRATION_GUIDE.md
│   │   │   ├── API_DOCUMENTATION.md
│   │   │   ├── APPLICATION_STARTUP_GUIDE.md
│   │   │   ├── BACKEND_DOCUMENTATION.md
│   │   │   ├── commit_message.txt
│   │   │   ├── COMPLETE_CODEBASE.md
│   │   │   ├── COMPLETE_FEATURE_IMPLEMENTATION_PLAN.md
│   │   │   ├── COMPLETE_SYSTEM_BUNDLE.md
│   │   │   ├── COMPLETE_SYSTEM_SUMMARY.md
│   │   │   ├── DEPLOYMENT_GUIDE.md
│   │   │   ├── ENTERPRISE_DMS_COMPLETE.md
│   │   │   ├── FINAL_COMPLETE_SUMMARY.md
│   │   │   ├── FINAL_IMPLEMENTATION_SUMMARY.md
│   │   │   ├── FINAL_VERIFICATION_CHECKLIST.md
│   │   │   ├── FRONTEND_DOCUMENTATION.md
│   │   │   ├── FUNCTION_FRACTURE_DETECTION_SUMMARY.md
│   │   │   ├── GITHUB_SETUP_GUIDE.md
│   │   │   ├── HARDENING_SUMMARY.md
│   │   │   ├── NEXT_STEPS.md
│   │   │   ├── PRODUCTION_SETUP_GUIDE.md
│   │   │   ├── PRODUCTION_SUMMARY.md
│   │   │   ├── README_PUSH.md
│   │   │   ├── README.md
│   │   │   ├── SOCIAL_MEDIA_UPGRADE.md
│   │   │   └── VERIFICATION.md
│   │   ├── ci-cd.yml.disabled
│   │   ├── DOKA_MASTER_PRODUCT_PLAN.md
│   │   └── PERSONAL_LOCAL_MASTER_PLAN.md
│   ├── Report/
│   │   ├── branch-cleanup-audit-2026-10-11.md
│   │   ├── browser-sample-acceptance.json
│   │   ├── cloudflare-worker-deployment-dry-run-2026-10-13.md
│   │   ├── final-local-verification-report-2026-10-13.md
│   │   ├── google-drive-checksum-verification-2026-10-13.md
│   │   ├── local-ocr-comparison.md
│   │   ├── ocr-benchmark-acceptance.md
│   │   ├── ocr-benchmark.json
│   │   ├── personal-local-acceptance-report.md
│   │   ├── personal-local-acceptance.json
│   │   ├── personal-local-current-run.json
│   │   ├── pilot-acceptance-20261013.json
│   │   ├── pilot-acceptance-sym300.json
│   │   ├── pilot-recovery.json
│   │   ├── preflight.json
│   │   ├── small-sample-browser-acceptance.json
│   │   ├── small-sample-pilot.json
│   │   ├── train1-local-readiness.md
│   │   └── train1-verification.md
│   ├── AI_CONSENT.md
│   ├── AI_RAG.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPMENT.md
│   ├── DOKA_STORAGE_MIGRATION_ROLLBACK.md
│   ├── master_result all
│   ├── OPERATIONS.md
│   ├── OWNER_LOCAL_CHECKLIST.md
│   ├── PERSONAL_LOCAL_GUIDE.md
│   ├── PHASE_7_18_EXECUTION_PLAN.md
│   ├── PHASE_TRAIN_STATUS.md
│   ├── REPOSITORY_INFRA_AUDIT_2026-10-15.md
│   ├── REPOSITORY_STRUCTURE.md
│   ├── RUNTIME_EVIDENCE.md
│   ├── SELF_AUDIT.md
│   ├── STORAGE.md
│   ├── TELEGRAM_INTEGRATION.md
│   ├── TESTING.md
│   └── TROUBLESHOOTING.md
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.production.yml
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── Dockerfile.railway
│   ├── env/
│   │   └── .env.docker
│   ├── monitoring/
│   │   ├── grafana/
│   │   │   ├── dashboards/
│   │   │   │   ├── dms-document-processing.json
│   │   │   │   ├── dms-overview.json
│   │   │   │   └── dms-system-monitoring.json
│   │   │   └── provisioning/
│   │   │       ├── dashboards/
│   │   │       │   └── dashboard.yml
│   │   │       └── datasources/
│   │   │           └── prometheus.yml
│   │   ├── prometheus/
│   │   │   └── prometheus.yml
│   │   └── docker-compose.monitoring.yml
│   ├── nginx/
│   │   └── nginx.conf
│   └── railway/
│       ├── railway.env
│       ├── railway.toml
│       └── start_railway.py
├── mobile/
│   ├── src/
│   │   ├── context/
│   │   │   ├── ApiContext.js
│   │   │   └── AuthContext.js
│   │   ├── screens/
│   │   │   ├── DashboardScreen.js
│   │   │   ├── DocumentDetailScreen.js
│   │   │   ├── DocumentsScreen.js
│   │   │   ├── LoginScreen.js
│   │   │   ├── ProfileScreen.js
│   │   │   └── UploadScreen.js
│   │   └── utils/
│   │       ├── appConfig.test.cjs
│   │       ├── uploadFile.cjs
│   │       └── uploadFile.test.cjs
│   ├── App.js
│   ├── app.json
│   ├── babel.config.js
│   └── package.json
├── Phase0_Evidence/
│   ├── acceptance/
│   │   └── personal-local-browser-smoke-2026-10-09.json
│   ├── cloud/
│   │   └── acceptance-manifest.example.json
│   ├── ocr_benchmark/
│   │   └── manifest.example.json
│   ├── train1/
│   │   ├── d1-authorization-migration-2026-10-09.json
│   │   └── d1-job-runtime.json
│   ├── acceptance_preflight.json
│   ├── DokaOcrReport.json
│   └── pl_g19_status.txt
├── scripts/
│   ├── audit/
│   │   ├── doka_self_audit.py
│   │   └── test_doka_self_audit.py
│   ├── acceptance_preflight.py
│   ├── cloud_acceptance.py
│   ├── cloud_provider_acceptance.py
│   ├── d1_job_runtime_acceptance.py
│   ├── doka_pilot_check.py
│   ├── export_cloud_openapi.py
│   ├── local_acceptance_preflight.py
│   ├── ocr_benchmark.py
│   ├── prepare_cloud_acceptance_fixture.py
│   ├── release_gate_check.py
│   ├── run_personal_local_acceptance.bat
│   ├── run_personal_local_acceptance.sh
│   ├── run-cloud-isolation-acceptance.ps1
│   ├── run-cloud-provider-acceptance.ps1
│   ├── test_search.py
│   └── verify_d1_migrations.py
├── supabase/
│   └── migrations/
│       ├── 20261001075215_doka_documents.sql
│       ├── 20261001075218_doka_storage_policies.sql
│       ├── 20261001075238_doka_rls_performance_hardening.sql
│       ├── 20261001075547_doka_column_privileges.sql
│       ├── 20261001100118_doka_least_privilege_grants.sql
│       ├── 20261001100500_doka_storage_no_overwrite_policy.sql
│       ├── 20261002064722_grant_doka_document_status_updates.sql
│       ├── 20261002080356_doka_cloud_library_lifecycle.sql
│       ├── 20261002081219_doka_folder_path_validation.sql
│       ├── 20261002090857_doka_permanent_delete.sql
│       ├── 20261002091404_doka_audit_events.sql
│       ├── 20261002091601_doka_audit_preview.sql
│       ├── 20261002092642_doka_document_versions.sql
│       ├── 20261002092707_doka_document_version_functions.sql
│       ├── 20261002093715_doka_atomic_bulk_actions.sql
│       ├── 20261002093843_doka_bulk_action_null_guard.sql
│       ├── 20261002095029_doka_bulk_updated_at_trigger.sql
│       ├── 20261002095530_doka_harden_version_rpc_guards.sql
│       ├── 20261002100306_doka_version_rpc_validation.sql
│       ├── 20261002100427_doka_version_rpc_final_hardening.sql
│       ├── 20261002100658_doka_version_object_key_pattern.sql
│       ├── 20261002114801_doka_audit_least_privilege.sql
│       ├── 20261002115107_doka_version_history_append_only.sql
│       ├── 20261005090000_doka_version_rpc_execute_hardening.sql
│       ├── 20261005112032_doka_version_rpc_invoker_recreate.sql
│       ├── 20261005112100_doka_storage_version_rpc.sql
│       ├── 20261005113151_doka_storage_provider_metadata.sql
│       ├── 20261005113241_doka_audit_export_backup_actions.sql
│       └── 20261009083942_doka_trigger_function_least_privilege.sql
├── web-platform/
│   ├── backend/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   │   └── 0001_doka_baseline.py
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── admin_activity.py
│   │   │   │   │   ├── admin.py
│   │   │   │   │   ├── ai_consent.py
│   │   │   │   │   ├── analytics.py
│   │   │   │   │   ├── audit.py
│   │   │   │   │   ├── auth_2fa.py
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── cloud_documents.py
│   │   │   │   │   ├── cloud_storage.py
│   │   │   │   │   ├── documents.py
│   │   │   │   │   ├── integrations.py
│   │   │   │   │   ├── local_auth.py
│   │   │   │   │   ├── monitoring.py
│   │   │   │   │   ├── permissions.py
│   │   │   │   │   ├── realtime.py
│   │   │   │   │   ├── reminders.py
│   │   │   │   │   ├── reports.py
│   │   │   │   │   ├── rules.py
│   │   │   │   │   ├── search.py
│   │   │   │   │   ├── settings.py
│   │   │   │   │   ├── sop.py
│   │   │   │   │   ├── tags.py
│   │   │   │   │   ├── telegram.py
│   │   │   │   │   ├── templates.py
│   │   │   │   │   ├── versions.py
│   │   │   │   │   ├── workspace_files.py
│   │   │   │   │   └── workspace.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py
│   │   │   │   └── webhooks.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_boundary.py
│   │   │   │   ├── backup_utils.py
│   │   │   │   ├── celery_app.py
│   │   │   │   ├── config_production.py
│   │   │   │   ├── config_validator.py
│   │   │   │   ├── config.py
│   │   │   │   ├── database.py
│   │   │   │   ├── encryption.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── file_safety.py
│   │   │   │   ├── local_security.py
│   │   │   │   ├── logging.py
│   │   │   │   ├── observability.py
│   │   │   │   ├── passwords.py
│   │   │   │   ├── performance.py
│   │   │   │   ├── prometheus_metrics.py
│   │   │   │   ├── rate_limiter.py
│   │   │   │   ├── redis_client.py
│   │   │   │   ├── security_production.py
│   │   │   │   ├── security.py
│   │   │   │   ├── storage.py
│   │   │   │   ├── supabase_auth.py
│   │   │   │   └── tasks.py
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── audit.py
│   │   │   │   ├── error_handler.py
│   │   │   │   ├── permission_middleware.py
│   │   │   │   └── rule_trigger_middleware.py
│   │   │   ├── routes/
│   │   │   │   ├── advanced_reports.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── document_versions.py
│   │   │   │   ├── external_integrations.py
│   │   │   │   ├── preview.py
│   │   │   │   ├── rate_limiting.py
│   │   │   │   └── realtime_updates.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── advanced_reporting.py
│   │   │   │   ├── advanced_search.py
│   │   │   │   ├── ai_duplicate_detector.py
│   │   │   │   ├── ai_tagging_service.py
│   │   │   │   ├── ai_usage_tracker.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── classifier.py
│   │   │   │   ├── cloud_documents.py
│   │   │   │   ├── cloud_storage.py
│   │   │   │   ├── consent_store.py
│   │   │   │   ├── document_preview.py
│   │   │   │   ├── document_understanding_service.py
│   │   │   │   ├── document_versioning.py
│   │   │   │   ├── duplicate_detector.py
│   │   │   │   ├── email_service_production.py
│   │   │   │   ├── email_service.py
│   │   │   │   ├── external_api_service.py
│   │   │   │   ├── external_integrations.py
│   │   │   │   ├── function_detection.py
│   │   │   │   ├── job_idempotency.py
│   │   │   │   ├── metadata_extractor.py
│   │   │   │   ├── monitoring_service.py
│   │   │   │   ├── myanmar_ocr.py
│   │   │   │   ├── ocr_benchmark.py
│   │   │   │   ├── ocr_comparison.py
│   │   │   │   ├── ocr_service.py
│   │   │   │   ├── ocr_validation_service.py
│   │   │   │   ├── organization_planner.py
│   │   │   │   ├── permission_service.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── pwa_service.py
│   │   │   │   ├── rate_limiting.py
│   │   │   │   ├── realtime_service.py
│   │   │   │   ├── report_service.py
│   │   │   │   ├── rule_engine.py
│   │   │   │   ├── rule_manager.py
│   │   │   │   ├── safe_workspace_service.py
│   │   │   │   ├── shipping_integration.py
│   │   │   │   ├── social_ingestor.py
│   │   │   │   ├── storage_mock.py
│   │   │   │   ├── storage_router.py
│   │   │   │   ├── telegram.py
│   │   │   │   ├── template_library.py
│   │   │   │   ├── totp_service.py
│   │   │   │   ├── train1_safety_contracts.py
│   │   │   │   ├── unified_ai_service.py
│   │   │   │   ├── vector_search.py
│   │   │   │   ├── version_service.py
│   │   │   │   ├── watcher.py
│   │   │   │   ├── workflow_automation.py
│   │   │   │   └── workspace_backup_service.py
│   │   │   ├── static/
│   │   │   │   ├── js/
│   │   │   │   │   ├── 2fa.js
│   │   │   │   │   ├── dashboard.js
│   │   │   │   │   ├── fetch_helper.js
│   │   │   │   │   ├── permissions.js
│   │   │   │   │   └── reports.js
│   │   │   │   ├── manifest.json
│   │   │   │   ├── offline.html
│   │   │   │   └── sw.js
│   │   │   ├── templates/
│   │   │   │   ├── 2fa_verify.html
│   │   │   │   ├── admin_activity.html
│   │   │   │   ├── admin_folder_permissions.html
│   │   │   │   ├── audit.html
│   │   │   │   ├── base.html
│   │   │   │   ├── dashboard.html
│   │   │   │   ├── document_detail.html
│   │   │   │   ├── index.html
│   │   │   │   ├── login.html
│   │   │   │   ├── pending.html
│   │   │   │   ├── reminders.html
│   │   │   │   ├── reports.html
│   │   │   │   ├── search.html
│   │   │   │   ├── settings_sources.html
│   │   │   │   ├── settings.html
│   │   │   │   └── sop.html
│   │   │   ├── cloud_main.py
│   │   │   └── main.py
│   │   ├── migrations/
│   │   │   └── add_function_fracture_detection.py
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   ├── backup.py
│   │   │   ├── init_minio.py
│   │   │   ├── migrate_bcrypt_v2.py
│   │   │   ├── migrate_expiry_columns.py
│   │   │   ├── migrate_phase2.py
│   │   │   ├── migrate_phase3.py
│   │   │   ├── migrate_phase4.py
│   │   │   └── wait_for_services.sh
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── custom.css
│   │   │   └── js/
│   │   │       └── utils.js
│   │   ├── tessdata/
│   │   │   ├── eng.traineddata
│   │   │   └── mya.traineddata
│   │   ├── tests/
│   │   │   ├── integration/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── conftest.py
│   │   │   │   ├── test_auth_bcrypt.py
│   │   │   │   └── test_db_auth.py
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_ai_consent_routes.py
│   │   │   ├── test_ai_provider_boundaries.py
│   │   │   ├── test_api_integration.py
│   │   │   ├── test_classifier.py
│   │   │   ├── test_consent_store.py
│   │   │   ├── test_e2e.py
│   │   │   ├── test_h1_local_auth_boundary.py
│   │   │   ├── test_h2_source_containment.py
│   │   │   ├── test_h3_unicode_passwords.py
│   │   │   ├── test_hardening.py
│   │   │   ├── test_health_check.py
│   │   │   ├── test_job_idempotency.py
│   │   │   ├── test_local_acceptance_preflight.py
│   │   │   ├── test_myanmar_ocr_postprocessing.py
│   │   │   ├── test_ocr_benchmark.py
│   │   │   ├── test_ocr_comparison.py
│   │   │   ├── test_ocr_safety_limits.py
│   │   │   ├── test_phase0_foundation.py
│   │   │   ├── test_security_regressions.py
│   │   │   ├── test_security.py
│   │   │   ├── test_services.py
│   │   │   ├── test_storage_providers.py
│   │   │   ├── test_symlink_safety.py
│   │   │   ├── test_train1_safety_contracts.py
│   │   │   ├── test_workflow_automation.py
│   │   │   ├── test_workspace_backup_boundaries.py
│   │   │   └── test_workspace_backup_routes.py
│   │   ├── .dockerignore
│   │   ├── .env.example
│   │   ├── .gitignore
│   │   ├── alembic.ini
│   │   ├── check_endpoints.py
│   │   ├── config.yaml
│   │   ├── create_admin_simple.py
│   │   ├── create_admin.py
│   │   ├── Dockerfile
│   │   ├── Dockerfile.production
│   │   ├── fix_admin_email.py
│   │   ├── pytest.ini
│   │   ├── quick_test.bat
│   │   ├── recreate_admin.py
│   │   ├── requirements-cloud.txt
│   │   ├── requirements-dev.txt
│   │   ├── requirements-local.txt
│   │   ├── requirements-production.txt
│   │   ├── requirements-test.txt
│   │   ├── requirements.txt
│   │   ├── run_tests.bat
│   │   ├── run_tests.ps1
│   │   ├── run.bat
│   │   ├── run.py
│   │   ├── run.sh
│   │   ├── test_admin_api.py
│   │   ├── test_api.py
│   │   └── update_password.py
│   ├── frontend/
│   │   ├── e2e/
│   │   │   └── personal-local.spec.ts
│   │   ├── public/
│   │   │   ├── manifest.json
│   │   │   └── sw.js
│   │   ├── scripts/
│   │   │   └── smoke-test.mjs
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ui/
│   │   │   │   │   ├── accordion.tsx
│   │   │   │   │   ├── alert-dialog.tsx
│   │   │   │   │   ├── alert.tsx
│   │   │   │   │   ├── aspect-ratio.tsx
│   │   │   │   │   ├── avatar.tsx
│   │   │   │   │   ├── badge.tsx
│   │   │   │   │   ├── breadcrumb.tsx
│   │   │   │   │   ├── button-group.tsx
│   │   │   │   │   ├── button.tsx
│   │   │   │   │   ├── calendar.tsx
│   │   │   │   │   ├── card.tsx
│   │   │   │   │   ├── carousel.tsx
│   │   │   │   │   ├── chart.tsx
│   │   │   │   │   ├── checkbox.tsx
│   │   │   │   │   ├── collapsible.tsx
│   │   │   │   │   ├── command.tsx
│   │   │   │   │   ├── context-menu.tsx
│   │   │   │   │   ├── dialog.tsx
│   │   │   │   │   ├── drawer.tsx
│   │   │   │   │   ├── dropdown-menu.tsx
│   │   │   │   │   ├── empty.tsx
│   │   │   │   │   ├── field.tsx
│   │   │   │   │   ├── form.tsx
│   │   │   │   │   ├── hover-card.tsx
│   │   │   │   │   ├── input-group.tsx
│   │   │   │   │   ├── input-otp.tsx
│   │   │   │   │   ├── input.tsx
│   │   │   │   │   ├── item.tsx
│   │   │   │   │   ├── kbd.tsx
│   │   │   │   │   ├── label.tsx
│   │   │   │   │   ├── menubar.tsx
│   │   │   │   │   ├── navigation-menu.tsx
│   │   │   │   │   ├── pagination.tsx
│   │   │   │   │   ├── popover.tsx
│   │   │   │   │   ├── progress.tsx
│   │   │   │   │   ├── radio-group.tsx
│   │   │   │   │   ├── resizable.tsx
│   │   │   │   │   ├── scroll-area.tsx
│   │   │   │   │   ├── select.tsx
│   │   │   │   │   ├── separator.tsx
│   │   │   │   │   ├── sheet.tsx
│   │   │   │   │   ├── sidebar.tsx
│   │   │   │   │   ├── skeleton.tsx
│   │   │   │   │   ├── slider.tsx
│   │   │   │   │   ├── sonner.tsx
│   │   │   │   │   ├── spinner.tsx
│   │   │   │   │   ├── switch.tsx
│   │   │   │   │   ├── table.tsx
│   │   │   │   │   ├── tabs.tsx
│   │   │   │   │   ├── textarea.tsx
│   │   │   │   │   ├── toggle-group.tsx
│   │   │   │   │   ├── toggle.tsx
│   │   │   │   │   └── tooltip.tsx
│   │   │   │   ├── Accessibility.tsx
│   │   │   │   ├── ActivityTimeline.tsx
│   │   │   │   ├── AdvancedSearch.tsx
│   │   │   │   ├── AITagging.tsx
│   │   │   │   ├── AnalyticsCharts.tsx
│   │   │   │   ├── AuditTrailViewer.tsx
│   │   │   │   ├── Breadcrumb.tsx
│   │   │   │   ├── CommentsSystem.tsx
│   │   │   │   ├── DocumentAnalysis.tsx
│   │   │   │   ├── DocumentExport.tsx
│   │   │   │   ├── DocumentPreview.tsx
│   │   │   │   ├── DocumentSharing.tsx
│   │   │   │   ├── DocumentUpload.tsx
│   │   │   │   ├── DocumentVersioning.tsx
│   │   │   │   ├── ErrorBoundary.tsx
│   │   │   │   ├── ExternalIntegrations.tsx
│   │   │   │   ├── FolderPermissions.tsx
│   │   │   │   ├── ForgotPassword.tsx
│   │   │   │   ├── FormValidation.tsx
│   │   │   │   ├── Login.tsx
│   │   │   │   ├── MonitoringDashboard.tsx
│   │   │   │   ├── NotificationCenter.tsx
│   │   │   │   ├── RulesEngine.tsx
│   │   │   │   ├── SemanticSearch.tsx
│   │   │   │   ├── SkeletonLoader.tsx
│   │   │   │   ├── StorageUsageStatistics.tsx
│   │   │   │   ├── TemplateLibrary.tsx
│   │   │   │   ├── ThemeToggle.tsx
│   │   │   │   ├── Toast.tsx
│   │   │   │   ├── TwoFactorAuth.tsx
│   │   │   │   ├── UserActivityAnalytics.tsx
│   │   │   │   └── VersionHistory.tsx
│   │   │   ├── contexts/
│   │   │   │   └── ThemeContext.tsx
│   │   │   ├── hooks/
│   │   │   │   └── use-mobile.ts
│   │   │   ├── layouts/
│   │   │   │   └── AdminLayout.tsx
│   │   │   ├── lib/
│   │   │   │   ├── cloudDocuments.ts
│   │   │   │   ├── localAuth.ts
│   │   │   │   ├── sentry.ts
│   │   │   │   ├── supabaseAuth.ts
│   │   │   │   └── utils.ts
│   │   │   ├── pages/
│   │   │   │   ├── admin/
│   │   │   │   │   ├── AITagging.tsx
│   │   │   │   │   ├── Analytics.tsx
│   │   │   │   │   ├── Audit.tsx
│   │   │   │   │   ├── Dashboard.tsx
│   │   │   │   │   ├── Documents.tsx
│   │   │   │   │   ├── index.ts
│   │   │   │   │   ├── Integrations.tsx
│   │   │   │   │   ├── Monitoring.tsx
│   │   │   │   │   ├── Permissions.tsx
│   │   │   │   │   ├── Rules.tsx
│   │   │   │   │   ├── SemanticSearch.tsx
│   │   │   │   │   ├── Settings.tsx
│   │   │   │   │   ├── Templates.tsx
│   │   │   │   │   ├── Users.tsx
│   │   │   │   │   └── Versioning.tsx
│   │   │   │   ├── AiUsage.tsx
│   │   │   │   ├── CloudAudit.tsx
│   │   │   │   ├── CloudDocuments.tsx
│   │   │   │   ├── DocumentDetail.tsx
│   │   │   │   ├── Documents.tsx
│   │   │   │   ├── DocumentUpload.tsx
│   │   │   │   ├── Home.tsx
│   │   │   │   ├── PersonalDashboard.tsx
│   │   │   │   ├── UserProfile.tsx
│   │   │   │   └── WorkspaceReview.tsx
│   │   │   ├── types/
│   │   │   │   └── database.types.ts
│   │   │   ├── App.css
│   │   │   ├── App.tsx
│   │   │   ├── index.css
│   │   │   └── main.tsx
│   │   ├── static/
│   │   │   └── js/
│   │   │       └── fetch_helper.js
│   │   ├── test-results/
│   │   │   ├── .last-run.json
│   │   │   └── browser-acceptance-report.json
│   │   ├── .env.example
│   │   ├── .gitignore
│   │   ├── components.json
│   │   ├── eslint.config.js
│   │   ├── index.html
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   ├── playwright.config.ts
│   │   ├── postcss.config.js
│   │   ├── tailwind.config.js
│   │   ├── tsconfig.app.json
│   │   ├── tsconfig.json
│   │   ├── tsconfig.node.json
│   │   └── vite.config.ts
│   └── tests/
│       ├── conftest.py
│       ├── test_backup_utils.py
│       ├── test_cloud_acceptance.py
│       ├── test_cloud_api_entrypoint.py
│       ├── test_cloud_documents_cleanup.py
│       ├── test_cloud_documents_http.py
│       ├── test_cloud_storage_http.py
│       ├── test_cloud_storage_routing.py
│       ├── test_cloud_storage.py
│       ├── test_cloudflare_authorization_schema.py
│       ├── test_cloudflare_b2_quota.py
│       ├── test_cloudflare_b2_storage.py
│       ├── test_cloudflare_cloudinary_guard.py
│       ├── test_cloudflare_d1_adapter.py
│       ├── test_cloudflare_d1_schema.py
│       ├── test_cloudflare_google_drive.py
│       ├── test_cloudflare_jobs.py
│       ├── test_cloudflare_outbox.py
│       ├── test_cloudflare_qstash.py
│       ├── test_cloudflare_storage_direct_upload.py
│       ├── test_cloudflare_storage_router.py
│       ├── test_cloudflare_streaming_hash.py
│       ├── test_cloudflare_worker_bundle_imports.py
│       ├── test_cloudflare_worker_contract.py
│       ├── test_config_environment.py
│       ├── test_cors_config.py
│       ├── test_d1_migrations.py
│       ├── test_document_understanding.py
│       ├── test_document_versioning_safety.py
│       ├── test_doka_pilot.py
│       ├── test_doka_storage_metadata_migration.py
│       ├── test_doka_version_rpc_migration.py
│       ├── test_hardening.py
│       ├── test_local_auth_state_permissions.py
│       ├── test_local_auth.py
│       ├── test_observability.py
│       ├── test_ocr_benchmark.py
│       ├── test_ocr_input_safety.py
│       ├── test_ocr_resource_limits.py
│       ├── test_organization_planner.py
│       ├── test_personal_local_entrypoint.py
│       ├── test_release_gate_check.py
│       ├── test_safe_workspace_service.py
│       ├── test_security_production.py
│       ├── test_unified_ai_fallback.py
│       ├── test_vector_search_ocr.py
│       ├── test_workspace_backup_safety.py
│       ├── test_workspace_backup_service.py
│       ├── test_workspace_import_route.py
│       └── test_workspace_security.py
├── .dockerignore
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml
├── backup-doka.bat
├── CURRENT_STATE.md
├── LICENSE
├── PROJECT_OVERVIEW.md
├── pyproject.toml
├── README.md
├── ROADMAP.md
├── run.bat
├── run.sh
├── SECURITY.md
├── start_application.bat
├── start_backend.bat
├── start_frontend.bat
├── start-doka.bat
├── stop-doka.bat
├── storage_contracts_compat.py
├── TOOL.md
├── UI_DESIGN_SYSTEM.md
├── uv.lock
└── wrangler.jsonc
```

## Updating this inventory

Refresh this file after any path addition, deletion, rename, or move. Regenerate the recursive tree from the target branch rather than editing the listing by hand. Include hidden files and all tracked subdirectories; do not filter by extension or assume that archived, test, evidence, or generated-but-tracked paths are irrelevant. The document's own path should remain in the tree.
