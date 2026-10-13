# Doka AI DMS — Personal Local User & Operations Guide

> **System Scope:** Dedicated Single-User Personal Office DMS  
> **Font Standard:** Pure Myanmar Unicode Standard (Unicode 5.2+ / NFC normalized, Zawgyi dropped)  
> **Deployment Model:** 100% Local Machine (Windows), Zero Cloud Dependency, Zero Subscription Cost  
> **Status:** All 4 Core Local Operational Phases Completed and Verified (2026-10-14)

---

## 1. Overview & Architecture

Doka AI DMS is configured for **high-performance, privacy-first single-user office document management**. All operations run strictly on your local machine without transmitting documents to third-party cloud servers.

### Architecture Highlights:
* **Single-User Admin:** Direct bearer authentication on local machine. Enterprise RBAC and Multi-User tenant code remain safely archived/deferred (`Train 2 / Phase 9`) and will not interfere with personal operations.
* **Modern Unicode Only:** Full text extraction standardizes on normalized Unicode (NFC), eliminating Zawgyi encoding collisions.
* **Read-Only Source Integrity:** Original files in `SOURCE_ROOT` are protected with read-only permissions and Windows byte-level locking; work is performed exclusively on verified copies.

---

## 2. Four Completed Operational Phases

### 🔹 Phase 1: Batch Worker, Resumability & Deduplication Engine
* **Incremental Checkpointing:** Processes large collections (up to 30,000 files) with automatic progress flushes every 50 files.
* **Crash & Interruption Resumability:** If power is lost or the system is shut down, re-running `analyze()` instantly skips already processed documents and resumes directly from where it stopped.
* **Exact SHA-256 Deduplication:** Identical files (exact file copies) automatically share extraction results without re-triggering OCR, saving hours of CPU processing time.
* **Bounded Memory Management:** Explicit `gc.collect()` garbage collection prevents memory bloating during large batch processing.

### 🔹 Phase 2: Final Move Execution & Safe Rollback
* **Atomic Plan Execution:** Approved file organization proposals can be applied directly to `FINAL_ROOT` (`Final/`).
* **Chunked Batch Scaling:** The new `apply_in_chunks()` engine and `/api/workspace/imports/{session_id}/apply-batch` endpoint support applying up to 50,000 approved files safely in atomic 500-file chunks.
* **Pre/Post Hash Verification:** Hashes are verified before and after copying (`target_hash == source_hash`); if any discrepancy occurs, the target file is immediately rolled back.
* **1-Click Undo:** `undo()` functionality uses the audit journal (`organization_audit.jsonl`) to revert applied moves if files were misplaced.

### 🔹 Phase 3: Fast Full-Text Search (SQLite FTS5)
* **High-Speed Search Engine:** Scanned Myanmar and English OCR content is indexed into a dedicated SQLite FTS5 database (`fts_index.db`) per session.
* **Contextual Snippet Extraction:** Searching for keywords (e.g. "Invoice", "ဘိလပ်မြေ", "ရွှေပြည်သာ") highlights the matching phrase with surrounding context.
* **Instant Filtering:** Real-time filtering by document category, file extension, and review status.

### 🔹 Phase 4: Desktop 1-Click Launcher & Local Backup Tools
* **`start-doka.bat`:** Launches Python backend (FastAPI/uvicorn) and frontend (Vite) in the background, waits for service initialization, and opens the default browser directly to `http://127.0.0.1:5173`.
* **`stop-doka.bat`:** Cleanly terminates background backend and frontend processes and frees ports 8000 and 5173.
* **`backup-doka.bat`:** Performs an immediate, verified SHA-256 backup archive of the workspace into `D:\Doka\Backups`.

---

## 3. Daily Usage Walkthrough

### Step 1: Start the DMS
Double-click `start-doka.bat` in the repository root. Your browser will automatically open to `http://127.0.0.1:5173`.

### Step 2: Import & Scan
1. In the **Safe Workspace** panel, enter your source directory (default: `D:\Doka\NEW Sample Ofiice\2 SYM SHEM CO.,LTD`).
2. Click **Start Safe Import**. Doka creates a verified copy and validates SHA-256 hashes.
3. Click **Scan** to catalog files, detect duplicate groups, and check file formats.

### Step 3: OCR & Document Understanding
1. Click **Understand**. Doka runs the Myanmar + English OCR engine with automatic deduplication.
2. Progress is checkpointed every 50 files. You can stop or close the app at any time; resuming will pick up from where it left off.

### Step 4: Review Proposals & Apply to Final
1. Click **Plan** to generate categorization proposals (e.g., `Final/Contracts/`, `Final/Invoices/2026/`).
2. Review suggestions in the UI, select approved files (or select all), and click **Apply Selected**.
3. Files are safely organized into `Final/` with source integrity preserved.

### Step 5: Fast Keyword Search
* Use the search bar in the UI to instantly search across all scanned documents by Burmese or English keywords. Matching results show highlighted snippets with one-click preview.

### Step 6: Backup & Shutdown
* To create a backup: Run `backup-doka.bat`.
* To stop the app: Double-click `stop-doka.bat`.

---

## 4. Verification Evidence & Test Coverage

