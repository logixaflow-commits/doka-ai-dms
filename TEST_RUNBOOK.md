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

Vitest only collects src/**/*.test.ts(x), keeping Playwright e2e specs out of the unit suite. Run Playwright separately with npm run test:e2e:local after configuring the staging test users and starting the app.

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

## Staging environment preflight (2026-11-12 audit)

The connected Cloudflare account has a separate `doka-ai-dms-staging` Worker. Its current binding inventory contains only `DOKA_STORAGE_SESSION_SECRET` as a secret; it does not currently contain B2 credentials or `SUPABASE_SERVICE_ROLE_KEY`. Do not copy credentials from the production Worker or reuse the production B2 bucket.

Before applying `20261110090000_doka_security_integrity_remediation.sql` to staging or deploying this branch to the staging Worker:

1. Provision or identify a dedicated non-production Backblaze B2 bucket and create a bucket-scoped application key for it. Add the matching `B2_BUCKET`, `B2_APPLICATION_KEY`, `B2_KEY_ID`, `B2_ENDPOINT`, `B2_REGION`, and a safe staging-only `B2_QUOTA_BYTES` to the staging Worker as encrypted secrets. Verify the bucket CORS allows the staging app origin, PUT and OPTIONS, and exposes `ETag`.
2. Add the staging Supabase service-role key as the encrypted `SUPABASE_SERVICE_ROLE_KEY` secret to the staging Worker. The Worker audit path in this branch calls `doka_record_audit_event` with this trusted credential; without it, audit writes fail closed with HTTP 503 after the database migration is applied. Never put this value in Vite/browser variables or GitHub source.
3. Configure the staging Worker `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` for the staging Supabase project only. The staging Worker currently has a publishable-key binding but it is a plain-text binding; replace it with the appropriate staging key through the approved secret configuration path. Confirm the URL is the staging project URL without printing key values.
4. Add the disposable User A/B variables listed in the Playwright/staging workflow instructions to the staging GitHub/Vercel environment only. Never reuse production identities.
5. Confirm the staging app origin and Worker origin are allowlisted in staging CORS. Do not edit production bindings, secrets, routes, bucket CORS or deployments.

### Migration history note

The staging migration ledger reports three entries: `20261016094050_staging_doka_core_schema_rls_storage`, `20261017081123_doka_rpc_security_hardening`, and `20261024034356_doka_least_privilege_grants_reconcile_20261024`. The first two staging bootstrap migration source files are not present in this repository's migration directory. Production reports 33 entries, including a different complete migration chain. This count difference alone does not prove schema drift: staging appears to have been bootstrapped with a consolidated baseline. Do not replay the 33 production migrations into staging. First recover or reconstruct and review the exact staging baseline SQL, then compare actual tables, columns, indexes, constraints, RLS policies, grants, and function definitions against production and the tracked source before declaring parity.

### Database migration gate

The current remediation migration revokes authenticated direct INSERT on audit/version tables and removes their INSERT policies; it also introduces the service-role-only audit RPC. It deliberately leaves the four owner-guarded SECURITY DEFINER RPCs executable by authenticated users. Staging Security Advisor currently reports those four functions. Do not switch them to SECURITY INVOKER or revoke EXECUTE until the caller paths and required table/column grants are proven compatible. Apply the migration to staging only after steps 1–3 are verified and a rollback/forward-repair plan is ready. Never apply it to production as part of this acceptance.

## Multipart integrity

For files above 5 GiB, the frontend worker computes whole-file SHA-256, per-part SHA-256 and per-part MD5. The client compares its per-part MD5 with the provider-generated part ETag returned by B2. The Worker checks each ETag against the part MD5, checks the B2 S3-compatible composite ETag (MD5 over concatenated binary part-MD5 values, suffixed with the part count), then streams the completed object back and checks exact size, whole SHA-256 and each part SHA-256. The x-amz-checksum-sha256 UploadPart header is not sent because it is not listed in B2 UploadPart documentation.

A real B2 bucket must allow the app origin and PUT/OPTIONS in CORS, and expose ETag. Do not change production CORS without owner approval.

## Manual 5 GiB+ acceptance (not yet run against real B2)

1. Use a disposable staging user and non-production B2 bucket.
2. Set staging VITE_DOKA_MAX_UPLOAD_BYTES above the test size. Confirm the Worker has B2_BUCKET/B2 credentials, B2_QUOTA_BYTES has sufficient headroom, and B2 routing is enabled. The Worker also enforces a separate 500 GiB hard ceiling; DOKA_STORAGE_MAX_OBJECT_BYTES is a routing threshold, not a per-file override. Do not paste secrets into logs.
3. Verify bucket CORS allows PUT/OPTIONS and exposes ETag.
4. Create a deterministic file larger than 5 GiB (e.g. 5 GiB + 16 MiB) and record local SHA-256.
5. Chrome DevTools > Memory: capture baseline; upload; inspect initiate, part-signing, direct B2 PUT and complete calls.
6. Confirm every part ETag, final composite ETag, exact object size and read-back SHA-256 match.
7. Cancel another upload midway; confirm abort endpoint runs and no completed document appears. Inspect unfinished multipart uploads in B2.
8. Record peak browser/worker memory, part count, final size, digest and elapsed time. Hash reads are bounded to 8 MiB; one part Blob/network buffer and browser overhead remain.
9. Delete the disposable test object and confirm cleanup.

Never skip ETag or read-back verification to work around CORS; correct only the non-production bucket CORS rule.
