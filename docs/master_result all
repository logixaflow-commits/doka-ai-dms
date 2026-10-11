# AI Provider Status Report

**Date:** 2026-10-11
**Method:** Live API calls (Python + requests)
**Total:** 11 providers | **Working:** 8 ✅ | **Partial:** 1 ⚠️ | **Failed:** 2 ❌

---

## TL;DR

Production AI capability **ready** — provider ၈ ခု live-tested။
Primary chain: **Groq → Cloudflare → Cohere → Gemini**။
HuggingFace Inference ပိတ် (Oct 8) — Hub/Spaces/Datasets ပဲ သုံး။
Cerebras/Canva မရ — billing/invalid။
**Blocker:** RAG dimension (Voyage 512 ≠ DB 768) + Publishing E2E။

---

## 1. Final Status Table

| # | Provider | Status | Chat | Embed | Image | Speech |
|---|---|---|---|---|---|---|
| 1 | **Gemini** | ✅ | ✅ | — | — | — |
| 2 | **Groq** | ✅ | ✅ | — | — | ✅ |
| 3 | **Cloudflare** | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | **Cohere** | ✅ | ✅ | ✅ | — | — |
| 5 | **Mistral** | ✅ | ✅ | — | — | — |
| 6 | **Voyage** | ✅ | — | ✅ | — | — |
| 7 | **OpenRouter** | ✅ | ✅ | — | — | — |
| 8 | **NVIDIA** | ✅ | ✅ | — | — | — |
| 9 | **HuggingFace** | ⚠️ PARTIAL | ❌ | ❌ | ❌ | ❌ |
| 10 | **Cerebras** | ❌ | ❌ | — | — | — |
| 11 | **Canva** | ❌ | ❌ | — | — | — |

---

## 2. Live Test Results

### ✅ Gemini
| Model | Status | Reply |
|---|---|---|
| gemini-3.5-flash | 200 ✅ | "OK" |
| gemini-3.5-flash-lite | 200 ✅ | "OK" |
| gemini-3.1-flash-lite | 200 ✅ | "OK" |
| gemini-3.8-flash | 200 ✅ | "OK" |
| gemini-flash-latest | 503 ❌ | — |

**Notes:** VPN လိုတယ်၊ `thinkingBudget=0` ထားရမယ်၊ Working keys ၄ ခု

### ✅ Groq
| Model | Status | Reply |
|---|---|---|
| qwen/qwen3.8-27b | 200 ✅ | "OK" |
| openai/gpt-oss-120b | 200 ⚠️ | (empty — max_tokens နည်း) |
| openai/gpt-oss-20b | 200 ⚠️ | (empty) |
| openai/gpt-oss-safeguard-20b | 200 ⚠️ | (empty) |
| allam-2-7b | 200 ✅ | — |

**Notes:** VPN ပိတ်ရမယ်၊ gpt-oss models တွေမှာ `max_tokens: 500+` ထား

### ✅ Cloudflare Workers AI
| Model | Status | Reply |
|---|---|---|
| @cf/meta/llama-3.1-8b-instruct | 200 ✅ | "OK" |
| @cf/meta/llama-3.2-3b-instruct | 200 ✅ | "OK" |
| @cf/mistral/mistral-7b-instruct-v0.2-lora | 200 ✅ | reply |
| @cf/openai/gpt-oss-120b | 200 ✅ | "OK" |

**Available (30+):** chat, embedding (`bge-m3`), image (`flux`), speech (`whisper`, `melotts`), vision (`llava`)

### ✅ Cohere
| Model | Status | Reply |
|---|---|---|
| command-a-03-2025 | 200 ✅ | "OK!" |
| command-r-08-2024 | 200 ✅ | reply |
| command-r7b-12-2024 | 200 ✅ | "OK!" |

### ✅ Mistral
| Model | Status | Reply |
|---|---|---|
| ministral-8b-latest | 200 ✅ | "OK!" |
| codestral-latest | 200 ✅ | "OK!" |
| mistral-small-latest | 429 ⚠️ | Rate limit |

### ✅ OpenRouter
| Model | Status | Reply |
|---|---|---|
| apodex/apodex-1.1-mini:free | 200 ✅ | "OK" |
| dots-studio/dots-3-note-preview:free | 200 ✅ | "OK" |
| liquid/lfm-2.5-2.6b:free | 200 ✅ | "OK" |
| nvidia/nemotron-3.5-lightning:free | 200 ✅ | "OK" |
| inclusionai/ling-3.1-flash | 429 ⚠️ | — |

**Free models:** 19 | **Limit:** 50 req/day

### ✅ NVIDIA NIM
| Model | Status | Reply |
|---|---|---|
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | 200 ✅ | "OK" |
| nvidia/nemotron-3.5-lightning-30b-a3b | 200 ✅ | reply |
| meta/llama-3.2-11b-vision-instruct | 200 ✅ | "OK" (vision) |
| nvidia/nemotron-3-super-120b-a12b | 200 ⚠️ | parse err |
| 17+ models | 404 ❌ | "Not found for account" |

