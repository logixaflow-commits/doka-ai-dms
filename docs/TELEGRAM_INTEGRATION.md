# Telegram Integration Guide: Doka-AI-DMS

> **Project:** Doka AI Document Management System (Personal Local / Cloud)  
> **Directory:** `logixaflow@gmail.com\doka-ai-dms`  
> **Runtime / Stack:** FastAPI (Python), Tesseract OCR, Cloudflare Worker / Local  
> **Primary Topic:** `📄 Doka-DMS`

---

## 1. Overview & Topic Role

Doka DMS uses the Telegram Supergroup to monitor document ingestion, optical character recognition (OCR), duplicates, and backups:
* Immediate alerts when new documents arrive in the Watch Folder or Workspace.
* OCR completion reports with confidence score and text snippet.
* Alerts for duplicate documents with one-click cleanup options.
* Backup verification logs.

Users can also verify or re-route documents using Telegram buttons.

---

## 2. Topic Configuration

* **Suggested Topic Name:** `📄 Doka-DMS`
* **Suggested Topic ID:** `2` (or your assigned `message_thread_id`)
* **Color / Icon:** 📄 Page / Document

---

## 3. Environment Variables

Configure these variables in `web-platform/backend/.env` or in Cloud/Worker environment settings:

| Key | Type | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | String (Secret) | `""` | Bot token provided by `@BotFather` |
| `TELEGRAM_CHAT_ID` | String | `""` | Supergroup ID (e.g. `-100xxxxxxxxxx`) |
| `TELEGRAM_TOPIC_ID` | Integer | `None` | Thread ID for `#Doka-DMS` topic |
| `TELEGRAM_ENABLED` | Boolean | `false` | Master toggle (`true` to enable delivery) |

---

## 4. Code Architecture

* **Service Module:** `web-platform/backend/app/services/telegram.py`
* **Configuration:** `web-platform/backend/app/core/config.py` (`Settings.TELEGRAM_*`)
* **Template:** `web-platform/backend/.env.example`

---

## 5. Available Action Hooks & API

### (1) Document Imported Alert
```python
from app.services.telegram import notify_document_imported

await notify_document_imported(
    doc_id="doc_8831",
    filename="Customs_Declaration_Yangon.pdf",
    category="Logistics / Customs"
)
```
* **Actions included:**
  - `[✅ Approve Category]` (`doka_cat_appr:doc_8831`)
  - `[⚠️ Quarantine]` (`doka_quar:doc_8831`)

### (2) OCR Completed Notification
```python
from app.services.telegram import notify_ocr_completed

await notify_ocr_completed(
    doc_id="doc_8831",
    filename="Customs_Declaration_Yangon.pdf",
    confidence=0.965,
    text_preview="Declaration of Goods: Consignee ABC Ltd, Weight 4500kg, Port Yangon."
)
```

### (3) Duplicate Document Warning
```python
from app.services.telegram import notify_duplicate_detected

await notify_duplicate_detected(
    original_id="doc_1020",
    duplicate_filename="Scan_Copy_02.pdf"
)
```
* **Actions included:**
  - `[🗑️ Auto-Move to Archive]` (`doka_dup_archive:doc_1020`)
  - `[Keep Both]` (`doka_dup_keep:doc_1020`)

### (4) Backup Status Notification
```python
from app.services.telegram import notify_backup_status

await notify_backup_status(
    backup_name="dms_backup_20261014.tar.gz",
    success=True,
    size_mb=128.4
)
```

---

## 6. Cloud / Local Deployment Checklist

1. In Local mode: Add the variables into `web-platform/backend/.env`.
2. In Cloud mode (Render / Cloudflare Worker): Add the keys to your project's Environment Secrets.
3. Set `TELEGRAM_ENABLED=true` to go live.

---

## 7. Inbound Action Handler API

This project includes a dedicated inbound endpoint to receive callbacks from the Central Cloudflare Gateway:
* **Endpoint:** `POST /api/telegram/action`
* **Supported Actions:**
  * `doka_cat_appr:<id>` -> Approves OCR category classification and moves document to `Final`
  * `doka_quar:<id>` -> Quarantines suspicious document into `Quarantine/Suspicious`
  * `doka_dup_archive:<id>` -> Moves redundant duplicate file to Duplicates archive
  * `doka_dup_keep:<id>` -> Retains both documents with unique version hashes

---

## 8. AI Provider & API Keys Configuration

| Provider | Environment Key | Primary Role in Doka AI DMS | Free / Paid Notes |
|---|---|---|---|
| **OpenRouter** | `OPENROUTER_API_KEY` | Free chat models for classification | Strict allowlist: `liquid/lfm-2.5`, `nemotron-3.5` |
| **Groq** | `GROQ_API_KEY` | Fast metadata extraction from OCR text | `qwen/qwen3.8-27b` (high throughput) |
| **Cloudflare** | `CLOUDFLARE_API_TOKEN`<br>`CLOUDFLARE_ACCOUNT_ID` | Cloudflare Worker AI & OCR embeddings | Fast serverless inference (`@cf/baai/bge-m3`) |
| **Mistral** | `MISTRAL_API_KEY` | Document validation & SOP check | `ministral-8b` |
| **Cohere** | `COHERE_API_KEY` | Multi-lingual Burmese OCR reranking | `command-a-03-2025` |
| **Voyage** | `VOYAGE_API_KEY` | Document vector embeddings for search | `voyage-3-lite` (512-dim vector) |
| **Hugging Face** | `HUGGINGFACE_API_KEY` | Local model weights & tokenizer assets | Inference API disabled (Oct 8); Hub/Spaces only |

---

## 9. Tuned Fallback Chains & AI Monitoring

### 💬 Document Classification & Metadata Extraction Chain
1. 🥇 **Groq (`qwen/qwen3.8-27b`)** — Primary for instant JSON metadata extraction (<1s latency, 14,400 req/day free).
2. 🥈 **Gemini 2.5/3.5-flash** — Native Burmese document understanding and fraud/quarantine inspection.
3. 🥉 **Cohere (`command-a-03-2025`)** — High-precision semantic audit.
4. 4️⃣ **Cloudflare Workers AI (`llama-3.1-8b`)** — Serverless resilience.
5. 5️⃣ **OpenRouter (Free models)** — Emergency quota fallback.

### 📚 Enterprise Document Search (RAG)
1. 🥇 **Voyage AI (`voyage-3-lite`, 512-D)**
2. 🥈 **Cohere (`embed-v4.0`, 512-D)**

### 📊 Real-Time AI Usage & Health API
* **Endpoint:** `GET /api/ai/usage`
* **Telegram Command:** Send `/ai_status` or click `[🔄 Refresh Usage]` in Telegram to view active provider states and daily call counts.


