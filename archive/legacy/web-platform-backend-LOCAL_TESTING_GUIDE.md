# Doka Personal Local — Local Testing Guide

ဤလမ်းညွှန်သည် လက်ရှိ repository structure နှင့် CI တွင် သတ်မှတ်ထားသော test commands များအတွက် ဖြစ်သည်။ စမ်းသပ်မှုအားလုံးကို disposable test data / fixture များဖြင့်သာ လုပ်ဆောင်ပါ။ မူရင်းရုံးဖိုင်များ သို့မဟုတ် မူရင်း source drive ကို test input အဖြစ် မသုံးပါနှင့်။

## Prerequisites

- Python 3.12 (CI baseline)
- Node.js 24.x and npm (frontend `package.json` engine)
- Git
- Windows PowerShell / Command Prompt သို့မဟုတ် Linux/macOS shell
- OCR integration စမ်းသပ်မည်ဆိုပါက Tesseract OCR နှင့် Poppler utilities ကို OS အလိုက် install လုပ်ထားရန် လိုနိုင်သည်။

Version စစ်ရန်:

```sh
python --version
node --version
npm --version
```

## Repository paths

- `web-platform/backend/` — FastAPI backend and retained legacy Enterprise tests
- `web-platform/tests/` — cross-cutting Personal Local regression tests
- `web-platform/frontend/` — React + Vite frontend
- `scripts/doka_pilot_check.py` — copied-data pilot gate (real office pilot အတွက်သာ)

## Backend setup and tests

Repository root မှ run ပါ:

### Windows PowerShell

```powershell
py -3.12 -m venv web-platform/backend/.venv
web-platform/backend/.venv/Scripts/python.exe -m pip install -r web-platform/backend/requirements-local.txt
Set-Location web-platform/backend
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing
Set-Location ../..
```

### Linux / macOS

```sh
python3.12 -m venv web-platform/backend/.venv
web-platform/backend/.venv/bin/python -m pip install -r web-platform/backend/requirements-local.txt
cd web-platform/backend
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
cd ../..
```

The backend `pytest.ini` deliberately selects `../tests` for the Personal Local profile. The old backend-local `test_*.py` files and `backend/tests/` target the retained Enterprise application; they are not included in this profile because its `requirements-local.txt` does not provide their dependencies and several tests import removed legacy modules. They remain in the repository and must not be reported as passing or silently folded into the Personal Local suite. Restore a separate legacy profile only after its dependencies and supported imports are established.

The Personal Local suite includes symlink-boundary tests. On Windows, creating symlinks requires Developer Mode or the SeCreateSymbolicLinkPrivilege right. If Windows returns `WinError 1314`, only the affected symlink test reports an explicit skip; the same cases are included in the configured Ubuntu CI suite. Other symlink-creation errors still fail.

Focused test file ကို စမ်းလိုပါက backend directory ထဲမှ ဥပမာ:

```sh
.venv/bin/python -m pytest ../tests/test_personal_local_entrypoint.py -q
```

Windows တွင် `.venv/Scripts/python.exe` ကို အသုံးပြုပါ။

## Frontend checks

```sh
cd web-platform/frontend
npm ci
npm run lint
npm run build
npm test
cd ../..
```

- `npm run lint` — ESLint quality check
- `npm run build` — TypeScript project build နှင့် Vite production bundle
- `npm test` — repository ရှိ frontend smoke/regression assertions

Lint baseline မရှင်းသေးပါက errors/warnings အားလုံးကို မှတ်တမ်းတင်ပြီး တစ်သုတ်ချင်း ပြင်ပါ။ Lint ကို ဖြတ်ကျော်ရန် rules များကို ပိတ်ခြင်း သို့မဟုတ် findings များကို ဖျောက်ခြင်း မလုပ်ပါနှင့်။

## Local application workflow

Repository root မှ:

- Windows: `start_application.bat`
- Linux/macOS: `./run.sh`

Launcher သည် Node.js 24.x ကို လိုအပ်သည်။ ပထမဆုံးစတင်ချိန်တွင် backend virtual environment / dependencies နှင့် frontend dependencies များကို ပြင်ဆင်နိုင်သည်။ Backend ကို `127.0.0.1:8000`၊ frontend ကို `127.0.0.1:3000` တွင် ဖွင့်ရန် ရည်ရွယ်ထားသည်။

Local login မလုပ်မီ `web-platform/backend/.env` ထဲတွင် ကိုယ်ပိုင် `BOOTSTRAP_ADMIN_PASSWORD` သတ်မှတ်ပါ။ မျှဝေသုံးနိုင်သော password သို့မဟုတ် production secret ကို မသုံးပါနှင့်။ Personal Local mode အတွက် Supabase credential များကို မထည့်ပါနှင့်။

## Safety rules for manual verification

1. `ORIGINAL_READ_ONLY=true` နှင့် `ALLOW_SOURCE_WRITE=false` ကို မပြောင်းပါနှင့်။
2. Import/scan/organize/backup/restore စမ်းသပ်ရာတွင် disposable copied fixtures ကိုသာ သုံးပါ။
3. `SOURCE_ROOT`, `WORKING_ROOT`, `FINAL_ROOT`, `BACKUP_ROOT` တို့သည် သီးခြားပြီး သတ်မှတ်ထားသည့် isolation rules ကို လိုက်နာကြောင်း စစ်ပါ။
4. Restore ကို active workspace ထဲသို့ တိုက်ရိုက်မလုပ်ပါနှင့်။ သီးခြား recovery destination ကိုသာ သုံးပါ။
5. Test ပြီးလျှင် fixture data ကိုသာ ဖယ်ရှားပါ။ မူရင်း data ကို မရွှေ့၊ မဖျက်၊ မပြင်ပါနှင့်။
6. Vercel production သည် paused/off အဖြစ် ဆက်ထားပါ။ ဤ guide အတွက် deploy မလိုအပ်ပါ။

## Results and evidence

Command တစ်ခုချင်းစီ၏ exit code, test count, failed/skipped count, runtime versions နှင့် error output ကို မှတ်တမ်းတင်ပါ။ Command မ run ရသေးပါက `pending` ဟုသာ မှတ်သားပါ။ Source code ထဲတွင် test ရှိနေခြင်းတစ်ခုတည်းဖြင့် test အောင်မြင်သည်ဟု မယူဆပါနှင့်။

Real-office pilot သည် Phase 2 gate ဖြစ်သည်။ မူရင်းရုံး data မဟုတ်သော သီးခြား copy ကို အသုံးပြုပြီးမှ `python scripts/doka_pilot_check.py --source <COPY_OF_REAL_OFFICE_DATA> --require-ocr` ကို run ပါ။ Test fixtures သို့မဟုတ် repository test များကို real-office pilot အောင်မြင်မှုအဖြစ် မတွက်ပါနှင့်။
