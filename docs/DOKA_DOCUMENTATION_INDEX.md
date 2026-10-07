# Doka Documentation Index

Last reconciled: 2026-10-07

> **Start here:** [`MASTER-ROADMAP.md`](../MASTER-ROADMAP.md). It is the live status dashboard. Do not create separate phase-status MD files.

## Canonical execution documents

| Document | Purpose | Authority |
|---|---|---|
| MASTER-ROADMAP.md | Live status dashboard, 12 release gates, update/reminder contract | Canonical front door |
| docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md | Detailed execution order, issue register, release gates and evidence | Canonical detailed execution |
| docs/DOKA_PHASE_A_TO_E_STATUS.md | Historical A-E acceptance/evidence record | Evidence history |
| docs/legacy/PERSONAL_LOCAL_MASTER_PLAN.md | Original Personal Local feature decomposition | Historical reference only |
| docs/legacy/DOKA_MASTER_PRODUCT_PLAN.md | Older product/cloud roadmap and implementation inventory | Historical reference only |

## Current product/runtime documentation

| Document | Purpose |
|---|---|
| README.md | Project entry point and high-level product boundary |
| QUICKSTART.md | Local setup and safe first-run procedure |
| docs/PERSONAL_LOCAL_RUNBOOK.md | Local operating, backup/recovery and pilot runbook |
| docs/UI.md | Active route map, workflow states and UI completion contract |
| docs/ARCHITECTURE.md | Current Local vs Cloud architecture boundary |
| docs/TOOLS.md | Tools/services and operational boundaries |
| docs/ENVIRONMENT_MATRIX.md | Live environment/key ownership and findings | Current operational inventory |
| docs/AI_PROVIDER_MATRIX.md | AI provider routing and Reader/Planner/Executor boundary | Current AI policy |
| docs/REPOSITORY_STRUCTURE.md | Repository layout and hygiene rules |

## Security and cloud contracts

| Document | Purpose |
|---|---|
| SECURITY.md | Repository/security/deployment controls |
| docs/DOKA_CLOUD_API_CONTRACTS.md | Cloud API endpoint and security contract |
| docs/DOKA_SUPABASE_SECURITY_REVIEW.md | Supabase RLS/grant/security review |
| docs/DOKA_FREE_CLOUD_ARCHITECTURE.md | Free-first cloud architecture decision |
| docs/DOKA_FASTAPI_CLOUD_DEPLOYMENT.md | Deferred/optional FastAPI cloud deployment boundary |

## Design/deferred documents

Enterprise, AI, mobile and other legacy design documents remain valid only for their stated scope. They must not be treated as active runtime features unless the unified roadmap explicitly moves them into the active release path.

## Documentation rules

1. Code state and documentation must not contradict each other.
2. Every release-critical change updates the relevant source-of-truth document.
3. Distinguish implemented, verified, pending verification and deferred.
4. Do not claim production readiness from CI alone.
5. Do not document Vercel as active production deployment while the owner-controlled pause remains in effect.
6. New UI feature = API/security contract + UI state + tests + documentation.
7. Material architecture changes update ARCHITECTURE.md and the unified roadmap.
8. Tool/service changes update TOOLS.md and the affected operational/security document.
9. Do not create a new MD for each completed phase. Update MASTER-ROADMAP.md and the relevant focused document instead.
10. Move superseded master plans to docs/legacy/ after checking unique content and references.

## Missing/intentional documents

ui.md and tool.md did not previously exist as dedicated current documents. Their canonical replacements are docs/UI.md and docs/TOOLS.md. A separate root-level TOOL.md is not necessary; keeping operational documentation under docs/ avoids root clutter.

## Final documentation goal

At final release, a new maintainer should be able to start from README.md, follow this index, understand the Local/Cloud boundary, reproduce the safe workflow, identify every remaining release gate, and find the exact evidence required to close it.