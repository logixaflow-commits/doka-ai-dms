# Doka AI and RAG

> **Owner:** How are AI providers, agents, RAG, privacy and publication safety governed?
> **Update when:** AI provider adapters, routing, agent boundaries, RAG behavior, consent or AI security controls change.
> **Last Updated:** 2026-10-09
> **Do NOT put here:** Current release-gate status, provider secrets, deployment credentials, or generic operational runbooks.

## Default posture
AI is disabled by default. External document processing requires explicit consent in addition to the global AI enable flag. Provider credentials remain server-side.

## Provider boundary
Implemented provider adapters are not automatically configured, enabled, live-tested or production-approved. Unsupported providers fail closed.

The current architecture includes provider routing/fallback logic and schema validation for AI document output. Embedding routing honors configured provider order and can fall back to deterministic local similarity where designed. Provider circuit state is currently process-local; this is not yet a distributed health registry or a production failover proof.


## Free-only model and billing boundary

Doka's unified provider adapter now enforces a free-only OpenRouter policy (merged to `main` in PR #24):
- Generic document analysis accepts only the explicit free chat-model allowlist or `openrouter/free`.
- Embeddings use the OpenRouter free embedding allowlist, defaulting to `liquid/lfm-2.5-embedding-350m:free`.
- Gemini, Groq, OpenAI, Hugging Face Inference API, and other provider adapters are not called by the unified service. Their environment keys, if present, do not activate those routes.
- If the free model/key is unavailable or the request fails, semantic similarity may fall back to deterministic local processing; it must not silently switch to a billable provider.
- Embedding, reranking, content-safety, and audio models are task-specific and must not be sent to the generic chat-completions endpoint.

The `:free` model suffix indicates OpenRouter's free model variant; `openrouter/free` is its free-model router. Free capacity can still have request limits, availability changes, or provider-side errors. Never use a paid model ID as a fallback. Keep AI disabled unless both `AI_ENABLED` and explicit external-processing consent are enabled.

A configured key is not proof of reachability, zero cost, or deployment. Verify key presence through the intended server-side secret store, then run a minimal non-sensitive smoke request and confirm zero-priced model usage in the OpenRouter dashboard. Never log or expose the key.

## Agent boundary
Reader: source reading, OCR/metadata extraction and duplicate/version clues; no writes.
Planner: recommendations and plans; no destructive writes.
Human Approval: required for publication-sensitive organization decisions.
Executor: deterministic approved actions only.

## RAG status
RAG ingest/embed/search capabilities exist in the repository, but live end-to-end verification and durable alert/feedback history remain release/future gates as specified by ROADMAP.md.

## Safety
Never infer live provider health from an API key alone. Never let AI bypass source immutability, ownership, human approval or deterministic executor checks.
