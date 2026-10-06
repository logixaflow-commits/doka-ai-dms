# Doka — Master Roadmap (Complete Single-File Documentation)

**Version:** 1.0  
**Last Updated:** 2026-10-06  
**Status:** ACTIVE — Single Source of Truth  
**Owner:** Single User (Logixa Flow)  
**Repository:** logixaflow-commits/doka-ai-dms  
**Purpose:** Consolidated roadmap for AI verification + human reference

---

## 📖 Table of Contents

0. [Phase 0: Personal Local Foundation](#0-phase-0-personal-local-foundation)
1. [Project Identity](#1-project-identity)
2. [Safety Rules (Non-Negotiable)](#2-safety-rules-non-negotiable)
3. [Architecture](#3-architecture)
4. [Feature Matrix](#4-feature-matrix)
5. [AI Features Plan](#5-ai-features-plan)
6. [Enterprise Archive](#6-enterprise-archive)
7. [Security Plan](#7-security-plan)
8. [Validation Gates](#8-validation-gates)
9. [Phase 1: Cloud Base](#9-phase-1-cloud-base)
10. [Phase 2: Desktop App](#10-phase-2-desktop-app)
11. [Phase 3: Android App](#11-phase-3-android-app)
12. [Phase 4: Sync Engine](#12-phase-4-sync-engine)
13. [Contributing Rules](#13-contributing-rules)
14. [Change Log](#14-change-log)
15. [Final Declaration](#15-final-declaration)

---

## 0. Phase 0: Personal Local Foundation

**Status:** 🔄 Foundation validation required before Cloud go-live  
**Purpose:** Preserve and validate the existing Personal Local safety foundation before the project proceeds through the Cloud Base → Desktop → Android → Sync execution order.

### 0.1 Phase 0 Scope

- Validate the existing Personal Local Edition on a real Windows machine.
- Execute **PL-G1 through PL-G20 exactly as defined in Section 8.1**; do not duplicate or redefine the gate list here.
- Preserve R1-R10 throughout validation.
- Record evidence for every gate, including failures and remediation.
- Phase 0 is a **foundation prerequisite**, not a competing product execution phase.
- Phase 1 Cloud Base remains the first active product phase after the foundation is validated.

### 0.2 Phase 0 Exit Criteria

Phase 0 is complete only when PL-G1 through PL-G20 have passed or have an explicitly documented owner-approved exception, with evidence recorded and no unresolved safety-critical failure.

---

## 1. Project Identity

### 1.1 Vision

Build a **Multi-Platform Unified Document Management System** that:
- Works on **Cloud** (browser)
- Works on **Desktop** (Windows/Mac/Linux)
- Works on **Android** (mobile)
- All three **sync together** with one user account
- **Never destroys original files**
- **AI recommends, human approves**
- **Works offline** when needed

### 1.2 Current State

| Aspect | Status |
| :--- | :--- |
| Code Foundation | ✅ Complete |
| Branch Consolidation | ✅ Complete (main) |
| CI (Automated) | ✅ Green |
| Personal Local Edition | ✅ Code Ready |
| Cloud Edition | ⚠️ Implemented, verification-gated |
| Vercel Deployment | ⏸️ Paused (owner-controlled) |
| Real-Machine Validation | ⏳ Pending owner-run acceptance tests |
| Production Sign-off | ❌ Not Issued |

### 1.3 Execution Order / Current State

**Current active product phase: Phase 1 — Cloud Base FIRST**

| Order | Phase | State |
| :--- | :--- | :--- |
| 0 | Personal Local Foundation + PL-G1 → PL-G20 | 🔄 Validation prerequisite |
| 1 | Cloud Base | 🔄 Active execution / go-live validation |
| 2 | Desktop | ⏳ Pending Phase 1 sign-off |
| 3 | Android | ⏳ Pending Phase 2 sign-off |
| 4 | Unified Sync Engine | ⏳ Pending Phase 3 sign-off |
| 5 | Enterprise | 🔒 Dormant Until Funded |

Personal Local remains the safety/reference foundation. It is **not** the first new product milestone; Cloud Base is.

Users: 1 owner for the Personal Local foundation; Cloud supports authenticated user accounts.
AI: Optional (Default OFF)

text

### 1.4 Core Business Problem

User has a messy office document drive (D:) containing:
- Many duplicate files
- Duplicate filenames with different contents
- Copies/finals/versions
- Poorly named files
- Inconsistent folders
- Myanmar + English documents
- Scanned PDFs/images
- Hard-to-classify documents

**Solution:** Safe inspection → verified copy → OCR/understanding → duplicate/version review → human approval → organized library → backup/recovery.

---

## 2. Safety Rules (Non-Negotiable)

These rules apply to **ALL phases** and **ALL platforms**. Violation = immediate reject.

| # | Rule | Enforcement |
| :- | :--- | :--- |
| **R1** | Original source is READ-ONLY | `ORIGINAL_READ_ONLY=true` |
| **R2** | SOURCE_ROOT ≠ WORKING_ROOT (no overlap) | Startup validation |
| **R3** | Never write to source directly | Code guard |
| **R4** | Workflow: Copy → Verify → Review → Approve → Copy to Final | Pipeline contract |
| **R5** | AI recommends, human approves | AI boundary |
| **R6** | No file enters Final without approval | Approval gate |
| **R7** | Undo only removes hash-unchanged files | Journal check |
| **R8** | No default usable admin password | Bootstrap only |
| **R9** | Legacy enterprise code preserved, not deleted | Archive boundary |
| **R10** | Vercel stays paused unless owner explicitly requests | Deployment control |

### 2.1 Detailed Rules

#### R1: Original Source Read-Only
✅ ALLOWED: Read files, compute hashes, copy files
❌ FORBIDDEN: Write, rename, move, delete, modify timestamps
ENFORCEMENT: ORIGINAL_READ_ONLY=true + app-level write guard

text

#### R2: Source ≠ Workspace
✅ ALLOWED: Source=D:\Office, Workspace=C:\DMS\Workspace
❌ FORBIDDEN: Source=D:\Office, Workspace=D:\Office\Workspace
ENFORCEMENT: Startup check, reject with error if overlap

text

#### R4: Workflow Contract
[1] Copy (source → workspace)
[2] Verify (SHA-256 match)
[3] Inspect (OCR + classification)
[4] Review (user sees proposal)
[5] Approve (user confirms)
[6] Copy to Final (workspace → Final)
[7] Verify (SHA-256 match again)
[8] Audit (journal entry)
NO SKIPPING STEPS.

text

#### R5: AI Boundary
✅ ALLOWED: AI suggests folder, category, tags, summary
❌ FORBIDDEN: AI deletes, moves, approves, modifies source
ENFORCEMENT: AI returns "recommendation" only; AI_ENABLED=false default

text

#### R7: Undo Safety
✅ ALLOWED: Undo if hash unchanged since apply AND journal entry exists
❌ FORBIDDEN: Undo if hash changed, not in journal, or source file
ENFORCEMENT: Journal lookup + SHA-256 comparison before delete

text

#### R8: No Default Password
✅ ALLOWED: BOOTSTRAP_ADMIN_PASSWORD set by user (≥12 chars)
❌ FORBIDDEN: admin/admin123 default, hardcoded passwords
ENFORCEMENT: App refuses to start if password missing

text

#### R9: Legacy Preservation
✅ ALLOWED: Keep legacy code in archive/, reference in docs
❌ FORBIDDEN: Delete legacy code, import into Personal Local, route legacy pages
ENFORCEMENT: Archive boundary respected

text

#### R10: Vercel Control
✅ ALLOWED: Owner explicitly requests Vercel build, one clean build
❌ FORBIDDEN: Reconnect, trigger deployment, commit vercel.json, retry repeatedly
ENFORCEMENT: Owner-controlled dashboard, no vercel.json in repo

text

### 2.2 Violation Response

1. Stop operation immediately
2. Log to audit
3. Alert owner
4. Revert if possible
5. Post-mortem required
6. Amend code to prevent recurrence

---

## 3. Architecture

### 3.1 High-Level Architecture
┌───────────────────────────────────────────────────────┐
│ CLIENT LAYER │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│ │ Browser │ │ Desktop │ │ Android │ │ CLI ││
│ │ (React) │ │ (Tauri) │ │ (RN) │ │ (opt) ││
│ └──────────┘ └──────────┘ └──────────┘ └────────┘│
└───────────────────────────────────────────────────────┘
↓
┌───────────────────────────────────────────────────────┐
│ API GATEWAY LAYER │
│ ┌──────────────────────────────────────────────────┐ │
│ │ Cloudflare Worker (Cloud) │ │
│ │ OR Local FastAPI (Desktop/Android offline) │ │
│ └──────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
↓
┌───────────────────────────────────────────────────────┐
│ BUSINESS LOGIC LAYER │
│ Auth | Document | OCR | Planner | Backup | Undo │
│ Search | Import | Duplicate | Version | Sync │
└───────────────────────────────────────────────────────┘
↓
┌───────────────────────────────────────────────────────┐
│ DATA LAYER │
│ Supabase (Auth+PG) | B2 (large) | Cloudinary (img) │
│ Supabase Storage | Google Drive | Local SQLite │
└───────────────────────────────────────────────────────┘
↓
┌───────────────────────────────────────────────────────┐
│ SYNC ENGINE LAYER │
│ Delta Sync + Conflict Resolution + Offline Queue │
└───────────────────────────────────────────────────────┘

text

### 3.2 Technology Stack

| Layer | Technology | Status |
| :--- | :--- | :--- |
| Frontend | React + TypeScript + Vite | ✅ Active |
| Desktop | Tauri (planned) | ⏳ Phase 2 |
| Mobile | React Native (planned) | ⏳ Phase 3 |
| Cloud API | Cloudflare Worker | ✅ Active |
| Local API | FastAPI + Python | ✅ Active |
| Database | Supabase Postgres | ✅ Active |
| Local DB | SQLite | ✅ Active |
| OCR | Tesseract (eng + mya) | ✅ Active |
| Storage (small ≤50 MiB) | Supabase Storage | ✅ Active |
| Storage (large >50 MiB) | Backblaze B2 | ✅ Active |
| Images | Cloudinary | ✅ Active |
| Backup | Google Drive | ✅ Active |
| Sync | Custom (planned) | ⏳ Phase 4 |

### 3.3 Repository Layout
enterprise-ai-dms/
├── web-platform/ # ACTIVE runtime
│ ├── backend/
│ │ ├── app/
│ │ │ ├── main.py
│ │ │ ├── personal/ # Personal Local code
│ │ │ ├── cloud/ # Cloud Edition code
│ │ │ └── ...
│ │ └── requirements.txt
│ └── frontend/
│ ├── src/
│ │ ├── App.tsx
│ │ ├── pages/
│ │ └── legacy/ # Not routed
│ └── package.json
├── cloudflare_worker/ # Active cloud API
├── supabase/ # DB + RLS + Storage
├── infrastructure/ # 💤 Deferred (Docker/K8s)
├── mobile/ # 💤 Deferred
├── archive/
│ └── legacy-enterprise/ # 💤 Preserved
├── docs/ # Documentation
├── scripts/ # Utility scripts
└── .github/workflows/ # CI

text

### 3.4 Data Flow (Upload)
User selects file

Client checks file size

Client requests upload session

API returns HMAC-bound session token
5a. ≤50 MiB → Direct upload to Supabase Storage
5b. >50 MiB → Direct upload to Backblaze B2

Client calls completion endpoint

API verifies session + size + result

API writes metadata to Postgres

OCR runs (background)

Classification + duplicate check

User reviews + approves

File moves to Final (copy-only)

Audit journal written

Sync push to other devices

text

### 3.5 Security Boundaries

| Boundary | Rule |
| :--- | :--- |
| Supabase RLS | Row-level security enforced |
| Cloudflare Worker | No byte proxy |
| Direct uploads | HMAC-bound sessions |
| Service-role key | Never committed |
| `VITE_*` values | Public config only |
| Vercel | Paused unless owner requests |

---

## 4. Feature Matrix

### 4.1 Legend

| Symbol | Meaning |
| :--- | :--- |
| ✅ | Active |
| 💤 | Dormant (preserved) |
| ⏳ | Planned |
| ❌ | Missing |
| 🔒 | Locked |

### 4.2 Document Management

| Feature | Status | Phase |
| :--- | :--- | :--- |
| Safe Import | ✅ Active | Pre |
| Resumable Import | ✅ Active | Pre |
| File Inventory | ✅ Active | Pre |
| OCR (English) | ✅ Active | Pre |
| OCR (Myanmar) | ✅ Active | Pre |
| Duplicate Detection | ✅ Active | Pre |
| Version Family Detection | ✅ Active | Pre |
| Organization Planner | ✅ Active | Pre |
| Manual Review | ✅ Active | Pre |
| Apply to Final | ✅ Active | Pre |
| Undo | ✅ Active | Pre |
| Backup | ✅ Active | Pre |
| Recovery | ✅ Active | Pre |
| Search (basic) | ✅ Active | Pre |
| Audit Log | ✅ Active | Pre |
| Document Versioning (V1,V2,V3) | ❌ Missing | Phase 1 |
| Bulk Actions | ❌ Missing | Phase 1 |
| Document Locking | ❌ Missing | Phase 1 |
| Advanced Filters | ❌ Missing | Phase 1 |
| Saved Searches | ❌ Missing | Phase 1 |
| Document Watermark | ❌ Missing | Phase 5 |
| DRM | ❌ Missing | Phase 5 |

### 4.3 AI Features

| Feature | Status | Phase |
| :--- | :--- | :--- |
| Provider Fallback | ✅ Active | Pre |
| AI Classification | 💤 Dormant | Phase 1 |
| AI Auto-Tagging | ❌ Missing | Phase 1 |
| Semantic Search | ❌ Missing | Phase 1 |
| Chat with Documents | ❌ Missing | Phase 1 |
| AI Summarization | ❌ Missing | Phase 1 |
| Rule Engine (IF-THEN) | 💤 Dormant | Phase 2 (optional) |
| Predictive Analytics | ❌ Missing | Phase 5 |

### 4.4 Enterprise Features (All Archived)

| Feature | Status | Location |
| :--- | :--- | :--- |
| Multi-user | 💤 Dormant | archive/legacy-enterprise/ |
| RBAC | 💤 Dormant | archive/legacy-enterprise/ |
| 2FA | 💤 Dormant | archive/legacy-enterprise/ |
| Folder Permissions | 💤 Dormant | archive/legacy-enterprise/ |
| SOP Tracking | 💤 Dormant | archive/legacy-enterprise/ |
| Reminders | 💤 Dormant | archive/legacy-enterprise/ |
| Email Alerts | 💤 Dormant | archive/legacy-enterprise/ |
| Compliance Reports | 💤 Dormant | archive/legacy-enterprise/ |
| Analytics Dashboard | 💤 Dormant | archive/legacy-enterprise/ |
| Real-time SSE | 💤 Dormant | archive/legacy-enterprise/ |
| Social Media Ingestion | 💤 Dormant | archive/legacy-enterprise/ |
| External API Integration | 💤 Dormant | archive/legacy-enterprise/ |
| Monitoring | 💤 Dormant | infrastructure/ |
| Mobile (native) | 💤 Dormant | mobile/ |
| Cloud Deployment | 💤 Dormant | infrastructure/ |

**🔒 ENTERPRISE — DORMANT UNTIL FUNDED**

All Enterprise features are preserved in `archive/legacy-enterprise/` (and
related legacy infrastructure locations) and are **not deleted**.

They are:
- ❌ NOT active in Personal Local
- ❌ NOT active in Cloud
- ❌ NOT automatically imported, routed, or exposed
- ❌ NOT part of the current product execution phases
- 🔒 Activation requires **funding + formal amendment + a new dedicated phase +
  full validation gates + owner sign-off**

No Enterprise feature may be activated merely because its legacy code exists.

### 4.5 Security Features

| Feature | Status | Phase |
| :--- | :--- | :--- |
| Local JWT Auth | ✅ Active | Pre |
| Bootstrap Admin Password | ✅ Active | Pre |
| Source Read-Only | ✅ Active | Pre |
| Path Traversal Protection | ✅ Active | Pre |
| Symlink Protection | ✅ Active | Pre |
| Fernet Encryption | ✅ Active | Pre |
| HMAC-bound Upload Sessions | ✅ Active | Phase 1 |
| Supabase RLS | ✅ Active | Phase 1 |
| Rate Limiting | ❌ Missing | Phase 1 |
| HttpOnly Cookies | ❌ Missing | Phase 1 |
| Server-side Token Revocation | ❌ Missing | Phase 1 |
| OS-level Source ACL | ❌ Missing | Phase 2 |
| Leaked Password Protection | 🚨 Not yet enabled/verified | Phase 1 |
| Manifest-only Download Enforcement | ❌ Missing | Phase 1 |

### 4.6 Deployment & Infrastructure

| Feature | Status | Phase |
| :--- | :--- | :--- |
| Local Filesystem | ✅ Active | Pre |
| Supabase Storage | ✅ Active | Phase 1 |
| Backblaze B2 | ✅ Active | Phase 1 |
| Cloudinary | ⚠️ Config-gated; recovery proof pending | Phase 1 |
| Google Drive | ⚠️ Config-gated; recovery proof pending | Phase 1 |
| Cloudflare Worker | ✅ Active | Phase 1 |
| FastAPI | ✅ Active | Pre |
| React Frontend | ✅ Active | Pre |
| Tauri Desktop | ❌ Missing | Phase 2 |
| React Native Android | ❌ Missing | Phase 3 |
| Sync Engine | ❌ Missing | Phase 4 |
| Docker Compose | 💤 Dormant | Future |
| Kubernetes | 💤 Dormant | Future |
| Prometheus | 💤 Dormant | Future |
| Vercel | ⏸️ Paused | Phase 1 |

### 4.7 Platform Support

| Platform | Status | Phase |
| :--- | :--- | :--- |
| Browser | ✅ Active | Pre |
| Windows | ⏳ Planned | Phase 2 |
| Mac | ⏳ Planned | Phase 2 |
| Linux | ⏳ Planned | Phase 2 |
| Android | ⏳ Planned | Phase 3 |
| iOS | ❌ Missing | Future |

### 4.8 Summary Counts

| Category | Active | Dormant | Missing |
| :--- | :--- | :--- | :--- |
| Document Management | 15 | 0 | 7 |
| AI Features | 1 | 2 | 5 |
| Enterprise | 0 | 15 | 0 |
| Security | 7 | 0 | 6 |
| Deployment | 7 | 3 | 5 |
| Platform | 1 | 0 | 5 |
| **Total** | **31** | **20** | **28** |

---

## 5. AI Features Plan

### 5.1 AI Philosophy

> **AI recommends. Human approves. AI never performs destructive actions.**

AI is: Optional · Advisory · Fallible · Replaceable · Local-first

### 5.2 Provider Fallback
Gemini (Google)
↓ (if fails)

OpenRouter
↓ (if fails)

Groq
↓ (if fails)

OpenAI
↓ (if all fail)

Graceful degradation (no AI)

text

### 5.3 Phase 1–2 AI Feature Delivery

| Feature | Phase | Purpose | Boundary |
| :--- | :--- | :--- | :--- |
| AI Classification | Phase 1 (optional; currently dormant) | Auto-categorize | Suggest only |
| AI Auto-Tagging | Phase 1 | Extract entities | Advisory tags |
| Semantic Search | Phase 1 | Meaning-based search | Suggestions |
| Chat with Documents | Phase 2 | Q&A over collection | Read-only |
| AI Summarization | Phase 2 | Multi-document summaries | Advisory |
| Rule Engine (IF-THEN) | Phase 2 (optional; dormant until enabled) | Workflow automation | Never auto-approve/delete |

**AI remains optional and is never a mandatory dependency for core DMS use.**

### 5.4 AI Safety Rules

| Rule | Enforcement |
| :--- | :--- |
| AI cannot delete | No delete API |
| AI cannot move | No move API |
| AI cannot approve | No approval API |
| AI cannot modify source | Source read-only |
| Human review required | Approval gate |
| Disable-able | AI_ENABLED=false |
| Graceful fail | Try/except + fallback |
| Keys never committed | .env only |

### 5.5 Cost Estimation

| Provider | Model | Cost per 1M tokens |
| :--- | :--- | :--- |
| Gemini | gemini-pro | $0.50 |
| Groq | llama-3 | $0.10 |
| OpenAI | gpt-4o-mini | $0.15 |

**Estimate:** ~$5-20/month for personal use.

### 5.6 Configuration

```yaml
ai:
  enabled: false
  fallback_enabled: true
  max_retries: 3
  timeout_seconds: 30
  classification:
    enabled: true
    min_confidence: 0.7
  tagging:
    enabled: true
    max_tags: 10
  semantic_search:
    enabled: true
    embedding_model: "all-MiniLM-L6-v2"
    top_k: 10
  chat:
    enabled: true
    max_context_docs: 5
6. Enterprise Archive
6.1 Archive Locations
Path	Contents
archive/legacy-enterprise/backend/	Enterprise FastAPI routes
archive/legacy-enterprise/frontend/	Legacy React pages
archive/legacy-enterprise/config.yaml	Old config
infrastructure/	Docker, K8s, Terraform
mobile/	Mobile app
6.2 Archived Feature Groups
Multi-User & Access Control: RBAC, folder permissions, 2FA, SSO

Workflow & Automation: SOP, Reminders, Rule Engine, Email Alerts

Analytics & Reporting: Dashboard, Charts, Reports, Heatmap

Document Features: Versioning, Bulk Actions, Locking, SSE

Integrations: External API, Social Media Ingestion, Webhooks

Infrastructure: PostgreSQL, Redis, MinIO, Celery, Docker, K8s

AI Features: Chat, Summarization, Auto-Tagging, Semantic Search

6.3 Re-Activation Process
Amendment to Project Charter

Funding secured

Isolation (keep Personal Local intact)

Full validation gates

Data migration plan

Rollback plan

Owner sign-off

Est. Time: 4-8 weeks per group
Est. Cost: $75-230/month

6.4 Warning
Do NOT activate enterprise features in Personal Local runtime.

Wait until: funding secured + amendment approved + time is right.

7. Security Plan
7.1 Security Principles
Least Privilege

Defense in Depth

Fail Secure

Audit Everything

No Secrets in Code

Human Approval

7.2 Current Personal Local Security
Layer	Implementation	Status
Auth	Local JWT (HS256)	✅
Password Hashing	bcrypt	✅
Bootstrap Password	User-set, ≥12 chars	✅
Token Storage	localStorage	⚠️ Acceptable (local)
Source Protection	App-level read-only	✅
Path Traversal	Blocked	✅
Symlink Following	Blocked	✅
Encryption	Fernet (AES-128)	✅
Audit Logging	Local file	✅
CORS	localhost only	✅
7.3 Cloud Security (Phase 1)
Layer	Implementation	Status
Auth	Supabase Auth	✅
Database	Postgres RLS	✅
Storage	Private buckets + presigned URLs	✅
Worker Secrets	Cloudflare bindings	✅
Upload Sessions	HMAC-bound	✅
No Byte Proxy	Direct uploads	✅
Service-Role Key	Never committed	✅
VITE_* Values	Public only	✅
Leaked Password Protection	❌ DISABLED	🚨 FIX
7.4 Security Gaps
#	Gap	Risk	Fix
1	localStorage tokens	Medium	HttpOnly cookies
2	No token revocation	Medium	Redis blacklist
3	No rate limiting	High	slowapi
4	No OS-level ACL	Low	Windows ACL
5	Leaked password protection off	High	Enable in Supabase
6	Manifest-only download not enforced	Low	Verify before serve
7.5 Incident Response
Detect

Contain

Assess

Notify

Remediate

Document

Improve

### 7.7 Phase 1 Cloud Security Deliverables

The following are explicit Phase 1 security deliverables, not indefinite backlog
items:

1. Rate limiting target: **100 requests/minute** per appropriate authenticated
   identity/IP boundary.
2. HttpOnly, secure cookie-based session/token handling; do not rely on
   `localStorage` for Cloud authentication tokens.
3. Server-side token/session revocation on logout.
4. Manifest-only download enforcement: a document may be served only when the
   authorized metadata/manifest record permits it.
5. Supabase Leaked Password Protection enabled and verified.
6. Preserve RLS, private storage, HMAC upload sessions, no-byte-proxy, and
   secret-boundary rules.

### 7.8 Phase 2 Desktop Security Deliverables

- OS-level Source ACL on supported desktop platforms.
- Preserve the source read-only contract at the OS boundary as well as in app
  code.
- No desktop feature may bypass the core approval/safety workflow.

### 7.10 Legal & Compliance

The project must establish the following documents before broader external or commercial use:

| Document | Purpose | Target |
| :--- | :--- | :--- |
| Privacy Policy | Explain collection, processing, storage, retention, and user rights | Before external Cloud users |
| DPA | Define controller/processor responsibilities and data-processing terms | Before processing third-party/customer data |
| NDA | Protect confidential business/customer information | As required for contractors, partners, and customers |
| SLA | Define availability, support, recovery, and service commitments | Before paid/customer commitments |
| Data Retention & Deletion Policy | Define retention, deletion, backup expiry, and legal-hold boundaries | Before external Cloud users |

Legal text must be reviewed for the actual operating jurisdictions and business model. Do not claim GDPR, Myanmar privacy, SOC 2, ISO 27001, or other compliance certification merely because a policy document exists.

### 7.11 Monitoring & Alerting

**Cloud observability stack:**
- **Sentry:** application errors, frontend/backend exceptions, release regressions.
- **Prometheus:** infrastructure/application metrics where self-hosted metrics are appropriate.
- **Grafana:** dashboards and operational visualization.
- **Cloudflare observability/logs:** Worker requests, failures, latency, and deployment health.
- **Backup/recovery alerts:** failed backups, restore failures, hash mismatches, and RTO/RPO breaches.
- **Security alerts:** authentication anomalies, repeated authorization failures, rate-limit spikes, and storage/upload failures.

Alert priorities:
- P0: data-loss, authorization bypass, production-wide outage
- P1: major feature outage, backup/recovery failure
- P2: degraded performance or repeated non-critical errors
- P3: informational/development issues

Monitoring must not expose document contents, secrets, access tokens, or unnecessary personal data.

### 7.9 Compliance Roadmap
Standard	Target	Status
GDPR	Phase 5	❌
SOC 2	Phase 5	❌
ISO 27001	Phase 5	❌
Myanmar Data Privacy	Phase 5	❌
## 8. Validation Gates
8.1 Personal Local Gates (Pre-Phase)
Gate	Task	Status
PL-G1	Windows startup	⏳
PL-G2	Login	⏳
PL-G3	Small test folder	⏳
PL-G4	Safe import	⏳
PL-G5	OCR (English)	⏳
PL-G6	OCR (Myanmar)	⏳
PL-G7	Duplicate detection	⏳
PL-G8	Version family	⏳
PL-G9	Organization plan	⏳
PL-G10	Approve + Apply	⏳
PL-G11	Undo	⏳
PL-G12	Backup	⏳
PL-G13	Recovery	⏳
PL-G14	Search	⏳
PL-G15	Browser E2E	⏳
PL-G16	Real office dataset	⏳
PL-G17	OCR tuning (≥70%)	⏳
PL-G18	Search tuning	⏳
PL-G19	Tailscale VPN (opt)	⏳
PL-G20	Sign-off	⏳
8.2 Cloud Edition Gates (Phase 1)
Gate	Task	Status
CL-G1	Authenticated user flow	⏳
CL-G2	Two-user isolation	⏳
CL-G3	50 MiB boundary	⏳
CL-G4	B2 multipart (>5 GiB)	⏳
CL-G5	Cloudinary derivative	⏳
CL-G6	Google Drive drill	⏳
CL-G7	OCR benchmark	⏳
CL-G8	Backup → restore proof	⏳
CL-G9	Supabase leaked-password	⏳
CL-G10	One clean Vercel build	⏳
CL-G11	Legacy routes fail closed	⏳
CL-G12	Cloud Edition sign-off	⏳
8.3 Desktop Gates (Phase 2)
Gate	Task	Status
DE-G1	Windows build	⏳
DE-G2	Mac build	⏳
DE-G3	Linux build	⏳
DE-G4	Offline mode	⏳
DE-G5	Sync with cloud	⏳
DE-G6	Auto-update	⏳
DE-G7	Code signing	⏳
DE-G8	Sign-off	⏳
8.4 Android Gates (Phase 3)
Gate	Task	Status
AN-G1	APK build	⏳
AN-G2	Camera OCR	⏳
AN-G3	Offline storage	⏳
AN-G4	Push notifications	⏳
AN-G5	Biometric auth	⏳
AN-G6	Background sync	⏳
AN-G7	Play Store publish	⏳
AN-G8	Sign-off	⏳
8.5 Sync Gates (Phase 4)
Gate	Task	Status
SY-G1	Delta sync	⏳
SY-G2	Conflict resolution	⏳
SY-G3	Offline queue	⏳
SY-G4	Real-time push	⏳
SY-G5	Version vectors	⏳
SY-G6	File chunking	⏳
SY-G7	Bandwidth optimization	⏳
SY-G8	No data loss	⏳
SY-G9	Sign-off	⏳
8.6 Gate Rules
Sequential — pass in order

Documented — evidence required

Repeatable — reproducible

Reviewed — owner signs off

Logged — update records

9. Phase 1: Cloud Base
Status: 🔄 Verification / Go-Live Gates
Duration: 2-4 weeks
Goal: Web-based DMS accessible from any browser

9.1 Objectives
Build cloud DMS with:

Browser access anywhere

Secure storage

Myanmar + English OCR

User isolation

Files up to 5 GiB

Backup/recovery

9.2 Deliverables
Component	Technology	Status
API Gateway	Cloudflare Worker	✅ Ready
Auth	Supabase Auth	✅ Configured
Database	Supabase Postgres + RLS	✅ Configured
Small Storage	Supabase Storage	✅ Configured
Large Storage	Backblaze B2	⚠️ Verify
Images	Cloudinary	⚠️ Verify
Backup	Google Drive	⚠️ OAuth
Frontend	Vercel	⏸️ Paused

### 9.2.1 Phase 1 Explicit Feature Deliverables

**Document Management**
- Document Versioning (V1, V2, V3)
- Bulk Actions (multi-select approve/reject)
- Document Locking (prevent concurrent edits)
- Advanced Filters (date, type, size)
- Saved Searches (query history)

**AI (optional, never mandatory)**
- AI Auto-Tagging
- Semantic Search
- AI Classification (currently dormant; activation requires explicit enablement)
- Core AI advisory boundary remains human-approval-first

**Security**
- Rate Limiting (100 req/min target)
- HttpOnly Cookies
- Server-side Token Revocation
- Manifest-only Download Enforcement
- Supabase Leaked Password Protection
- Existing RLS/HMAC/private-storage/no-byte-proxy controls remain mandatory
9.3 Step-by-Step Plan
Week 1: Verification

Day 1: Enable and verify Supabase leaked-password protection

Day 2: Verify Cloudflare Worker live

Day 3: Test authenticated user flow (CL-G1)

Day 4: Test two-user isolation (CL-G2) with separate sessions

Day 5: Test 50 MiB boundary (CL-G3) including routing/rejection behavior

Week 2: Storage Providers

Day 1: Test B2 multipart >5 GiB (CL-G4) and recovery

Day 2: Test Cloudinary derivative (CL-G5) and fail-closed fallback

Day 3: Verify Google Drive OAuth (CL-G6)

Day 4: Test Google Drive export + recovery

Day 5: OCR benchmark (CL-G7) for Myanmar + English

Week 3: Recovery & Deployment

Day 1: Backup → restore → SHA-256 proof (CL-G8) + record RTO/RPO

Day 2: Legacy routes fail closed (CL-G11)

Day 3: One clean Vercel build (CL-G10) only when the owner confirms the rate-limit window is available

Day 4: Re-run all gates

Day 5: Sign-off (CL-G12)

Week 4: Buffer

Fix any failures

Document learnings

Prepare Phase 2

9.4 Upload Flow
text
User selects file → Client requests session → Worker returns HMAC token
→ Client uploads directly (≤50 MiB→Supabase, >50 MiB→B2)
→ Client calls completion → Worker verifies → Postgres metadata
→ OCR background → Classification → User review → Apply to Final
→ Audit → Sync push
9.5 Success Metrics
Metric	Target
Upload success	>99%
OCR accuracy	≥70%
Two-user isolation	100%
Backup/restore	100%
Vercel build	1 clean
Response time	<500ms
9.6 Blockers
Blocker	Owner
Supabase leaked-password	User
Vercel rate limit	User
B2 verification	Both
Cloudinary verification	Both
Google Drive OAuth	User

### 9.9 Local → Cloud Migration Path

Migration is a controlled, reversible transition. **Local remains the safety source until Cloud verification and hash checks are complete.**

1. **Export local data**
   - Export approved documents, metadata, versions, audit records, and backup manifests from Personal Local.
   - Preserve original source files and the local export as rollback copies.
2. **Set up Cloud account**
   - Create and verify the Cloud account/authentication boundary.
   - Confirm private storage, RLS, upload-session controls, and backup configuration.
3. **Upload to Cloud storage**
   - Route small files to Supabase Storage and large files to B2 according to the Phase 1 storage policy.
   - Upload copies only; never alter the original local source.
4. **Sync metadata**
   - Import document IDs, filenames, versions, tags, OCR/search metadata, approval state, and audit references.
5. **Verify hashes**
   - Recompute SHA-256 for every migrated document and compare with the local export manifest.
   - Any mismatch blocks migration completion.
6. **Switch primary**
   - After migration evidence passes, Cloud becomes the primary shared working library.
   - Local remains available as a retained rollback/reference copy until the owner approves retirement.
7. **Rollback**
   - If migration, integrity, permissions, or recovery validation fails, stop new Cloud writes, retain the Cloud copy for investigation, and restore working operations from the verified local dataset.
   - Reconcile only after the failure is understood; never overwrite the verified local source blindly.

**Migration exit criteria:** 100% required files accounted for, SHA-256 verification passed, metadata reconciled, permissions verified, backup/recovery evidence recorded, and owner sign-off obtained.

## 9.7 Current Go-Live Evidence

The implementation is in the branch-consolidated verification stage.

- PR #17 is merged and PR #19 was reconciled into `main` and closed.
- Remaining `fix/*` branches are historical working branches and may be deleted by the repository owner.
- The repository has no `vercel.json` override file; Vercel remains owner-controlled and intentionally paused.
- Cloudflare direct-upload routing is implemented without proxying document bytes through the Worker.
- Quality CI uses concurrency cancellation and excludes documentation-only root Markdown changes from its path allow-list.
- The Cloudflare production deploy workflow also cancels superseded runs on the same ref.
- Supabase Leaked Password Protection remains an explicit acceptance gate until enabled and verified.

## 9.8 Remaining Action List

1. Authenticated upload/list/update/download/version/restore/trash E2E.
2. Separate-session User A/User B isolation test.
3. 50 MiB routing boundary test.
4. Real B2 multipart and recovery drill.
5. Real Cloudinary derivative and fallback drill.
6. Google Drive OAuth export and recovery drill.
7. Myanmar + English OCR benchmark with measured accuracy.
8. Backup → restore → SHA-256 proof with RTO/RPO evidence.
9. Enable and verify Supabase Leaked Password Protection.
10. One clean Vercel build when the rate-limit window permits and only while Vercel remains owner-approved.
11. Re-run all Cloud Edition gates and record evidence.
12. Issue final sign-off only after all mandatory gates pass.

10. Phase 2: Desktop App
Status: ⏳ Pending
Duration: 4-8 weeks
Goal: Native desktop app with offline support

10.1 Technology Choice
Recommended: Tauri

Aspect	Tauri	Electron
Size	~10 MB	~150 MB
RAM	Low	High
Speed	Fast	Slower
Security	Better	Good
10.2 Deliverables
Windows installer (.exe/.msi)

Mac installer (.dmg)

Linux installer (.AppImage)

Embedded FastAPI + SQLite

Offline mode

Local ↔ Cloud sync

Auto-update

Code signing

### 10.2.1 Phase 2 Explicit Feature Deliverables

**Document Management**
- Continue Cloud document versioning on-device
- Bulk Actions
- Document Locking for concurrent offline edits
- Advanced Filters
- Saved Searches
- **Document Watermark remains Phase 5 only**

**AI (optional)**
- Chat with Documents (RAG + LLM)
- AI Summarization (multi-document)
- Rule Engine (IF-THEN) as an optional, dormant-by-default capability
- Semantic Search/embeddings available offline where practical

**Security**
- OS-level Source ACL
- Desktop secure credential/session storage
- Preserve read-only source and human-approval boundaries

10.3 Step-by-Step Plan
Week 1-2: Setup — Install Rust + Tauri, embed React + FastAPI + SQLite
Week 3-4: Offline — Local storage, OCR, search, offline queue
Week 5-6: Sync — Cloud API, delta sync, conflict resolution, real-time
Week 7-8: Polish — Auto-update, code signing, installer, testing

10.4 Success Metrics
Metric	Target
App size	<50 MB
Startup	<3s
Offline	100% functional
Sync latency	<5s
11. Phase 3: Android App
Status: ⏳ Pending
Duration: 6-10 weeks
Goal: Mobile scan + approve + sync

11.1 Technology Choice
Recommended: React Native

11.2 Deliverables
Android APK/AAB

Camera OCR (on-device)

Offline storage

Push notifications

Biometric auth

Background sync

Play Store deployment

11.3 Step-by-Step Plan
Week 1-2: Setup — React Native, navigation, auth, API client
Week 3-4: Camera + OCR — Camera, on-device OCR, preprocessing, multi-page
Week 5-6: Offline — Local DB, queue, sync, conflict
Week 7-8: Notifications — Firebase, push, background, biometric
Week 9-10: Polish — UI, testing, Play Store prep, release

11.4 Success Metrics
Metric	Target
APK size	<30 MB
OCR accuracy	≥70%
Offline	100%
Sync latency	<10s
Crash rate	<1%
12. Phase 4: Sync Engine
Status: ⏳ Pending
Duration: 4-6 weeks
Goal: All platforms sync together seamlessly

This is the HARDEST phase.

12.1 Deliverables
Delta sync (changes only)

Conflict resolution

Offline queue

Real-time push (WebSocket/SSE)

Version vectors

File chunking

Bandwidth optimization

### 12.1.1 North-Star Sync Deliverables

- One user account works across **Cloud + Desktop + Android**.
- The same document/data state is available across all three platforms.
- Desktop and Android support offline work with a durable local queue.
- Cloud is the authoritative shared source of truth; clients reconcile safely.
- Conflict resolution never silently destroys data.
- Document versions, approvals, metadata, and audit history remain consistent
  across platforms.

12.2 Sync Protocol
text
Device A changes file
→ Compute delta
→ Generate version vector
→ Push to server
→ Server broadcasts
→ Device B receives delta
→ Check conflicts
  ├── No conflict → Apply
  └── Conflict → User resolves
→ Acknowledge
12.3 Conflict Resolution
Strategy	When
Last-Write-Wins	Non-critical metadata
User Choice	Document content
Merge	Text documents
Keep Both	Cannot merge
12.4 Version Vectors
text
Each device has unique ID
Each change increments counter
Vector = {device_A: 5, device_B: 3, device_C: 7}
Compare: A>B all → A newer; A<B all → B newer; mixed → conflict
12.5 Success Metrics
Metric	Target
Sync latency	<5s
Conflict rate	<1%
Data loss	0%
Offline→Online	<30s
13. Contributing Rules
13.1 Current Development Target
Active milestone: **Cloud Base (Phase 1)**

Foundation: Personal Local Edition (safety/reference foundation; must remain
validated)

Next: Desktop App (Phase 2) → Android App (Phase 3) → Sync Engine (Phase 4)

Locked: Enterprise (Phase 5, Dormant Until Funded)

13.2 Safety Boundary (Keep Intact)
□ Original source read-only
□ Writable ops inside workspace only
□ Organization copies to Final (no source modification)
□ AI optional, disabled by default
□ Enterprise/cloud not reintroduced to Personal Local
13.3 Development Prerequisites
Python 3.12

Node.js 24.x

Git

Tesseract OCR

Docker (optional)

13.4 Validation Checklist
Before completing a change:

□ Python syntax checks pass
□ Local safety regression tests pass
□ Frontend build + smoke test passes
□ FastAPI entry point starts
□ Frontend only calls Personal Local endpoints
□ Document workflow: source unchanged
□ Cloud: Worker/storage boundary verified
□ No server-side secrets exposed
13.5 Branch and Merge Policy
main = consolidated production branch

PR #17 merged

PR #19 reconciled and closed

fix/* branches = historical

13.6 Commit Message Format
text
<type>(<scope>): <subject>
Types: feat, fix, docs, refactor, test, chore

13.7 PR Requirements
Reference a gate

Not violate SAFETY_RULES

Update FEATURE_MATRIX if feature added

Not delete archive code

Pass CI

Update CHANGELOG

### 13.9 Phase-by-Phase Rollback Plan

| Phase | Rollback trigger | Procedure |
| :--- | :--- | :--- |
| Phase 0 — Personal Local Foundation | Safety regression or failed PL gate | Stop release; restore last validated local code/config; keep source read-only; rerun failed PL gates before proceeding. |
| Phase 1 — Cloud Base | Auth/isolation/storage/recovery failure | Stop go-live; disable affected Cloud write paths; retain verified local/export copies; restore from last verified backup; revert deployment/config to last known-good version. |
| Phase 2 — Desktop | Installer/offline/security regression | Withdraw affected build; keep previous signed build available; preserve local database and source; restore last known-good app version and reconcile only after validation. |
| Phase 3 — Android | Crash/data/sync regression | Halt rollout; keep previous Play Store version available; disable affected background-sync feature if necessary; preserve local queue and recover from last verified state. |
| Phase 4 — Sync Engine | Conflict/data-loss risk | Stop sync writes/queue processing; preserve per-device queues and server state; return to last verified synchronization protocol/version; reconcile manually before resuming. |
| Phase 5 — Enterprise | Any unsafe activation or failed gate | Do not activate; if already activated under an approved amendment, isolate Enterprise routes/data, disable new writes, restore previous supported configuration, and follow the approved migration/rollback plan. |

**Universal rollback rules:** never delete original source files, never overwrite the only verified copy, preserve audit evidence, record the incident, and require validation before re-enabling the affected capability.

### 13.10 Support Plan

| Area | Plan |
| :--- | :--- |
| User documentation | Quickstart, installation, cloud setup, migration, backup/recovery, troubleshooting, and safety guides |
| Training | Short operator training for import → review → approve → apply → backup/recovery workflow |
| Support structure | Single-owner support initially; formal support queue/process when external users are introduced |
| Incident handling | Severity-based P0–P3 response, evidence collection, containment, remediation, and post-incident review |
| Release support | Changelog, known-issues list, rollback version, and migration notes for each release |
| Recovery support | Documented backup/restore drills and recovery contact/procedure |
| Feedback | Capture bugs, usability issues, feature requests, and safety concerns separately |

Support documentation must reinforce the safety model: originals remain protected, AI is optional, and human approval is required for destructive/organizational actions.

13.8 Legacy Enterprise Code
Preserve in archive/legacy-enterprise/

Do not delete

Do not import into Personal Local

Do not route legacy pages

14. Change Log
[Unreleased]
Consolidated documentation into single Master Roadmap
Added explicit Phase 0 foundation alignment without duplicating PL-G1 to PL-G20
Added Local → Cloud migration, service cost planning, phase rollback, legal/compliance, monitoring/alerting, and support planning

Added all 15 original files' content

Structured for AI verification

[0.1.0] - 2026-10-01
Personal Local Edition (code complete)

Safe import with SHA-256

OCR (eng + mya)

Duplicate detection

Version family detection

Organization planner

Manual review UI

Undo, backup, recovery

Search

Local JWT auth

21 hardening tasks

[0.0.1] - 2026-09-01
Initial project setup

Enterprise Edition code (now archived)

Cloud Edition code (verified separately)

15. Final Declaration
15.1 Project Current State
Aspect	Status
Code Foundation	✅ Complete
CI	✅ Green
Architecture	✅ Stable
Safety Model	✅ In Place
Documentation	✅ In Place
Real-Machine Test	⏳ Not Yet
Real Office Data	⏳ Not Yet
15.2 Next Milestone
The next milestone is evidence-based release validation:

Run remaining authenticated, isolation, provider recovery, OCR, backup, Supabase security, and Vercel checks. Issue final go-live sign-off only when ALL required gates pass.

15.3 Core Policy
Safety First · Cloud Base First · Human Approval First · AI Optional ·
Legacy Preserved · Validation Gates Always

15.4 North Star — Multi-Platform Unified System
The final target is one unified DMS where the **same user account** works on
Cloud + Desktop + Android, the **same data synchronizes across all three**,
Desktop and Android support **offline mode**, and there is **one source of
truth** with safe conflict resolution and no silent data loss.

15.5 Long-Term Vision
A professional AI-assisted DMS that can take a messy office document environment and safely transform it into a structured, searchable, understandable document library without risking the original files.

15.6 What NOT to Do
❌ Migrate to Next.js without concrete requirement

❌ Replace FastAPI without concrete requirement

❌ Add PostgreSQL/Redis/MinIO to Personal Local

❌ Add Supabase to Personal Local

❌ Expose backend publicly

❌ Make AI mandatory

❌ Let AI auto-delete files

❌ Organize directly on D:

❌ Delete legacy features

❌ Randomly restructure repository

❌ Add large UI before core validated

❌ Claim production-ready before real-machine testing

15.7 Immediate Next Steps
#	Action	Owner	Time
1	Run start_application.bat on Windows	User	15 min
2	Small test folder (5-20 files)	User	30 min
3	Test Import + SHA-256	User	30 min
4	Test OCR (Myanmar + English)	User	30 min
5	Enable Supabase leaked-password protection	User	30 min
6	One clean Vercel build	User	1 hour
7	Real office dataset test	User	1 day
8	Phase 1 Cloud Gates (CL-G1 to CL-G12)	Both	2-4 weeks
**Roadmap phase order:** Cloud Base → Desktop → Android → Sync Engine → Enterprise (locked/dormant until funded).

**Non-negotiable constraints:** Do not activate Enterprise; do not delete legacy
code; do not skip validation gates; do not weaken R1-R10; do not auto-delete or
auto-approve; do not expose the backend publicly; do not make AI mandatory.

Signed: ________________________
Date: 2026-10-06
Version: 1.0 (Locked)
Status: ACTIVE — Single Source of Truth
