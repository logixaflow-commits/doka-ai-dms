# TEST_RUNBOOK.md

Commands are local/CI only; no deploys or infrastructure changes.

## Frontend

~~~powershell
cd apps/web-platform/frontend
npm ci --no-audit --no-fund
npm run test:unit
npm run build
npm run lint
npm test
~~~

Expected: npm ci succeeds with Node 24.x; 7 Vitest tests pass, including the 100 MiB mock test with a maximum 8 MiB chunk-read assertion; build, lint and smoke tests exit 0. The build may emit the existing large-chunk advisory.

Vitest only collects src/**/*.test.ts(x), keeping Playwright e2e specs out of the unit suite. Browser e2e acceptance requires disposable test identities; never use Production user credentials. The former staging environment has been decommissioned, so e2e is not treated as a Production release gate.

## Backend focused tests

~~~powershell
$env:PYTHONPATH = "$PWD;$PWD/apps/web-platform/backend"
python -m pip install -r apps/web-platform/backend/requirements-local.txt
python -m pytest -o addopts="" -q apps/web-platform/backend/tests/test_b2_multipart_integrity.py apps/web-platform/backend/tests/test_stream_hash.py apps/web-platform/tests/test_cloudflare_b2_storage.py apps/web-platform/tests/test_cloudflare_worker_contract.py
~~~

Expected: pytest exits 0. Use -o addopts="" to disable the repository coverage defaults for focused runs. The cloud provider suite and Personal Local regression suite are listed in .github/workflows/doka-quality.yml.

## Workflow YAML

~~~powershell
python -c "import yaml; yaml.safe_load(open('.github/workflows/production-ci.yml', encoding='utf-8')); yaml.safe_load(open('.github/workflows/doka-quality.yml', encoding='utf-8')); print('Workflow YAML parsed')"
~~~

## Benchmark

~~~powershell
python apps/web-platform/backend/cloudflare_worker/bench_stream_hash.py
~~~

Measured in the isolated Python 3.13.18 box: 1 MiB 0.089056s vs 0.000600s (148.52x); 10 MiB 0.890030s vs 0.005907s (150.67x); 100 MiB 8.902834s vs 0.058875s (151.22x). Environment-specific only; the script verifies identical digests.

## Production security migration rollout — completed 2026-11-12

The forward migration `doka_security_integrity_remediation` (ledger version `20261112051653`) was applied to Production project `Enterprise AI DMS` after the Production Worker deployment succeeded.

### Release verification
1. PR #140 was merged to `main` as commit `62c5a4b9f8146b851417db10dfb74d03b2c7a157`. Production CI, Doka Quality Checks, CodeQL language analysis, Dependency Review, and Vercel production smoke check completed successfully. CodeQL's separate PR configuration notice was neutral, not a failing code analysis.
2. `SUPABASE_SERVICE_ROLE_KEY` is present as an encrypted secret in the Production Worker. Its value is never exposed to browser code, source, logs, or chat.
3. Cloudflare Worker Production Deploy completed successfully. The Python Worker dry-run build, deploy, health check, single-user readiness, Telegram bot identity, and webhook registration/verification all passed.
4. Migration `doka_security_integrity_remediation` was applied only after the Worker deploy passed.
5. Post-migration SQL verification confirmed:
   - RLS remains enabled on `doka_audit_events`, `doka_document_versions`, and `doka_documents`.
   - Authenticated direct INSERT is denied on audit and version tables.
   - Authenticated execution of `doka_record_audit_event` is denied; `service_role` execution is granted.
   - The bulk/status/trash and version replace/restore RPCs are SECURITY DEFINER, use a fixed search path, and contain explicit `auth.uid()` owner checks.
6. The Production database currently has no active document row, so a real owner-vs-cross-owner document operation could not be exercised. Do not claim full live document E2E acceptance until a disposable, approved test document and second owner identity are available.
7. Do not restore direct authenticated INSERT or broaden protected column UPDATE grants as a rollback. Use a forward repair migration if needed.

### Remaining production acceptance gates
- B2 5 GiB+ live provider acceptance remains unrun; use a disposable bucket/identity, explicit cost cap, and verified cleanup plan before running it.
- Storage MIME allowlist remains unset pending an inventory of supported upload types and upload paths.
- CSP remains report-only pending browser violation collection.
- OCR and live Telegram document-query/account-linking commands remain incomplete/gated.
- Supabase Security Advisor reports four intentional SECURITY DEFINER warnings for authenticated owner-checked RPCs; review their function bodies and fixed search paths before changing their grants. Leaked-password protection remains disabled per the user's Free-plan constraint.

## Multipart integrity

