# Doka Working Tool & Delivery Protocol

## 1. Read order
1. README.md
2. CURRENT_STATE.md
3. PROJECT_OVERVIEW.md
4. ROADMAP.md
5. TOOL.md
6. Relevant docs/*.md
7. Code, tests and workflow files

## 2. Git workflow
Work from main unless an explicitly authorized branch is required. Keep changes small and reviewable. Never expose secrets in commits, logs or browser configuration. Historical material is archived, not discarded.

## 3. Phase completion protocol
1. Implementation complete.
2. Unit tests pass.
3. Integration tests pass.
4. Required E2E/live verification passes.
5. Acceptance criteria satisfied.
6. Evidence recorded.
7. Documentation updated in the same change.
8. CURRENT_STATE.md NEXT ACTION updated.

## 4. Documentation update protocol
| Change | Required documentation |
|---|---|
| Feature | CURRENT_STATE.md, ROADMAP.md |
| Architecture | PROJECT_OVERVIEW.md and relevant architecture reference |
| UI | UI_DESIGN_SYSTEM.md |
| Security | SECURITY.md |
| Tool/workflow | TOOL.md |
| DB/schema/migration | docs/DATABASE.md |
| Deployment | docs/DEPLOYMENT.md |
| AI/RAG | docs/AI_RAG.md |
| Storage | docs/STORAGE.md |
| API | docs/API.md |
| Testing | docs/TESTING.md |
| Operations | docs/OPERATIONS.md |
| Phase closure | README.md plus all applicable domain docs |

A phase is not complete if required documentation/evidence is missing.

## 5. Doc drift rule
If code changes without the corresponding authority document being updated, flag the drift and reconcile documentation before closing the work. Do not use repeated phase-status files as substitutes for canonical status.

## 6. Tools matrix
| Tool | Purpose | Local/Cloud | Required | Credential |
|---|---|---|---|---|
| Python 3.12 | FastAPI/backend | Local | Yes | No |
| Node 24 + npm | React/Vite | Local | Yes | No |
| Tesseract | Myanmar/English OCR | Local | Benchmark | No |
| Supabase | Auth/Postgres/RLS/Storage | Cloud | Yes for Cloud | Owner credentials for live tests |
| Cloudflare Worker | Cloud API | Cloud | Yes for Cloud | Worker access |
| Cloudinary | derivative/provider path | Cloud | Pending live proof | Provider credentials |
| Backblaze B2 | >50 MiB source path | Cloud | Pending live proof | Provider credentials |
| Google Drive | export/archive | Cloud | Pending live proof | OAuth credentials |
| AI providers | optional advisory processing | Both | Disabled by default | Provider-specific keys |
| Vercel | frontend target | Cloud | Paused | Owner authorization |

## 7. Evidence rules
Status means:
- DONE = implementation exists.
- VERIFIED = evidence exists.
- PENDING = required work/evidence not yet complete.
- BLOCKED = cannot close until prerequisite passes.
- DEFERRED = intentionally postponed.
- NEXT = next action.
- VERIFY = fact requires fresh verification.

Configured credentials do not prove provider health. Unit tests do not prove live integration. Synthetic pilots do not prove office readiness.

## 8. Safety invariants
Original source is read-only. Organization is copy-only. Final/quarantine remain inside the workspace. Recovery is isolated. Cloud ownership is enforced by authenticated identity plus RLS/Storage boundaries. AI never bypasses human approval for publication-sensitive actions.

## 9. Session start/end
Start by reading CURRENT_STATE, ROADMAP and TOOL. End by updating CURRENT_STATE, ROADMAP when status changes, relevant domain documentation, and the evidence record.

## 10. Release acceptance
No final release claim without the required real browser, copied-office, OCR, recovery, isolation, provider and security evidence listed in ROADMAP.md.
