# Local Installation & Testing Guide

Complete step-by-step guide to install and test Compass RAG on your local machine.

## Prerequisites Check

### System Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 20GB free space
- **CPU**: 4-core minimum

### Required Software

```bash
# Check if you have these installed:
node --version        # Node.js 18+
npm --version         # npm 9+
python --version      # Python 3.11+
pip --version         # pip 23+
docker --version      # Docker 20.10+ (for containerized setup)
```

## Installation Options

Choose one approach:

### Option 1: Docker Compose (Recommended - Easiest)
✅ Recommended for first-time testing  
✅ All services pre-configured  
✅ No dependency conflicts  
⏱️ Time: 10-15 minutes

### Option 2: Local Python + Node (Advanced)
✅ Full control and debugging  
✅ Can modify code and test immediately  
⏱️ Time: 30-45 minutes

### Option 3: Hybrid (Python local, Services in Docker)
✅ Balance of control and simplicity  
⏱️ Time: 20-30 minutes

---

## Option 1: Docker Compose (Recommended)

### Step 1: Get Your OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up and get your API key
3. Set environment variable:

```bash
# Windows (PowerShell)
$env:OPENROUTER_API_KEY = "sk-your-key-here"

# macOS/Linux
export OPENROUTER_API_KEY="sk-your-key-here"
```

### Step 2: Start All Services

```bash
# Navigate to project directory
cd /path/to/compass-rag

# Start services (first run will build images)
docker-compose up -d

# Wait 30-40 seconds for services to start
sleep 40

# Check service status
docker-compose ps
```

Expected output:
```
NAME                  STATUS
compass-backend       healthy (after ~30s)
compass-frontend      healthy (after ~30s)
compass-postgres      healthy (after ~10s)
compass-prometheus    running
compass-jaeger        running
compass-grafana       running
compass-alertmanager  running
```

### Step 3: Verify Services

```bash
# Test backend health
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"compass-rag"}

# Check frontend
open http://localhost:3000
# or: firefox http://localhost:3000
# or: start http://localhost:3000
```

### Step 4: Access Dashboards

```
Frontend:        http://localhost:3000
Prometheus:      http://localhost:9090
Jaeger Tracing:  http://localhost:16686
Grafana:         http://localhost:3001  (admin/admin)
AlertManager:    http://localhost:9093
```

### Step 5: Test End-to-End

See **Testing Workflow** section below.

---

## Option 2: Local Python + Node (Advanced)

### Step 1: Clone & Setup Project

```bash
# Navigate to project
cd /path/to/compass-rag

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 2: Install Python Dependencies

```bash
# Install backend dependencies
pip install -r requirements.txt

# Verify installation
python -c "import compass; print('✓ Backend installed')"
```

### Step 3: Install Frontend Dependencies

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Back to root
cd ..
```

### Step 4: Setup Database

```bash
# Option A: Use SQLite (simplest for testing)
# Edit src/compass/config.py:
# DATABASE_URL = "sqlite:///./compass.db"

# Option B: Install PostgreSQL locally
# macOS: brew install postgresql
# Windows: Download from postgresql.org
# Ubuntu: sudo apt-get install postgresql

# Start PostgreSQL and create database
createdb -U postgres compass
```

### Step 5: Start Backend

```bash
# Set environment variables
export OPENROUTER_API_KEY="sk-your-key"
export PYTHONPATH=./src

# Start uvicorn server
python -m uvicorn compass.main:app --reload --host 0.0.0.0 --port 8000

# Should show:
# Uvicorn running on http://0.0.0.0:8000
```

### Step 6: Start Frontend (New Terminal)

```bash
# Activate venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Navigate to frontend
cd frontend

# Start dev server
npm run dev

# Should show:
# Local: http://localhost:5173
```

### Step 7: Test End-to-End

See **Testing Workflow** section below.

---

## Option 3: Hybrid (Python Local + Docker Services)

### Step 1: Start Only Support Services

```bash
# Start only supporting services (not backend)
docker-compose up -d postgres prometheus jaeger grafana alertmanager

# Wait for services
sleep 20

# Check status
docker-compose ps
```

### Step 2: Install & Start Python Backend

```bash
# Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start backend (connects to Docker PostgreSQL)
export OPENROUTER_API_KEY="sk-your-key"
export DATABASE_URL="postgresql://compass:compass_password@localhost:5432/compass"
python -m uvicorn compass.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Start Frontend

```bash
# In new terminal
cd frontend
npm install
npm run dev
```

---

## Testing Workflow

### 1. Frontend Login

```
URL: http://localhost:3000

Test Credentials:
- Email: test@example.com
- Password: anything (test mode)

Note: Backend uses simple test auth by default
```

### 2. Select Documentation Variant

- Click "Cloud Native" or "Server-Based"
- This switches which documentation the agent searches

### 3. Test Basic Query

```
Query: "How do I install Compass?"

Expected:
✓ Message appears in chat
✓ Loading indicator shows
✓ Answer appears from agent
✓ Processing time shown (e.g., "2.3s")
✓ Tool calls displayed
✓ Citations appear in right panel
```

### 4. Test Variant Switching

```
1. Select Cloud Native variant
2. Ask a question (e.g., "What is cloud native?")
3. Switch to Server-Based
4. Ask similar question
5. Compare answers - should reflect different documentation
```

### 5. View Citations

```
1. Click on assistant message (answer)
2. Right panel shows "Citations"
3. Each citation numbered with:
   - Document title
   - File path
   - Excerpt content