| Test Area | Scope | Result | Evidence File |
| :--- | :--- | :--- | :--- |
| **Resumability & Dedup** | `test_document_understanding.py` | **6/6 Passed** | Memory flush, deduplication markers |
| **Chunked Apply Engine** | `test_organization_planner.py` | **10/10 Passed** | 500-chunk atomicity, safe rollback |
| **FTS5 Index & Search** | `test_safe_workspace_service.py` | **5/5 Passed** | SQLite FTS5 table, snippet extraction |
| **Pilot Office Acceptance** | 300 Real SYM Office Files | **Passed (0 failures)** | [`docs/Report/pilot-acceptance-sym300.json`](file:///D:/Project/logixaflow@gmail.com/doka-ai-dms/docs/Report/pilot-acceptance-sym300.json) |

---

## 5. Remaining Work & Roadmap Inventory (ကျန်ရှိသည့် အချက်များနှင့် ရှေ့ဆက် အစီအစဉ်များ)

ယခုအခါ Personal Local စနစ်၏ အခြေခံ Code Engine (Phase 1-4) အားလုံး ပြီးပြည့်စုံသွားပြီ ဖြစ်သဖြင့် အနာဂတ်အတွက် ဆက်လက်လုပ်ဆောင်နိုင်သော အချက်များမှာ အောက်ပါအတိုင်း ဖြစ်ပါသည် -

### 1. ဖိုင် ၁,၆၂၁ လုံး အပြည့်အစုံကို စတင် Run ခြင်း (Full Office Corpus Run)
* အခု စမ်းသပ်မှုတွင် ရုံးဖိုင် ၁,၆၂၁ ထဲမှ အချိုးကျ ရွေးထုတ်ထားသော ဖိုင် ၃၀၀ ဖြင့် အောင်မြင်စွာ စမ်းသပ်ခဲ့ပါသည်။
* **ကျန်ရှိချက်:** ရုံး Folder ဖြစ်သော `D:\Doka\NEW Sample Ofiice\2 SYM SHEM CO.,LTD` ရှိ ဖိုင် ၁,၆၂၁ လုံး အပြည့်အစုံကို စနစ်ထဲသို့ Import ပြုလုပ်ပြီး အပြီးသတ် နေရာချထားခြင်း (အနာဂတ်တွင် ဖိုင် ၃၀,၀၀၀ အထိ အဆင့်ဆင့် တိုးချဲ့ခြင်း)။

### 2. Disk Space သန့်ရှင်းရေးနှင့် Pruning စနစ် (Storage Quota Management)
* ဖိုင်များကို `Final/` Folder ထဲသို့ ရွှေ့ပြောင်းပြီးပါက Working Copy နေရာတွင် Hard Disk နေရာ မပြည့်စေရန် ယာယီ Copy ဖိုင်များကို Prune လုပ်ပေးမည့် Disk Maintenance စနစ်။

### 3. Windows Task Scheduler ဖြင့် နေ့စဉ် အလိုအလျောက် Backup စနစ် (Scheduled Daily Backup)
* `backup-doka.bat` ကို Windows Task Scheduler တွင် ထည့်သွင်းပြီး ညစဉ် (ဥပမာ - ည ၁၁ နာရီတိုင်း) External Drive သို့မဟုတ် Drive D ထဲသို့ အလိုအလျောက် Auto-Backup ပြုလုပ်စေခြင်း။

### 4. Benchmark Quality Gate 3 တရားဝင် ပိတ်သိမ်းခြင်း (Pure Unicode Alignment)
* Test Suite ထဲရှိ မြန်မာစာ Benchmark Dataset တွင် ပါဝင်နေသော ဇော်ဂျီ စာသားအဟောင်းများကို စံယူနီကုဒ်ဖြင့် တိုက်ဆိုင်စစ်ဆေးနိုင်ရန် Reference JSON ကို ယူနီကုဒ် ပြင်ဆင်ပြီး Gate 3 ကို Formal Pass အဖြစ် ပိတ်သိမ်းခြင်း။

### 5. AI စွမ်းရည် ချိတ်ဆက်ခြင်း (ရွေးချယ်ခွင့် - Optional Smart DMS & RAG)
* ဖိုင်များကို အကျဉ်းချုပ်ဖတ်ခိုင်းခြင်း၊ စာချုပ်ထဲက အချက်အလက်များ မေးမြန်းခြင်း ("Chat with Document") ပြုလုပ်လိုပါက OpenRouter Free API Key လေး ထည့်သွင်းပေးရန်သာ ကျန်ရှိခြင်း။

### 6. Cloud နှင့် Multi-User စနစ် (Archived / Inactive)
* တစ်ယောက်တည်း သုံးမည်ဖြစ်သဖြင့် Cloudflare, Supabase, B2, Multi-User RBAC စနစ်များကို Codebase ထဲတွင် မပျက်မစီးဘဲ လုံခြုံစွာ Archive လုပ်ထားပြီး ဖြစ်ပါသည်။ အနာဂတ်တွင် ရုံးပြင်ပမှ သုံးချင်လာမှသာ ပြန်လည်အသက်သွင်းနိုင်ပါသည်။

