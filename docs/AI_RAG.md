# Doka AI and RAG

> **Owner:** How are AI providers, agents, RAG, privacy and publication safety governed?
> **Update when:** AI provider adapters, routing, agent boundaries, RAG behavior, consent or AI security controls change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Current release-gate status, provider secrets, deployment credentials, or generic operational runbooks.

## Default posture
AI is disabled by default. External document processing requires explicit consent in addition to the global AI enable flag. Provider credentials remain server-side.

## Provider boundary
Implemented provider adapters are not automatically configured, enabled, live-tested or production-approved. Unsupported providers fail closed.

The current architecture includes provider routing/fallback logic and schema validation for AI document output. Embedding routing honors configured provider order and can fall back to deterministic local similarity where designed.

## Agent boundary
Reader: source reading, OCR/metadata extraction and duplicate/version clues; no writes.
Planner: recommendations and plans; no destructive writes.
Human Approval: required for publication-sensitive organization decisions.
Executor: deterministic approved actions only.

## RAG status
RAG ingest/embed/search capabilities exist in the repository, but live end-to-end verification and durable alert/feedback history remain release/future gates as specified by ROADMAP.md.

## Safety
Never infer live provider health from an API key alone. Never let AI bypass source immutability, ownership, human approval or deterministic executor checks.
