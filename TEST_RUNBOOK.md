# TEST_RUNBOOK.md

All commands below are local/CI tests only; they do not deploy, merge, rotate secrets, or change infrastructure.

## Frontend
```powershell
cd apps/web-platform/frontend
npm install
npm run build
npm run test:unit
```
Expected: TypeScript/Vite build exits 0; Vitest reports the worker hashing unit tests passed. The lockfile currently needs regeneration because package.json includes Vitest and @noble/hashes entries absent from package-lock.json. After dependency review, run `npm install` and commit the regenerated package-lock.json. Until then, `npm ci` is expected to fail due to package/lock mismatch.

Debug: `npm ls vitest @noble/hashes`; verify package-lock has matching root dependency declarations and node_modules entries.

## Backend focused tests
```powershell
cd apps/web-platform/backend
$env:PYTHONPATH="cloudflare_worker;."
python -m pip install -r requirements-local.txt
python -m pip install pytest pytest-asyncio pyyaml
python -m pytest -vv -s tests/test_stream_hash.py tests/test_security_headers_contract.py tests/test_staging_workflow_yaml.py
```
Expected: pytest exits 0. ImportError: confirm working directory and PYTHONPATH. Fixture error: run the failing test with `-vv -s` and inspect conftest.py. These focused tests do not establish live B2 behavior.

## YAML
```powershell
python -c "import yaml; yaml.safe_load(open('.github/workflows/production-ci.yml', encoding='utf-8')); print('YAML parsed')"
```
Expected: YAML parsed.

## Benchmark
```powershell
python apps/web-platform/backend/cloudflare_worker/bench_stream_hash.py
```
Expected: markdown table with 1, 10 and 100 MiB timings and matching digests. Actual timings depend on hardware.

## Manual 5 GiB memory profile
Use Chrome DevTools > Memory. Take a heap snapshot before upload; run a 5 GiB non-production test upload; record peak browser/worker memory; take a second snapshot; confirm growth is bounded by chunk buffering plus browser overhead. Check cancellation terminates the worker. Do not use production documents.
