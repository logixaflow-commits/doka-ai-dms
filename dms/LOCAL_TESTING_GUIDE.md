# Local Testing Guide

ဒီ guide သည် Enterprise DMS hardening tests တွေကို local machine မှာ run လုပ်နည်းကို ပြသပေးထားပါတယ်။

## Prerequisites

စမ်းကြည့်ခင်အလိုအပ်ချက်များ:
- Python 3.8+ (လက်ရှိသုံးနေသည်: Python 3.14.5)
- pip (Python package manager)
- Virtual environment (recommended)

## Quick Start (Windows)

### 1. Simple Test Run (Batch File)
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\dms"
run_tests.bat
```

ဒါဆိုရင်:
- Virtual environment အလိုရှိရင် create ပေးပါမယ်
- Test dependencies တွေ install ပေးပါမယ်
- Security tests နဲ့ health check tests တွေ run ပေးပါမယ်

### 2. Manual Setup (Step by Step)

#### Step 1: Navigate to Project Directory
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\dms"
```

#### Step 2: Create Virtual Environment
```cmd
python -m venv venv
```

#### Step 3: Activate Virtual Environment
```cmd
venv\Scripts\activate.bat
```

#### Step 4: Install Dependencies
```cmd
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
```

#### Step 5: Run Tests

**All available tests:**
```cmd
pytest tests/ -v
```

**Specific test files:**
```cmd
pytest tests/test_security.py -v
pytest tests/test_health_check.py -v
```

**Specific test classes:**
```cmd
pytest tests/test_security.py::TestPasswordHashing -v
pytest tests/test_health_check.py::TestHealthCheckImplementation -v
```

**With coverage report:**
```cmd
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

## Test Files Available

### 1. `tests/test_security.py`
- Password hashing tests
- JWT token tests
- Encryption tests
- Run: `pytest tests/test_security.py -v`

### 2. `tests/test_health_check.py`
- Health check endpoint implementation tests
- Hardening file existence tests
- Run: `pytest tests/test_health_check.py -v`

### 3. `tests/test_classifier.py`
- Document classification tests
- Duplicate detection tests
- Run: `pytest tests/test_classifier.py -v`

### 4. `tests/test_hardening.py`
- Config validation tests
- Rate limiting tests
- Encryption key rotation tests
- OCR fallback tests
- Vector search caching tests
- Rule engine performance tests
- External API retry tests
- Run: `pytest tests/test_hardening.py -v`

## Test Results Interpretation

### ✅ PASSED
Test အောင်မြင်ပါတယ်။ Feature က မှန်ကန်စွာ အလုပ်ပေးနေပါတယ်။

### ❌ FAILED
Test မအောင်မြင်ပါ။ Issue ရှိနေပါတယ်။ Error message ကို check ပြီး fix လုပ်ပါ။

### ⚠️ SKIPPED
Test ကို skip လုပ်ထားပါတယ် (သက်ဆိုင်ရာ dependency မရှိလို့ ဖြစ်နိုင်ပါတယ်)။

## Common Issues & Solutions

### Issue 1: "ModuleNotFoundError"
**Solution:**
```cmd
pip install -r requirements.txt
```

### Issue 2: "Config validation failed" during tests
**Solution:** 
ဒါက normal ပါ။ Tests တွေက conftest.py မှာ environment variable ကို set လုပ်ထားပြီးဖြစ်ပါတယ်။

```python
# tests/conftest.py
os.environ['SKIP_CONFIG_VALIDATION'] = 'true'
```

### Issue 3: Import errors
**Solution:**
```cmd
cd dms
pytest tests/ -v
```

Project root မှာ ရှိနေစေပါ။

### Issue 4: Virtual environment not activating
**Solution:**
```cmd
# Windows
venv\Scripts\activate.bat

# If that doesn't work, try full path
cd "D:\1 main\Enterprise AI DMS Blueprint\dms"
.\venv\Scripts\activate.bat
```

## Advanced Testing Options

### Run specific tests with markers
```cmd
# Run only unit tests
pytest -m unit -v

# Run only security tests  
pytest -m security -v

# Run only database tests
pytest -m database -v
```

### Run tests in parallel (faster)
```cmd
# First install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest tests/ -n 4 -v
```

### Generate detailed coverage report
```cmd
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

Coverage report ကို `htmlcov/index.html` မှာ ကြည့်နိုင်ပါတယ်။

### Debug failed tests
```cmd
# Stop on first failure
pytest tests/ -x -v

# Drop to PDB on failure
pytest tests/ --pdb -v
```

## Continuous Testing (Watch Mode)

```cmd
# First install pytest-watch
pip install pytest-watch

# Run tests in watch mode
ptw tests/ --poll
```

Files ပြောင်းလိုက်တိုင်း tests တွေကို auto re-run လုပ်ပေးပါမယ်။

## Test Configuration

ပြင်ဆင်ချင်ရင် `pytest.ini` ကို ပြင်ဆင်နိုင်ပါတယ်:

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
addopts = -v --tb=short --strict-markers
```

## Expected Test Results

လက်ရှိအဆင့်မှာ:
- `test_security.py`: 6/7 tests pass (1 pre-existing failure)
- `test_health_check.py`: 15/15 tests pass
- `test_classifier.py`: Run to check
- `test_hardening.py`: Requires additional dependencies

## Troubleshooting

### Python version issues
```cmd
python --version
# Should be 3.8+
```

### Permission issues
**Solution:** Run as Administrator ဖြစ်စေပါ။

### Port conflicts
Tests တော်တော်မှာ ports လိုအပ်ချင်ပါတယ်။ Conflicts ရှိရင်:
- Other applications တွေကို close ပေးပါ
- Different ports သုံးပါ

## Getting Help

ပြဿနာရှိရင်:
1. Error message ကို စစ်ဆေးပါ
2. Python version နဲ့ dependencies တွေကို စစ်ဆေးပါ
3. Virtual environment ကို ပြန် create လုပ်ကြည့်ပါ

## Next Steps

Tests အောင်မြင်ပြီးရင်:
1. Application ကို start လုပ်ပါ
2. Manual testing လုပ်ပါ
3. Integration tests တွေ run ပါ
4. Production ကို deploy လုပ်ပါ

---

**Note:** ဒီ guide ကို Windows အတွက် ရေးဆွဲထားပါတယ်။ Linux/Mac သုံးရင် commands တွေကို appropriate shell commands တွေနဲ့ အစားသောက်ပေးပါ။
