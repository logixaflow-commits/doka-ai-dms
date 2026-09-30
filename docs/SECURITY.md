# Repository security and secrets handling

## Current Personal Local Edition

- Never commit `.env` files, API keys, passwords, private keys, or real document data.
- The local runtime uses `web-platform/backend/.env`; the committed template is `web-platform/backend/.env.example`.
- Keep `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false`.
- Use a strong `BOOTSTRAP_ADMIN_PASSWORD` locally; no usable password is stored in the repository.
- Keep the real source drive outside the writable workspace.
- Review Git history before sharing the repository if credentials or real office data were ever committed.
- Prefer GitHub Secret Scanning / Push Protection and Dependabot where available.

## Current CI boundary

The current `Local Core Checks` workflow validates Python compilation, frontend build/smoke tests, and the Personal Local safety regression suite. It does not claim to be a full secret scanner or dependency vulnerability scanner.

## Deferred enterprise material

Legacy deployment scripts and enterprise configuration are preserved under `archive/legacy-enterprise/`. They are not part of the Personal Local runtime and should not be used as the local startup path.
