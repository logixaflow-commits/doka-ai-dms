# Train 1 + Personal Local — execution handoff

**Status:** preparation checklist, not release approval. Reconciled 2026-10-12. Train 1 runtime evidence and Personal Local release gates are separate.

## 1. Remaining work

### Train 1
- [x] D1 job idempotency hardened: malformed IDs rejected, cross-organization idempotency replay prevented, and durable job creation fails closed unless a non-empty, canonical organization ID is supplied. Job type and idempotency key must be strings without ambiguous surrounding whitespace.
- [ ] The required organization ID must come from verified authentication/authorization context at the future handler boundary; this primitive validation is not itself proof of tenant authorization.
- [x] Exact-HEAD CI for 8a700a083dd049acd9b98fdb00614d40fdca8c4a: Doka Quality Checks #939, Dependency Review #82, CodeQL #320 passed; Cloud storage contracts reported 117 passed.
- [x] Consent checks, retry taxonomy, DLQ/outbox primitives, circuit breaker/failover controls, strict structured output, and OCR-aware retrieval have implementation/contract-test coverage.
- [ ] **Job consumer:** define supported job types, authenticated tenant/organization ownership, concrete handlers, and terminal-result contract; connect Worker entrypoint/consumer. Test duplicate delivery, lease expiry/fencing, bounded retries, exhaustion/DLQ, and recovery end to end.
- [ ] **Queue delivery:** provision QStash credentials and a verified callback URL in non-production; test signature validation, replay/duplicate handling, retries, and completion. Never place secrets in Git, logs, chat, or evidence.
- [ ] **Real consent boundary:** prove callers derive subject identity from verified authentication and resource scope from authorized document context; test grant/revoke at the actual provider-call route. Keep Personal Local document understanding local-only by default.
- [ ] **Provider runtime:** with explicit test purpose and approved free/allowlisted provider configuration, test timeouts, retryable/permanent failures, circuit transitions, and failover. Keep AI disabled if consent/configuration is absent.
- [ ] **Myanmar/English OCR:** visually resolve ground-truth uncertainty, including 11 Plavix and 5 cool-storage lines below 95% source alignment; improve failing samples without relaxing thresholds, then rerun.
- [ ] Record exact tested SHA and runtime evidence. Do not claim Train 1 complete until runtime gates pass.

### Personal Local
- [ ] **Gate 3 OCR:** current expanded report is FAIL. mya mean CER/WER = 0.1200/0.3056; mya+eng = 0.3379/0.5342; three samples fail strict per-sample limits. Do not lower thresholds.
- [ ] **Gate 4 browser:** repeat E2E with representative copied office data, not only synthetic text; cover error/restart paths and record tested commit.
- [ ] **Gate 5 pilot:** import → OCR/understand → review → human approval → final-copy/apply using a COPY of office data. Verify source hashes unchanged and source/workspace/backup/evidence paths disjoint.
- [ ] **Gate 6 recovery:** timed backup + isolated restore/undo on the real local machine; record durations and agree explicit RTO/RPO targets.
- [ ] **Gate 8 freeze:** sign off exact candidate only after Gates 1–7 evidence is accepted.
- [ ] Cloud gates are separate: Gate 9 needs two disposable authenticated users/tokens and exact 50 MiB lifecycle tests; Gate 10 real A/B isolation proof; Gate 11 application-path B2/Drive/provider recovery; Gate 12 remains blocked while production is intentionally paused and until explicit owner approval plus final acceptance.

## 2. Local prerequisites

