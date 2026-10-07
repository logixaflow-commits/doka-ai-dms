# Doka UI Design System

## Product UI boundary
The active UI is a React 19 + TypeScript + Vite 7 application. Personal Local and Personal Cloud are separate navigation/runtime boundaries. Incomplete Enterprise/Mobile routes are not active production UI.

## Brand and visual tokens
Use the existing application tokens and Tailwind CSS 4.3.3 utilities as the implementation source of truth. Do not invent token values in documentation that are not present in the code.

## Typography, spacing, radius, shadow
Use the values already defined by the frontend's Tailwind/theme/component classes. New tokens must be introduced in code first, then documented here.

## Component contract
Active reusable UI patterns include cards, KPI/status blocks, buttons, inputs, tables, badges, alerts, tabs, modal/dialog surfaces, progress/loading states, empty states and error states. Radix UI primitives, Lucide icons, class-variance-authority, clsx and tailwind-merge are part of the current frontend stack.

## Layout
Primary application structure uses authenticated navigation/sidebar/topbar/main-content patterns where implemented. Personal Local Safe Workspace navigation must remain local-only; Cloud navigation must not expose local filesystem actions.

## Responsive and accessibility
Required acceptance widths: 320, 375, 390, 768, 1024 and 1440px. Preserve no-horizontal-overflow behavior, keyboard navigation, visible focus, accessible labels, sufficient contrast, 44px-class touch targets where applicable, screen-reader semantics and reduced-motion-safe behavior.

## Screens inventory
- Login.
- Dashboard/status.
- Safe Workspace.
- Import.
- Scan/OCR.
- Review plan.
- Approval.
- Final/organized workspace.
- Backup.
- Recovery.
- Cloud document library where the Cloud edition is enabled.

Implementation status must be verified from mounted routes and runtime behavior; documentation must not convert a component into a completed feature merely because source files exist.

## UI completion rule
A feature is complete only when its intended edition mounts it, navigation exposes it correctly, API/authz exists, loading/empty/success/error/disabled states exist, responsive/accessibility behavior is tested, regression coverage exists, and release-critical browser evidence passes.