```

### 6. View Reasoning Trail

```
1. Click on assistant message
2. Expand "Reasoning Trail" in right panel
3. See:
   - Variant used
   - Number of tool calls
   - Processing time
   - Processing steps (Query → Planning → Execution → Synthesis)
```

### 7. Test Error Handling

```
1. Enter invalid query: ""
2. Try with special characters
3. Submit while slow query running
4. Logout and try to access without token

Expected: Graceful error messages
```

### 8. Monitor Metrics

```
Prometheus (http://localhost:9090):
- Expand "Graph" tab
- Query: compass_queries_total
- See query counts by variant and status

Grafana (http://localhost:3001):
- Login: admin / admin
- Navigate to "Compass Overview" dashboard
- See real-time metrics:
  - Query rate
  - Success rate gauge
  - Latency percentiles
  - Tool calls breakdown
```

### 9. View Traces

```
Jaeger (http://localhost:16686):
1. Open Jaeger UI
2. Select "compass" service
3. View recent traces
4. Click trace to see:
   - Request timeline
   - Tool call timing
   - Component breakdown
```

### 10. Run Evaluation Harness

```bash
# Run subset of evaluation queries
python scripts/run_evaluation.py --limit 10

# Expected output:
# ======================================================================
# EVALUATION RESULTS SUMMARY
# ======================================================================
# Total Queries: 10
# Successful: 8-10
# Success Rate: 80-100%
# Avg Latency: 2000-3000ms
# ...

# Full evaluation (takes ~30-60 minutes)
python scripts/run_evaluation.py --batch-size 5
```

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Must be 3.11+

# Check for port conflicts
# Windows:
netstat -ano | findstr :8000
# macOS/Linux:
lsof -i :8000

# If port in use, change port in code or kill process
```

### Frontend won't connect to backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check frontend environment
# frontend/.env should have:
VITE_API_URL=http://localhost:8000/api/v1

# Check browser console for errors (F12)
```

### OpenRouter API key not working

```bash
# Verify key is set
echo $OPENROUTER_API_KEY

# Check key format (should start with "sk-")
# Get new key from https://openrouter.ai/keys

# Verify in Python
python -c "import os; print(os.getenv('OPENROUTER_API_KEY'))"
```

### Docker services not starting

```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs

# Rebuild images
docker-compose down
docker-compose up -d --build

# Check disk space (need 10GB+)
docker system df
```

### Database connection errors

```bash
# Check PostgreSQL is running
# Docker:
docker-compose logs postgres

# Local:
psql -U postgres -c "\l"

# Create database if missing
createdb -U compass compass

# Test connection
psql -U compass -d compass -c "SELECT 1"
```

---

## Performance Expectations

### First Time Setup
- Docker images: 2-5 minutes to build
- Services starting: 30-40 seconds
- Frontend build: 1-2 minutes

### Query Performance
- Cold start (index load): 5-10 seconds
- Warm query (cached index): 2-4 seconds
- Citations generation: <1 second
- Metrics collection: <100ms

### Resource Usage
- Backend: 200-400MB RAM
- Frontend: 100-150MB RAM
- PostgreSQL: 50-100MB RAM
- Total: ~500MB-700MB RAM

---

## Testing Checklist

- [ ] Backend API responds to health check
- [ ] Frontend loads on http://localhost:3000
- [ ] Can login with test credentials
- [ ] Can submit query and get answer
- [ ] Variant switching works
- [ ] Citations appear in sidebar
- [ ] Reasoning trail shows tool calls
- [ ] Prometheus metrics update
- [ ] Grafana dashboard shows query rate
- [ ] Jaeger shows traces
- [ ] Error handling works gracefully
- [ ] Evaluation harness runs successfully

---

## Common Tasks

### View Live Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Backend console
# (If running locally) look at terminal output
```

### Reset Everything

```bash
# Stop services
docker-compose down -v

# Remove volumes (deletes all data)
rm -rf .compass_* compass.db

# Restart
docker-compose up -d
```

### Stop Services (Keep Data)

```bash
docker-compose stop

# Restart later
docker-compose start
```

### View Database

```bash
# PostgreSQL (Docker)
docker-compose exec postgres psql -U compass -d compass

# SQLite (Local)
sqlite3 compass.db

# Useful queries:
# SELECT * FROM sessions;
# SELECT * FROM audit_events LIMIT 10;
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Backend will show detailed logs
python -m uvicorn compass.main:app --reload --log-level debug
```

---

## Next Steps After Testing

1. **Build search index** — Populate .atlas/index.json with your documentation
2. **Customize prompts** — Adjust system prompts in agent configuration
3. **Tune budgets** — Adjust MAX_TOOL_CALLS_PER_QUERY based on performance
4. **Configure alerts** — Set thresholds in Prometheus for your environment
5. **Deploy to production** — Use docker-compose on a server

---

## Support

If you encounter issues:

1. Check logs: `docker-compose logs` or terminal output
2. Verify prerequisites: Python 3.11+, Node 18+, Docker
3. Check environment variables: `echo $OPENROUTER_API_KEY`
4. Test connectivity: `curl http://localhost:8000/health`
5. Review error messages in browser console (F12)

For detailed troubleshooting, see specific error sections above.
