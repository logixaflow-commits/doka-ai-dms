# Doka Security

## Scope
This document defines the active security boundary for Personal Local and Personal Cloud. Enterprise controls remain deferred until their dedicated roadmap gates are activated.

## Threat model
Protect against unauthorized document access, cross-user data access, source mutation, path traversal, unsafe restore/copy behavior, leaked credentials, insecure provider use, unauthorized administrative operations and accidental production reactivation.

## Authentication
Personal Local uses its local authentication/session boundary. Personal Cloud uses Supabase Auth. Cloud ownership is derived from the verified authenticated identity; clients must not supply a trusted owner identity.

## Authorization
Authorization is enforced server-side. RLS/Storage policies provide an independent ownership boundary but do not replace API authorization. Administrative operations are explicitly protected. Human approval remains required for publication-sensitive AI organization.

## RLS and Storage
Cloud document, version and audit data are owner-scoped. Private Storage object paths are scoped to the authenticated user. Version and bulk database functions retain explicit ownership checks. Trashed documents are excluded from normal access paths.

## Service-role and secrets
Service-role/database secrets, AI-provider keys, Cloudinary secrets, B2 credentials and OAuth refresh tokens are server-side only. Browser VITE_* values may contain intentionally public configuration only.

## Personal Local filesystem safety
Original source is read-only. SOURCE_ROOT and WORKING_ROOT must not overlap. Writable organization targets remain within the working root. Backup is separate. Restore is isolated. Copy/undo operations verify content integrity and do not overwrite unrelated content.

## API and browser boundary
The browser must use the intended API boundary and must never bypass server authorization by calling privileged storage/database APIs directly. Signed URLs are short-lived. Preview accepts only explicitly safe passive formats.

## Rate limits, CORS and abuse controls
Rate limiting and CORS remain server-side controls. Production configuration must use exact allowed origins and bounded request/resource limits. Do not weaken these controls to make a deployment pass.

## Logging and PII
Do not log credentials, tokens, signed URLs, raw document contents or unnecessary personal data. Telemetry must be privacy-scrubbed where configured.

## Dependency and supply-chain security
Maintain lockfiles, Dependabot/security scanning, CodeQL and secret scanning. A green scan is evidence for that scan only; it does not prove runtime security.

## Deployment control
Vercel is owner-paused. Do not reactivate, reconnect or deploy without explicit owner authorization. Cloudflare Worker is the active cloud API. Render has no active runtime verified.

## Known/deferred risks
- Supabase leaked-password protection remains a release verification item until explicitly enabled and verified.
- Real B2, Cloudinary and Google Drive recovery evidence is pending.
- Enterprise RBAC/tenant isolation is deferred.
- Configured provider credentials do not prove live health.

## Verification checklist
- [ ] Authenticated cloud lifecycle tested.
- [ ] Two-user isolation tested.
- [ ] RLS/Storage/RPC ownership tested.
- [ ] Source hashes unchanged after local pilot.
- [ ] Backup/restore integrity and RTO/RPO measured.
- [ ] Provider recovery drills completed.
- [ ] Security Advisor findings reviewed.
- [ ] Release evidence recorded in CURRENT_STATE.md and ROADMAP.md.