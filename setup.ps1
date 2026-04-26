# Quick setup script for Compass RAG (Windows PowerShell)

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Compass RAG - Local Setup Script      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "✗ Python 3.11+ not found" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = python --version 2>&1 | Select-String -Pattern '\d+\.\d+' -AllMatches | ForEach-Object { $_.Matches[0].Value }
Write-Host "✓ Python $pythonVersion" -ForegroundColor Green

# Check Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "✗ Node.js 18+ not found" -ForegroundColor Red
    Write-Host "Install from: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Node.js $(node --version)" -ForegroundColor Green

# Check npm
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Host "✗ npm not found" -ForegroundColor Red
    exit 1
}

Write-Host "✓ npm $(npm --version)" -ForegroundColor Green

# Check Docker (optional)
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Write-Host "✓ Docker installed" -ForegroundColor Green
} else {
    Write-Host "⚠ Docker not found (optional for local setup)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup options:" -ForegroundColor Yellow
Write-Host "1) Docker Compose (Recommended)"
Write-Host "2) Local Python + Node"
Write-Host "3) Hybrid (Python local + Docker services)"
Write-Host ""

$option = Read-Host "Choose option (1-3)"

switch ($option) {
    "1" {
        Write-Host ""
        Write-Host "Starting Docker Compose setup..." -ForegroundColor Yellow

        $dockerComposeCmd = Get-Command docker-compose -ErrorAction SilentlyContinue
        if (-not $dockerComposeCmd) {
            Write-Host "✗ Docker Compose not found" -ForegroundColor Red
            Write-Host "Install from: https://docs.docker.com/compose/install/" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "Building Docker images (this may take 5-10 minutes)..." -ForegroundColor Yellow
        docker-compose up -d --build

        Write-Host ""
        Write-Host "Waiting for services to start (30 seconds)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30

        Write-Host ""
        docker-compose ps

        Write-Host ""
        Write-Host "✓ Services started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Access points:"
        Write-Host "  Frontend:      http://localhost:3000"
        Write-Host "  Prometheus:    http://localhost:9090"
        Write-Host "  Jaeger:        http://localhost:16686"
        Write-Host "  Grafana:       http://localhost:3001 (admin/admin)"
    }

    "2" {
        Write-Host ""
        Write-Host "Setting up local Python environment..." -ForegroundColor Yellow

        # Create virtual environment
        python -m venv venv
        & ".\venv\Scripts\Activate.ps1"

        Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
        pip install --upgrade pip
        pip install -r requirements.txt

        Write-Host ""
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location frontend
        npm install
        Pop-Location

        Write-Host ""
        Write-Host "✓ Local environment setup complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "1. Set your OpenRouter API key:"
        Write-Host "   `$env:OPENROUTER_API_KEY = 'sk-your-key-here'"
        Write-Host ""
        Write-Host "2. Start backend (PowerShell 1):"
        Write-Host "   .\venv\Scripts\Activate.ps1"
        Write-Host "   `$env:PYTHONPATH = './src'"
        Write-Host "   python -m uvicorn compass.main:app --reload"
        Write-Host ""
        Write-Host "3. Start frontend (PowerShell 2):"
        Write-Host "   cd frontend"
        Write-Host "   npm run dev"
        Write-Host ""
        Write-Host "4. Open browser:"
        Write-Host "   http://localhost:5173 (frontend)"
        Write-Host "   http://localhost:8000/health (backend)"
    }

    "3" {
        Write-Host ""
        Write-Host "Setting up hybrid environment..." -ForegroundColor Yellow

        # Start Docker services
        Write-Host "Starting Docker services (postgres, prometheus, jaeger, grafana)..." -ForegroundColor Yellow
        docker-compose up -d postgres prometheus jaeger grafana alertmanager

        Start-Sleep -Seconds 20

        # Setup Python
        Write-Host "Setting up local Python environment..." -ForegroundColor Yellow
        python -m venv venv
        & ".\venv\Scripts\Activate.ps1"

        Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
        pip install --upgrade pip
        pip install -r requirements.txt

        # Setup frontend
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location frontend
        npm install
        Pop-Location

        Write-Host ""
        Write-Host "✓ Hybrid environment setup complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "1. Set your OpenRouter API key:"
        Write-Host "   `$env:OPENROUTER_API_KEY = 'sk-your-key-here'"
        Write-Host "   `$env:DATABASE_URL = 'postgresql://compass:compass_password@localhost:5432/compass'"
        Write-Host ""
        Write-Host "2. Start backend (PowerShell 1):"
        Write-Host "   .\venv\Scripts\Activate.ps1"
        Write-Host "   `$env:PYTHONPATH = './src'"
        Write-Host "   python -m uvicorn compass.main:app --reload"
        Write-Host ""
        Write-Host "3. Start frontend (PowerShell 2):"
        Write-Host "   cd frontend"
        Write-Host "   npm run dev"
        Write-Host ""
        Write-Host "Access points:"
        Write-Host "  Frontend:      http://localhost:5173"
        Write-Host "  Prometheus:    http://localhost:9090"
        Write-Host "  Jaeger:        http://localhost:16686"
        Write-Host "  Grafana:       http://localhost:3001 (admin/admin)"
    }

    default {
        Write-Host "Invalid option" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Setup complete! Refer to INSTALLATION.md for detailed testing instructions." -ForegroundColor Green
