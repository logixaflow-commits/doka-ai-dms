# Repository security and secrets handling

## Current Personal Local Edition

- Never commit `.env` files, API keys, passwords, private keys, or real document data.
- The local runtime uses `web-platform/backend/.env`; the committed template is `web-platform/backend/.env.example`.
- Keep `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false`.
- Use a strong `BOOTSTRAP_ADMIN_PASSWORD` locally; no usable password is stored in the repository.
- Keep the real source drive outside the writable workspace.
- Review Git history before sharing the repository if credentials or real office data were ever committed.
- Prefer GitHub Secret Scanning / Push Protection and Dependabot where available.

## Secret scanning and CI

- Install pre-commit with `pipx install pre-commit`, then run `pre-commit install` to enable the pinned Gitleaks staged-file hook in `.pre-commit-config.yaml`.
- Run `pre-commit run --all-files` before a large repository handoff.
- The consolidated Doka Quality workflow also runs Gitleaks against the current checkout. This is not a historical Git-history scan; if a credential may have been committed in the past, run a dedicated history scan and rotate/revoke the credential.
- Dependabot alerts and GitHub secret-scanning alerts must be reviewed in the repository Security tab; CI/npm/pip audits do not replace that inventory.
- CodeQL and a report-only Semgrep baseline are configured in the quality workflow. Semgrep remains non-blocking until findings are triaged; CodeQL upload alone does not prove branch protection blocks PRs.

## Deferred enterprise material

Legacy deployment scripts and enterprise configuration are preserved under `archive/legacy-enterprise/`. They are not part of the Personal Local runtime and should not be used as the local startup path.
