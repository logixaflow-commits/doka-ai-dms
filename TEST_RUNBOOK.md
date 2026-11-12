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

## Production security migration rollout

The forward migration removes direct authenticated INSERT on audit/version tables and installs owner-checked SECURITY DEFINER RPCs with a fixed `pg_catalog, public, pg_temp` search path. The Worker audit call uses the caller's verified Supabase JWT; no service-role key is required.

1. Require all CI checks to pass on the exact PR head.
2. Deploy the reviewed Worker code first. If the audit RPC is not installed yet, the Worker uses a 404-only compatibility fallback to the existing owner-scoped audit INSERT policy. Other RPC errors do not trigger fallback.
3. Apply `20261110090000_doka_security_integrity_remediation.sql` as a forward migration only after reviewing the SQL and confirming the Worker deployment is healthy.
4. Verify an authenticated owner can create an audit event, and a mismatched owner ID is denied. Verify bulk status/trash, version replacement, and version restore succeed for the owner and reject cross-owner document/version IDs.
5. Confirm direct authenticated INSERT on `doka_audit_events` and `doka_document_versions` is denied after migration. If the audit RPC is missing from the PostgREST schema cache, the legacy INSERT fallback will fail closed after privileges are revoked; refresh the schema cache rather than broadening grants.
6. Keep a forward-repair plan. Do not restore direct authenticated INSERT or broaden protected column UPDATE grants as a rollback.

Do not deploy or apply the migration if CI is failing, the Worker deployment cannot be verified, or the owner/cross-owner RPC checks cannot be performed.

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
