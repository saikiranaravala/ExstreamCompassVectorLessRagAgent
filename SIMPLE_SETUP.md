# Simple Local Setup (No Docker)

Get Compass RAG running in 15 minutes with just Python and Node.

## Prerequisites (Check These First)

```bash
# Check Python 3.11+
python --version
# Should show: Python 3.11.x or higher

# Check Node.js 18+
node --version
# Should show: v18.x or higher

# Check npm
npm --version
# Should show: 9.x or higher
```

**Don't have these?**
- Python: Download from https://www.python.org/downloads/
- Node.js: Download from https://nodejs.org/

## Step 1: Get OpenRouter API Key

1. Visit https://openrouter.ai
2. Sign up (free tier works)
3. Copy your API key

## Step 2: Setup Python Backend

```bash
# Navigate to project folder
cd /path/to/compass-rag

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies (takes 2-3 minutes)
pip install -r requirements.txt

# Verify installation
python -c "from compass import agent; print('✓ Backend ready')"
```

## Step 3: Setup Frontend

```bash
# Open new terminal/command prompt in same folder
cd /path/to/compass-rag/frontend

# Install dependencies (takes 1-2 minutes)
npm install

# Go back to root
cd ..
```

## Step 4: Create Config File

Create `.env` file in root folder:

```
OPENROUTER_API_KEY=sk-your-key-here
REASONING_MODEL=deepseek-v4
SUMMARIZATION_MODEL=deepseek-v4
DEBUG=true
DATABASE_URL=sqlite:///./compass.db
```

Replace `sk-your-key-here` with your actual key.

## Step 5: Start Backend

```bash
# Make sure venv is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Start backend on port 8000
python -m uvicorn compass.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
Uvicorn running on http://0.0.0.0:8000
Application startup complete
```

## Step 6: Start Frontend (New Terminal)

```bash
# Open NEW terminal/command prompt

# Navigate to frontend
cd /path/to/compass-rag/frontend

# Start dev server on port 5173
npm run dev
```

**Expected output:**
```
Local: http://localhost:5173
```

## Step 7: Open in Browser

Go to: **http://localhost:5173**

## Testing

### 1. Login
- Email: `test@example.com`
- Password: `anything` (test mode accepts any password)

### 2. Select Variant
- Click **Cloud Native** or **Server-Based**

### 3. Ask Question
```
Type: "What is cloud native deployment?"
Click: Send
```

### 4. Expected Result
✅ Answer appears in 2-4 seconds  
✅ Shows tool calls and processing time  
⚠️ May say "No documents found" (index empty)  

### 5. See Details
- Click on the assistant's answer to expand
- Shows citations and reasoning trail

## Troubleshooting

### Backend won't start

**Error: "ModuleNotFoundError"**
```bash
# Make sure venv is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Try pip install again
pip install -r requirements.txt
```

**Error: "Port 8000 already in use"**
```bash
# Find and stop process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :8000
kill -9 <PID>

# Or use different port:
python -m uvicorn compass.main:app --port 8001
```

**Error: "OpenRouter API key not valid"**
```bash
# Check .env file has your key
cat .env

# Verify key starts with "sk-or-"
# Get new key: https://openrouter.ai/keys
```

### Frontend won't load

**Error: "Connection refused on localhost:8000"**
```bash
# Make sure backend is running in other terminal
# Check: http://localhost:8000/health
curl http://localhost:8000/health

# Should see: {"status":"healthy","service":"compass-rag"}
```

**Error: "Port 5173 already in use"**
```bash
# Frontend will try next port (5174, 5175, etc.)
# Check terminal output for actual URL
# Or kill process:
# Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5173
kill -9 <PID>
```

### Slow responses

**Backend is slow on first query**
- First query loads index and model (~10-15 seconds)
- Subsequent queries are fast (2-4 seconds)

**Check Python version**
```bash
python --version  # Must be 3.11+
```

## File Structure

```
compass-rag/
├── .env                    ← Create this with API key
├── venv/                   ← Virtual environment (created by setup)
├── src/compass/            ← Python backend code
├── frontend/               ← React frontend code
├── tests/                  ← Test suites
└── SIMPLE_SETUP.md        ← This file
```

## Next Steps

### Run More Tests
```bash
# Test with evaluation queries (requires index)
python scripts/run_evaluation.py --limit 5
```

### Stop Services
```bash
# In backend terminal: Ctrl+C
# In frontend terminal: Ctrl+C
```

### Deactivate Python Environment
```bash
deactivate  # When you're done
```

## Common Commands

```bash
# Start fresh backend
python -m uvicorn compass.main:app --reload

# Run tests
python -m pytest tests/ -v

# Check API health
curl http://localhost:8000/health

# View frontend on phone (replace with your IP)
http://192.168.1.100:5173

# Clean Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

## What's Running

| Component | URL | What it Does |
|-----------|-----|--------------|
| **Backend** | http://localhost:8000 | Processes queries, runs agent |
| **Frontend** | http://localhost:5173 | Web interface for chatting |
| **SQLite DB** | ./compass.db | Stores sessions, audit logs |

## That's It!

You now have a fully working Compass RAG system:
- ✅ Chat interface
- ✅ Query processing
- ✅ Session management
- ✅ Audit logging
- ✅ Full API

**No Docker, no extra services, just Python + React.**

---

Need help? Check these files:
- `INSTALLATION.md` — Detailed setup options
- `QUICKSTART.md` — Quick reference
- `docs/DEPLOYMENT.md` — Production setup

### Tips

1. **Keep both terminals open** — One for backend, one for frontend
2. **First query is slow** — Index loads on first use (10-15 sec)
3. **Modify and test** — Change code, frontend auto-reloads
4. **Check the logs** — Both terminals show what's happening
5. **Save your conversations** — Click "Export" in UI (when available)

Enjoy! 🎉