For files above 5 GiB, the frontend worker computes whole-file SHA-256, per-part SHA-256 and per-part MD5. The client compares its per-part MD5 with the provider-generated part ETag returned by B2. The Worker checks each ETag against the part MD5, checks the B2 S3-compatible composite ETag (MD5 over concatenated binary part-MD5 values, suffixed with the part count), then streams the completed object back and checks exact size, whole SHA-256 and each part SHA-256. The x-amz-checksum-sha256 UploadPart header is not sent because it is not listed in B2 UploadPart documentation.

A real B2 bucket must allow the app origin and PUT/OPTIONS in CORS, and expose ETag. Do not change production CORS without owner approval.

## Manual 5 GiB+ acceptance (not yet run against real B2; Production test intentionally blocked)

1. Do not run this test against Production without a separately approved maintenance window, a disposable test identity, explicit storage-cost limit, and a verified cleanup plan. The decommissioned staging environment is no longer available.
2. Any future acceptance must use a dedicated disposable bucket and a disposable identity, with VITE_DOKA_MAX_UPLOAD_BYTES above the test size. Confirm B2_BUCKET/B2 credentials, B2_QUOTA_BYTES headroom, and B2 routing. The Worker also enforces a separate 500 GiB hard ceiling; DOKA_STORAGE_MAX_OBJECT_BYTES is a routing threshold, not a per-file override. Do not paste secrets into logs.
3. Verify bucket CORS allows PUT/OPTIONS and exposes ETag.
4. Create a deterministic file larger than 5 GiB (e.g. 5 GiB + 16 MiB) and record local SHA-256.
5. Chrome DevTools > Memory: capture baseline; upload; inspect initiate, part-signing, direct B2 PUT and complete calls.
6. Confirm every part ETag, final composite ETag, exact object size and read-back SHA-256 match.
7. Cancel another upload midway; confirm abort endpoint runs and no completed document appears. Inspect unfinished multipart uploads in B2.
8. Record peak browser/worker memory, part count, final size, digest and elapsed time. Hash reads are bounded to 8 MiB; one part Blob/network buffer and browser overhead remain.
9. Delete the disposable test object and confirm cleanup.

Never skip ETag or read-back verification to work around CORS; correct only the non-production bucket CORS rule.


### Production owner-isolation verification (2026-11-12)

A transaction-scoped Production verification was completed using two existing Auth user IDs and two synthetic document rows. All test writes were rolled back; no synthetic documents or audit rows remain.

- Owner A successfully changed their own document status through `doka_bulk_update_documents`.
- Owner A's attempt to trash Owner B's document was denied with the expected not-found/ownership-safe result; Owner B's row remained unchanged.
- Owner A successfully created a version using their own user-prefixed object key.
- Owner A's attempt to replace Owner B's document version was denied.
- Authenticated direct INSERT into `doka_audit_events` was denied.
- Authenticated execution of `doka_record_audit_event` was denied.
- The same audit RPC executed successfully under `service_role`.
- The transaction was rolled back after the assertions; the post-test Production database contains no synthetic test documents, versions, or audit events.

This validates the tested database ownership and audit boundaries, but it is not a full browser/API/storage E2E test and does not replace real B2 upload acceptance.

### Remaining workflow/dependency observations (2026-11-12)

- The latest `main` commit `a9622f5beeb27e0ded69dea83ae9fb565f2b884d` passed Production CI, Doka Quality Checks, and both CodeQL language analyses.
- Historical secret scan run `43160801106` failed with zero jobs returned by the Actions jobs endpoint. This is an unexecuted/unverified scan, not a clean scan and not evidence of a detected secret.
- Dependabot PRs #142 and #143 propose the same Vitest 5.1.0 dependency change. Both passed backend checks and CodeQL/Dependency Review but failed frontend production build because TypeScript could not resolve Node built-in module types in test files (`node:fs`, `node:path`, `node:crypto`, and `process`). Do not merge until this is corrected and all required checks pass.


### Final Production verification update (2026-11-12)

- Follow-up documentation commit: `22fc35ac1a985410c0f4595ca2cd1f19862e9b34`.
- GitHub required checks on that commit completed successfully: Production Release Gate, Supabase Preview, Production CI backend/frontend jobs, Doka Quality Checks (backend dependency audit, backend regression tests, frontend build/smoke, cloud-storage contracts, symlink security, static analysis/SBOM, workflow sanity, Electron smoke, repository preflight), and CodeQL/Dependency Review where applicable.
- The Production Worker settings were read back without exposing secrets. Telegram routing variables are confirmed as `TELEGRAM_CHAT_ID=-1003992125718`, `TELEGRAM_TOPIC_ID=8`, and `TELEGRAM_ENABLED=true`. Bot token, webhook secret, allowed-user IDs, B2 credentials, and Supabase service-role key remain encrypted/redacted.
- The Worker was not redeployed for this documentation-only commit; the previously successful Production Worker deployment remains the deployed release.
- Dependabot PR #142 was closed as an exact duplicate of #143. PR #143 remains open and unmerged because its Vitest 5.1.0 update currently fails the frontend TypeScript build; the failure details were recorded in its PR discussion.
