# Application Startup Guide

Enterprise AI DMS ကို local machine မှာ ဘယ်လို start လုပ်ရမှာ guide ပါ။

## Prerequisites

- Python 3.8+ (လက်ရှိ: Python 3.14.5)
- Node.js 16+ (React frontend အတွက်)
- npm (Node.js package manager)

## Quick Start (Recommended)

### Option 1: Start Both Backend & Frontend (အကြိုက်)

```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint"
start_application.bat
```

ဒါဆိုရင်:
- Backend (FastAPI) ကို port 8000 မှာ start ပေးပါမယ်
- Frontend (React) ကို port 3000 မှာ start ပေးပါမယ်
- Browser ကို auto open ပေးပါမယ်

### Option 2: Start Separately

**Backend Only:**
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint"
start_backend.bat
```
Access: http://localhost:8000

**Frontend Only:**
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint"
start_frontend.bat
```
Access: http://localhost:3000

## Manual Startup

### Step 1: Start Backend (FastAPI)

```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\dms"

# Activate virtual environment (optional but recommended)
venv\Scripts\activate.bat

# Start FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend ကို သီးသန့်တည်းစေချင်ရင် `--reload` flag ကို ဖြုတ်ပါ:

```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Start Frontend (React)

**New Terminal ဖွင့်ပါ:**

```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\app"

# Install dependencies if first time
npm install

# Start React development server
npm run dev
```

## Access URLs

**Application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**Documentation:**
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc

**Health Checks:**
- Full Health: http://localhost:8000/health
- Quick Health: http://localhost:8000/health/quick

## Troubleshooting

### Backend Issues

**Issue: "Module not found" errors**
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\dms"
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Issue: Port 8000 already in use**
```cmd
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Or use different port:**
```cmd
python -m uvicorn app.main:app --port 8001
```

### Frontend Issues

**Issue: "npm not found"**
- Install Node.js from https://nodejs.org/

**Issue: "Dependencies not installed"**
```cmd
cd "D:\1 main\Enterprise AI DMS Blueprint\app"
npm install
```

**Issue: Port 3000 already in use**
```cmd
# Kill process using port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Or configure different port in `app/vite.config.ts`:**
```typescript
server: {
  port: 3001, // Change to different port
  // ... rest of config
}
```

### Database Issues

**Issue: Database connection failed**
1. Check PostgreSQL is running
2. Update `.env` with correct database credentials
3. Use SQLite for development:
   ```
   DATABASE_URL=sqlite:///./dms.db
   ```

### Redis Issues

**Issue: Redis connection failed**
1. Install and start Redis
2. Or disable Redis-dependent features temporarily

## Development Mode Features

**Backend (with --reload flag):**
- Auto-restart on code changes
- Detailed error messages
- Debug mode enabled

**Frontend:**
- Hot module replacement
- Fast refresh
- Source maps
- Detailed error overlay

## Production Deployment

For production, don't use development mode. Build the frontend:

```cmd
cd app
npm run build
```

And run backend without reload:
```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Environment Variables

Key environment variables in `.env`:

```
# Application
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dms_db

# Frontend
VITE_API_URL=http://localhost:8000
```

## Verification

**Verify Backend:**
```cmd
curl http://localhost:8000/health
```
Should return health status JSON.

**Verify Frontend:**
```cmd
curl http://localhost:3000
```
Should return HTML content.

**Verify API:**
```cmd
curl http://localhost:8000/docs
```
Should show Swagger UI.

## Stopping the Application

**Manual:**
- Press Ctrl+C in each terminal window
- Or close the terminal windows

**Using startup script:**
- Close the opened command windows

## Next Steps

1. ✅ Start backend and frontend
2. 🌐 Open http://localhost:3000 in browser
3. 👤 Create admin account or login
4. 📄 Upload documents to test AI features
5. 🔍 Test search and classification
6. 📊 Explore dashboard and analytics

## Getting Help

Issues ရှိရင်:
1. Check terminal error messages
2. Verify all services are running (PostgreSQL, Redis)
3. Check network connectivity
4. Review logs in terminal windows

---

**မှတ်ချက်:** ဒီ guide ကို Windows အတွက် ရေးဆွဲထားပါတယ်။ Linux/Mac သုံးရင် commands တွေကို appropriate shell commands တွေနဲ့ အစားသောက်ပေးပါ။
