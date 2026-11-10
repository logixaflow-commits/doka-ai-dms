# Session token threat model and migration decision

## Current deployment
The Vite SPA authenticates directly against Supabase Auth, stores access and refresh tokens in localStorage, and sends access tokens as Bearer credentials to the Cloudflare Worker.

## Current localStorage model
Advantages: simple SPA integration, survives reloads, and avoids ambient-cookie CSRF. Risks: same-origin XSS can read and exfiltrate both access and refresh tokens; compromised dependencies and extensions may also access them. Refresh-token persistence increases the impact window. CSP reduces injection opportunities but does not protect tokens after script execution.

## Options

| Option | Security | Advantages | Costs / risks |
|---|---|---|---|
| A. HttpOnly + Secure + SameSite cookie with Supabase SSR helpers | JS cannot read refresh cookie; cookie attributes reduce theft | Standard SSR-compatible session model | Requires SSR/BFF auth endpoints, CSRF defenses, cookie scope and auth-flow migration |
| B. BFF | Browser holds opaque HttpOnly session cookie; BFF owns Supabase tokens | Strong token isolation and centralized refresh/revocation | Requires server session storage or encrypted session, CSRF, rotation and endpoint refactor |
| C. Hybrid | Access token in memory; refresh token in HttpOnly cookie managed by BFF | Transitional compromise | Requires BFF refresh/cookie issuance and CSRF controls; reload requires refresh roundtrip |

## Recommendation
Recommend BFF with HttpOnly Secure SameSite cookies for this Cloudflare Worker + SPA architecture. It keeps refresh credentials out of JavaScript and centralizes rotation, revocation and CSRF checks. Hybrid is a temporary migration bridge only.

## Code preparation and gates
VITE_AUTH_STORAGE_MODE=local remains the default. cookie-prep is preparation only: it keeps tokens in memory and is not a cookie implementation. JavaScript cannot create HttpOnly cookies. Do not enable it until same-origin BFF endpoints, Set-Cookie attributes, CSRF token and Origin validation, logout, refresh rotation and cross-tab behavior are implemented and tested.

## Rollout
1. Build and test BFF session endpoints without changing active SPA mode.
2. Configure Secure; HttpOnly; SameSite=Lax (or stricter), narrow Path/Domain, and CSRF token + Origin validation.
3. Canary behind an explicit server-side feature flag.
4. Verify sign-in, refresh rotation, concurrent refresh, logout, expiry, revocation, multi-tab and cross-origin behavior.
5. Enable only after owner approval; invalidate old local tokens only after successful migration.

Owner approval is required before enabling cookie migration or deploying CSP enforce mode.