**Notes:** Build.nvidia.com မှာ "Request Access" နှိပ်ရမယ်

### ✅ Voyage AI
| Model | Status | Dim |
|---|---|---|
| voyage-3-lite | 200 ✅ | 512 |

**Notes:** DB (768) နဲ့ မကိုက် — fix လိုတယ်

### ⚠️ HuggingFace — PARTIAL
| Endpoint | Status | Detail |
|---|---|---|
| whoami | ✅ 200 | T2W1, free |
| Token role | ⚠️ read-only | Gated download မရ |
| Model Hub | ✅ 200 | Public |
| Dataset Hub | ✅ 200 | Public |
| Spaces | ✅ 200 | Public |
| Myanmar models | ✅ 200 | `GKLMIP/bert-myanmar-*` |
| Myanmar Spaces | ✅ 200 | `MyanmarTTS`, `MyanmarGPT-Chat` |
| Inference Providers | ❌ 402 | **Free credits ဖျက် (Oct 8)** |

### ❌ Cerebras
| Endpoint | Status |
|---|---|
| list models | 200 (`gpt-oss-120b`, `qwen-3.8-27b`) |
| chat | 402 BILLING |

### ❌ Canva
| Endpoint | Status |
|---|---|
| users/me | 401 invalid_access_token |

---
---

## 3. Provider Chain — Production Setup

### Chat

    Primary:    Groq qwen3.8-27b         (fast, 14,400/day)
    Fallback 1: Cloudflare llama-3.1-8b  (free)
    Fallback 2: Cohere command-a-03-2025 (quality)
    Fallback 3: Gemini 3.5-flash         (Myanmar)
    Emergency:  OpenRouter free           (50/day)

### Coding

    Primary:    Mistral codestral-latest
    Fallback:   Groq qwen3.8-27b

### Embedding

    Primary:    Voyage voyage-3-lite (512)   ⚠️ DB dimension စစ်
    Fallback:   Cloudflare @cf/baai/bge-m3 (1024)
    ❌ OpenRouter hash fallback — semantic quality မရ

### Image / Speech

    Image:  Cloudflare flux-2-klein-9b
    Speech: Cloudflare whisper (STT) / melotts (TTS)

---
## 4. Open Items

| Item | Status | Blocker? |
|---|---|---|
| Groq VPN dependency | ⚠️ | No |
| Groq gpt-oss empty reply | ⚠️ | No (max_tokens fix) |
| Voyage 512 vs DB 768 | ⚠️ | **Yes** |
| RAG ingest E2E | ⚠️ | **Yes** |
| Publishing E2E | ⚠️ | **Yes** |
| HF Inference (402) | ❌ | No (alternative ရှိ) |
| Cerebras billing | ❌ | No |
| Canva invalid | ❌ | No |
| NVIDIA access (17 models) | ⚠️ | No |

---

## 5. Security — Key Rotation

Keys tested in chat — **rotate လုပ်ရမယ်**:

| Provider | URL |
|---|---|
| Gemini | https://aistudio.google.com/apikey |
| Groq | https://console.groq.com/keys |
| Cloudflare | https://dash.cloudflare.com/profile/api-tokens |
| Cohere | https://dashboard.cohere.com/api-keys |
| Mistral | https://console.mistral.ai/api-keys |
| Voyage | https://dashboard.voyageai.com/api-keys |
| NVIDIA | https://build.nvidia.com |
| OpenRouter | https://openrouter.ai/keys |
| HuggingFace | https://huggingface.co/settings/tokens |

---

## 6. Conclusion

| အချက် | Status |
|---|---|
| ✅ AI provider availability | **Blocker မဟုတ်တော့** (၈ ခု working) |
| ⚠️ RAG dimension | **Blocker** (Voyage 512 ≠ DB 768) |
| ⚠️ Publishing E2E | **Blocker** (မစမ်းရသေး) |

**Release certification:** `PENDING` — RAG + Publishing E2E ပြီးမှ close

---

## 7. Appendix — HF ရဲ့ တာဝန်

| တာဝန် | HF သုံးမလား | Alternative |
|---|---|---|
| Remote chat | ❌ | Groq, Cloudflare, Cohere, Gemini |
| **Local chat backup** | ✅ | Ollama + HF model |
| Remote embedding | ❌ | Voyage, Cloudflare `bge-m3` |
| **Local embedding** | ✅ | `BAAI/bge-m3` |
| **Myanmar NLP** | ✅ | `GKLMIP/bert-myanmar-base` |
| **Demo hosting** | ✅ | HF Spaces |
| Moderation | ✅ | Local `distilbert-sst-2` |

**လုပ်ရမယ့်အဆင့်:**
1. Token upgrade — read → write
2. Ollama install — local chat backup
3. HF Spaces deploy — Myanmar chatbot demo
4. Myanmar dataset — search & download
