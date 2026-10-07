# Doka AI Provider Matrix

Last reconciled: 2026-10-07

## Design decision

Do **not** use 7–8 AI APIs interchangeably for every task. That increases cost, failure modes, debugging complexity and privacy exposure.

Use **role-based routing** with a small fallback chain.

### Agent boundary

**Reader → Planner → Executor**

- Reader: read-only source inspection/OCR/extraction.
- Planner: structured recommendation only.
- Executor: only acts on a human-approved plan.

No AI agent may directly mutate the original source. Executor operations remain copy-only, bounded to the workspace, audited and undoable.

## Provider roles

| Provider | Current template | Best role | Default | Notes |
|---|---|---|---|---|
| Gemini | Yes | multimodal reading/classification | Candidate primary | Good fit for document/image understanding; must benchmark Myanmar data |
| Groq | Yes | fast text classification/planning | Candidate fast path | Use for low-latency text tasks; verify model/API availability |
| OpenRouter | Yes | fallback/aggregator | Candidate fallback | Useful as a single fallback boundary, not as another always-on provider |
| OpenAI | Yes | high-quality structured planning/extraction | Optional premium fallback | Keep behind explicit consent/budget |
| Hugging Face | Yes | embeddings/local semantic similarity | Local-first | Current MiniLM model should not be assumed Myanmar-strong; benchmark before semantic search |
| NVIDIA | Planned | specialized model provider | Off | Do not enable until adapter + endpoint + cost are verified |
| Cerebras | Planned | fast inference | Off | Same rule |
| Cohere | Planned | embeddings/reranking | Off | Same rule |
| Voyage | Planned | embeddings/reranking | Off | Same rule |
| Mistral | Planned | general/structured inference | Off | Same rule |
| Cloudflare | Planned | Workers AI / cloud-native inference | Off | Cloud-only optional route; never required by Personal Local |

## Recommended routing

Provider selection is **task-based**, not one global key:

| Task | Primary chain | Fallback policy |
|---|---|---|
| Multimodal reading | Gemini | local OCR → one configured text fallback → human review |
| Fast classification | Groq | Cerebras when configured → Gemini → local rules |
| High-quality planning | OpenAI | Gemini → Groq → OpenRouter |
| Embeddings/similarity | Hugging Face | Voyage/Cohere only after their adapters are implemented and benchmarked → local TF-IDF |
| Cloudflare-native inference | Cloudflare Workers AI | opt-in cloud route only; never required by Personal Local |

A provider being listed here does **not** mean its key is enabled. Each provider must pass adapter, health, quality, privacy and cost checks before entering a production chain.

### 1. Read / OCR
Use local Tesseract + deterministic extractors first.

AI is only a fallback/enrichment layer when:
- `AI_ENABLED=true`
- `AI_EXTERNAL_PROCESSING_CONSENT=true`
- the user has explicitly accepted external processing.

### 2. Classification / metadata
Prefer a fast provider for low-risk text. Gemini is a candidate for multimodal cases.

### 3. Duplicate/version analysis
Do **not** spend API calls by default. Use SHA-256, filename/version rules, local TF-IDF and local embeddings first. Escalate only ambiguous cases.

### 4. Organization planning
The planner may propose folder/name/category changes as structured JSON. It must not execute them.

### 5. Execution
No AI provider is required. The executor uses the approved plan and deterministic filesystem safety checks.

## Fallback policy

A provider chain should be short:

**Primary → one fallback → local/rule-based review**

Do not make a 7-provider waterfall by default.

Every AI call should record:
- provider
- model
- task
- latency
- success/failure class
- token/usage metadata where available
- consent state
- redaction/privacy mode

Never record:
- API keys
- raw secrets
- full document contents in normal telemetry
- sensitive document paths when avoidable.

## Current live finding

As of 2026-10-07, the live Cloudflare Worker secret inventory contains B2, Cloudinary, Google Drive and Supabase bindings, but **no AI-provider secret bindings**. Therefore the cloud AI path should be treated as disabled/unconfigured.

The local backend template contains five currently declared AI credentials (Gemini, OpenRouter, Groq, OpenAI, Hugging Face) plus planned configuration for Mistral, Cerebras, NVIDIA, Cohere, Voyage and Cloudflare. Planned credentials do not enable a provider. Actual local `.env` values are not available in Git and must be tested locally without exposing secrets.

## Agent implementation audit

Before claiming the existing “source-reading agent / work agent” split is production-ready, verify in code that:

1. Reader has no write-capable filesystem tool.
2. Planner cannot call copy/move/delete.
3. Executor accepts only an approved, validated plan.
4. Original source is outside executor write roots.
5. Every mutation has an audit event and undo/recovery path.
6. External AI is blocked without consent.
7. Provider selection is task-aware rather than one global key for everything.

If the current code already follows these boundaries, document the exact module paths in this matrix; otherwise refactor toward them before enabling external AI.


## Current safety contract

- Document-analysis provider output is schema-validated before it enters Doka workflow state; malformed JSON or invalid field types trigger provider fallback instead of being accepted.
- Embedding routing follows `AI_EMBEDDING_PROVIDER_ORDER`. Only providers with a dedicated adapter are eligible; unsupported configured names remain fail-closed.
- Similarity has a deterministic local fallback so Personal Local does not require external embedding availability.


### Provider resilience

Implemented providers use a per-process circuit breaker: after the configured consecutive-failure threshold, a provider is skipped during the cooldown window and retried in half-open mode afterward. A successful probe closes the circuit. Fallback order remains capability-specific, and Personal Local still has a local/rule-based path when external AI is unavailable.
