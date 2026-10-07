# Doka Enterprise Identity, Organization & RBAC Design

Status: design only — no organization/team endpoints are exposed in production yet.  
Prerequisite: Personal Cloud lifecycle, Personal Local pilot and recovery gates must pass before enabling team data access.

## Security goals

- A user sees only personal documents and organizations they belong to.
- Tenant boundaries are enforced in Postgres RLS and the API, never only in frontend navigation.
- Roles are assigned by trusted server-side membership workflows, not user-editable profile metadata.
- Every membership/role/share change is auditable.
- Removing a member immediately blocks future API access; sensitive operations may additionally validate active sessions where required.

## Initial role model

| Role | Manage organization | Invite/remove members | Change roles | Read documents | Upload/update documents | Delete/restore documents |
|---|---:|---:|---:|---:|---:|---:|
| Owner | Yes | Yes | Yes | Yes | Yes | Yes |
| Admin | Limited | Yes | Yes (except owner) | Yes | Yes | Yes |
| Editor | No | No | No | Yes | Yes | Trash/restore own or explicitly assigned docs |
| Reviewer | No | No | No | Assigned docs | Metadata/review state only | No |
| Viewer | No | No | No | Shared docs only | No | No |

A membership can have only one active role. The Owner role is unique per organization; transfer requires a dedicated audited operation.

## Future data model

- `doka_organizations`: organization ID, display name, creator/owner, timestamps, lifecycle state.
- `doka_memberships`: organization ID, user ID, role, membership state, invited/accepted timestamps.
- `doka_invitations`: hashed invite token, email, role, expiry, creator, acceptance state.
- `doka_document_shares`: document ID, target organization/user, access level, expiry and creator.
- `doka_audit_events`: append-only event ID, organization, actor, action, target, safe metadata, timestamp.

Do not add organization_id to the current personal document rows until tenant membership and share semantics have been fully implemented and tested. Personal documents remain owner-scoped by the existing policies.

## RLS design requirements

- Enable RLS on every exposed table.
- Use `TO authenticated` plus a membership/ownership predicate; role alone is not authorization.
- UPDATE policies require both USING and WITH CHECK to prevent tenant reassignment.
- Keep role authority in a protected table or trusted `app_metadata`; never trust `user_metadata`.
- Prefer invoker-rights functions; avoid SECURITY DEFINER unless there is a reviewed, non-exposed helper requirement.
- Never grant `anon` table access.
- Keep service-role credentials out of browser bundles and ordinary API paths.
- Audit event tables deny UPDATE/DELETE to normal users.

## Required authorization test matrix

For every organization and shared-document API, tests must cover:
- owner can perform all allowed operations;
- admin cannot transfer or remove the owner;
- editor/reviewer/viewer are restricted to the role matrix;
- a user from another organization cannot list, fetch, update, download or infer document IDs;
- revoked and expired invitations cannot be accepted;
- role downgrade/removal takes effect on the next protected request;
- forged user_metadata claims do not grant privileges;
- pagination, filters, export and signed URLs preserve tenant scoping.

## Activation gate

Do not expose Admin Users, Permissions, Teams, sharing or enterprise navigation until:
1. schema and RLS migrations are reviewed;
2. server-side invitation and membership APIs are implemented;
3. the role matrix has automated tests;
4. two-tenant isolation tests pass;
5. audit coverage and recovery are verified;
6. a security review is recorded.
