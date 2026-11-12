# CSP Compatibility Audit

## Source reviewed
`apps/web-platform/frontend/index.html`, `src/main.tsx`, `src/App.tsx`, `vite.config.ts`, `src/workers/hash.worker.ts`, `src/workers/hashFileChunks.ts`, and Worker CSP middleware.

## Findings
- **Inline scripts:** index.html includes a remote Telegram SDK script at `https://telegram.org/js/telegram-web-app.js`. Current `script-src 'self'` blocks it. Add `https://telegram.org` only if Telegram Mini App functionality is required.
- **Inline styles:** React 19, Tailwind and Radix UI are present. The entrypoints reviewed do not prove whether all runtime style attributes are absent. A full component/runtime audit is still required; do not add `unsafe-inline` as a blanket fix.
- **Third-party scripts:** Telegram SDK observed. Vercel SpeedInsights component and Sentry initialization are observed; their exact network origins need staging Network/CSP reports before allowlisting.
- **Supabase:** Auth requests use the configured `VITE_SUPABASE_URL`; add only that exact origin to `connect-src`. Worker API is same-origin relative to its configured base.
- **Fonts/images:** favicon is same-origin. Existing policy permits https/data/blob images, but remote font hosts are not proven absent; inspect CSS and runtime requests.
- **Worker:** Vite emits the hashing worker as a same-origin module asset. `worker-src 'self' blob:` is compatible with the current worker output. The worker hashes bounded 8 MiB reads and does not require a third-party worker origin.
- **Multipart storage:** Browser requests to B2 use presigned HTTPS PUT URLs; the browser reads the provider-computed part `ETag`, so B2 must expose `ETag` through CORS. The exact B2 endpoint origin is runtime configuration and must be observed in staging before adding it to `connect-src`.
- **Inline event handlers:** none observed in reviewed HTML/entrypoint files.

## Policy changes needed before enforce
1. Add `https://telegram.org` to script-src if the SDK remains.
2. Add the exact configured Supabase origin to connect-src.
3. Review Sentry, Vercel Insights, font and image network origins using CSP reports.
4. Consider `style-src-attr 'none'` after verifying component runtime behavior.
5. Keep `worker-src 'self' blob:`.

## Decision
**Not enforce-ready.** The current report-only policy blocks the observed Telegram SDK script and may block Sentry/Supabase/font requests. Enforce mode remains disabled pending staging report review and owner approval.