- [ ] Clean checkout of intended branch/commit; clean working tree; exact-HEAD CI green.
- [ ] Python 3.13, isolated virtual environment, and backend requirements-local.txt + requirements-test.txt installed.
- [ ] Node.js 24.x and npm; run npm ci in web-platform/frontend.
- [ ] Tesseract OCR 5.5.3.20260724 (or record actual version) with both eng and mya language packs; verify PDF/OCR tooling is callable.
- [ ] Privacy-approved COPY of representative office files and separate OCR sample directory with a verified manifest. Include Myanmar-only, English-only, mixed-script, scanned PDF/image, and relevant office formats. Keep source documents and raw OCR/reference text out of Git and chat.
- [ ] Dedicated, empty, non-overlapping paths for source copy, workspace, backup, OCR samples, and evidence. Never pilot against original office files.
- [ ] Temporary strong BOOTSTRAP_ADMIN_PASSWORD and generated SECRET_KEY stored locally only.
- [ ] Local web-platform/backend/.env based on .env.example. For initial local run verify AI_ENABLED=false, AI_EXTERNAL_PROCESSING_CONSENT=false, DOKA_STORAGE_PROVIDER=disabled, ORIGINAL_READ_ONLY=true, ALLOW_SOURCE_WRITE=false. Leave cloud/provider credentials blank unless a separately approved test needs them.
- [ ] Sufficient disk space for copies, OCR renders, workspace, backups, and browser artifacts. Store private evidence outside source/workspace paths.

## 3. Local preparation commands (PowerShell, from repository root)

Do not run the full acceptance script until all paths point to a dedicated COPY and workspace/backup roots are empty.

    git status --short --branch
    git rev-parse HEAD
    python --version
    node --version
    npm --version
    tesseract --version
    tesseract --list-langs

    py -3.13 -m venv web-platform/backend/.venv
    web-platform/backend/.venv/Scripts/python.exe -m pip install --upgrade pip
    web-platform/backend/.venv/Scripts/python.exe -m pip install -r web-platform/backend/requirements-local.txt -r web-platform/backend/requirements-test.txt

    Set-Location web-platform/frontend
    npm ci
    npm run build
    npm run lint
    npm test
    Set-Location ../..

Confirm tesseract --list-langs includes eng and mya. Missing either language is a stop condition, not a warning to ignore.

### OCR benchmark first

Use the private, verified manifest and sample images; these paths are examples only. Keep JSON output private and outside the samples directory.

    $env:OCR_TIMEOUT_SECONDS = '120'
    web-platform/backend/.venv/Scripts/python.exe scripts/ocr_benchmark.py --root 'D:\DokaPilotCopy\ocr-samples' --manifest 'D:\DokaPilotCopy\manifest.verified-private.json' --output 'D:\DokaEvidence\train1-ocr.json'

Exit code 0 means the OCR gate passed; exit code 2 means quality failure. Preserve failure evidence and investigate references/recognition without lowering thresholds.

### Fail-closed preflight and full local acceptance

Before installing dependencies or processing any sample, both acceptance runners invoke `scripts/local_acceptance_preflight.py`. It checks the required paths and manifest, rejects symlinks/path overlap/non-empty workspace or backup roots, requires Python 3.13, Node 24.x, and Tesseract with both `eng` and `mya`, and verifies the initial run stays AI-disabled and source-read-only. The JSON report records readiness flags only, not paths, secrets, or OCR text.

The runner requires `DOKA_PILOT_SOURCE`, `DOKA_PILOT_WORKSPACE`, `DOKA_PILOT_BACKUPS`, `DOKA_OCR_ROOT`, `DOKA_OCR_MANIFEST`, and `BOOTSTRAP_ADMIN_PASSWORD` (at least 16 characters). It runs OCR, copied-office pilot/recovery, frontend build, local services, and Playwright E2E. A preflight exit code of 2 is a stop condition: fix the reported prerequisites rather than bypassing the check. Read the runner first and never use original office files.

## 4. Who must supply what

**Repository/CI:** consumer/handler implementation after job types and tenant identity are specified; tests, local preflight/docs, contract tests, static checks, exact-HEAD CI.

**Real local machine / authorized owner:** Tesseract and language data; representative privacy-approved documents and verified references; copied-office pilot; realistic browser run; measured RTO/RPO; local admin password; disposable cloud test users; QStash/provider credentials and callback configuration; final security/release sign-off.

No production data, production queue, secrets, or live deployment should be changed during local preparation.