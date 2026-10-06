# Doka — Master Roadmap (Complete Single-File Documentation)

**Version:** 1.0  
**Last Updated:** 2026-10-06  
**Status:** ACTIVE — Single Source of Truth  
**Owner:** Single User (Logixa Flow)  
**Repository:** logixaflow-commits/enterprise-ai-dms  
**Purpose:** Consolidated roadmap for AI verification + human reference

---

## 📖 Table of Contents

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
| Cloud Edition | ⚠️ Partial (gated) |
| Vercel Deployment | ⏸️ Paused (owner-controlled) |
| Real-Machine Validation | ❌ Not Started |
| Production Sign-off | ❌ Not Issued |

### 1.3 Current Phase
Phase: PERSONAL LOCAL
Users: 1 (Owner only)
Deployment: Local machine (Windows)
Network: Localhost only
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
| Rule Engine (IF-THEN) | 💤 Dormant | Phase 5 |
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

**Activation:** Requires funding + Amendment.

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
| Leaked Password Protection | ❌ Missing | Phase 1 |

### 4.6 Deployment & Infrastructure

| Feature | Status | Phase |
| :--- | :--- | :--- |
| Local Filesystem | ✅ Active | Pre |
| Supabase Storage | ✅ Active | Phase 1 |
| Backblaze B2 | ✅ Active | Phase 1 |
| Cloudinary | ✅ Active | Phase 1 |
| Google Drive | ✅ Active | Phase 1 |
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

### 5.3 Phase 1 AI Features

| Feature | Purpose | Boundary |
| :--- | :--- | :--- |
| Classification | Auto-categorize | Suggest only |
| Auto-Tagging | Extract entities | Advisory tags |
| Semantic Search | Meaning-based search | Suggestions |
| Chat with Docs | Q&A over collection | Read-only |
| Summarization | Summarize long docs | Advisory |

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

7.6 Compliance Roadmap
Standard	Target	Status
GDPR	Phase 5	❌
SOC 2	Phase 5	❌
ISO 27001	Phase 5	❌
Myanmar Data Privacy	Phase 5	❌
8. Validation Gates
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
Status: 🔄 Ready to Start
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
9.3 Step-by-Step Plan
Week 1: Verification

Day 1: Enable Supabase leaked-password protection

Day 2: Verify Cloudflare Worker live

Day 3: Test authenticated user flow (CL-G1)

Day 4: Test two-user isolation (CL-G2)

Day 5: Test 50 MiB boundary (CL-G3)

Week 2: Storage Providers

Day 1: Test B2 multipart >5 GiB (CL-G4)

Day 2: Test Cloudinary derivative (CL-G5)

Day 3: Setup Google Drive OAuth (CL-G6)

Day 4: Test Google Drive export + recovery

Day 5: OCR benchmark (CL-G7)

Week 3: Recovery & Deployment

Day 1: Backup → restore → SHA-256 proof (CL-G8)

Day 2: Legacy routes fail closed (CL-G11)

Day 3: One clean Vercel build (CL-G10)

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
Active: Personal Local Edition (main)

Deferred: Cloud Edition (verified separately)

Archived: Enterprise (preserved)

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

13.8 Legacy Enterprise Code
Preserve in archive/legacy-enterprise/

Do not delete

Do not import into Personal Local

Do not route legacy pages

14. Change Log
[Unreleased]
Consolidated documentation into single Master Roadmap

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
Safety First · Local First · Human Approval First · AI Second · Cloud Later

15.4 Long-Term Vision
A professional AI-assisted DMS that can take a messy office document environment and safely transform it into a structured, searchable, understandable document library without risking the original files.

15.5 What NOT to Do
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

15.6 Immediate Next Steps
#	Action	Owner	Time
1	Run start_application.bat on Windows	User	15 min
2	Small test folder (5-20 files)	User	30 min
3	Test Import + SHA-256	User	30 min
4	Test OCR (Myanmar + English)	User	30 min
5	Enable Supabase leaked-password protection	User	30 min
6	One clean Vercel build	User	1 hour
7	Real office dataset test	User	1 day
8	Phase 1 Cloud Gates (CL-G1 to CL-G12)	Both	2-4 weeks
Signed: ________________________
Date: 2026-10-06
Version: 1.0 (Locked)
Status: ACTIVE — Single Source of Truth
