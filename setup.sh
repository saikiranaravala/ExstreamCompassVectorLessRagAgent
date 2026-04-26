#!/bin/bash
# Quick setup script for Compass RAG (macOS/Linux)

set -e

echo "╔════════════════════════════════════════╗"
echo "║  Compass RAG - Local Setup Script      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3.11+ not found${NC}"
    echo "Install from: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ ! "$PYTHON_VERSION" > "3.10" ]]; then
    echo -e "${RED}✗ Python version too old: $PYTHON_VERSION (need 3.11+)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js 18+ not found${NC}"
    echo "Install from: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [[ $NODE_VERSION -lt 18 ]]; then
    echo -e "${RED}✗ Node.js version too old: $NODE_VERSION (need 18+)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js $(node -v)${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm $(npm -v)${NC}"

# Check for Docker (optional)
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker $(docker --version | awk '{print $3}')${NC}"
else
    echo -e "${YELLOW}⚠ Docker not found (optional for local setup)${NC}"
fi

echo ""
echo -e "${YELLOW}Setup options:${NC}"
echo "1) Docker Compose (Recommended)"
echo "2) Local Python + Node"
echo "3) Hybrid (Python local + Docker services)"
echo ""
read -p "Choose option (1-3): " OPTION

case $OPTION in
    1)
        echo ""
        echo -e "${YELLOW}Starting Docker Compose setup...${NC}"

        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}✗ Docker Compose not found${NC}"
            echo "Install from: https://docs.docker.com/compose/install/"
            exit 1
        fi

        echo -e "${YELLOW}Building Docker images (this may take 5-10 minutes)...${NC}"
        docker-compose up -d --build

        echo ""
        echo -e "${YELLOW}Waiting for services to start (30 seconds)...${NC}"
        sleep 30

        echo ""
        docker-compose ps

        echo ""
        echo -e "${GREEN}✓ Services started!${NC}"
        echo ""
        echo "Access points:"
        echo "  Frontend:      http://localhost:3000"
        echo "  Prometheus:    http://localhost:9090"
        echo "  Jaeger:        http://localhost:16686"
        echo "  Grafana:       http://localhost:3001 (admin/admin)"
        ;;

    2)
        echo ""
        echo -e "${YELLOW}Setting up local Python environment...${NC}"

        # Create virtual environment
        python3 -m venv venv
        source venv/bin/activate

        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        pip install --upgrade pip
        pip install -r requirements.txt

        echo ""
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        cd frontend
        npm install
        cd ..

        echo ""
        echo -e "${GREEN}✓ Local environment setup complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Set your OpenRouter API key:"
        echo "   export OPENROUTER_API_KEY='sk-your-key-here'"
        echo ""
        echo "2. Start backend (Terminal 1):"
        echo "   source venv/bin/activate"
        echo "   export PYTHONPATH=./src"
        echo "   python -m uvicorn compass.main:app --reload"
        echo ""
        echo "3. Start frontend (Terminal 2):"
        echo "   cd frontend"
        echo "   npm run dev"
        echo ""
        echo "4. Open browser:"
        echo "   http://localhost:5173 (frontend)"
        echo "   http://localhost:8000/health (backend)"
        ;;

    3)
        echo ""
        echo -e "${YELLOW}Setting up hybrid environment...${NC}"

        # Start Docker services
        echo -e "${YELLOW}Starting Docker services (postgres, prometheus, jaeger, grafana)...${NC}"
        docker-compose up -d postgres prometheus jaeger grafana alertmanager

        sleep 20

        # Setup Python
        echo -e "${YELLOW}Setting up local Python environment...${NC}"
        python3 -m venv venv
        source venv/bin/activate

        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        pip install --upgrade pip
        pip install -r requirements.txt

        # Setup frontend
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        cd frontend
        npm install
        cd ..

        echo ""
        echo -e "${GREEN}✓ Hybrid environment setup complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Set your OpenRouter API key:"
        echo "   export OPENROUTER_API_KEY='sk-your-key-here'"
        echo "   export DATABASE_URL='postgresql://compass:compass_password@localhost:5432/compass'"
        echo ""
        echo "2. Start backend (Terminal 1):"
        echo "   source venv/bin/activate"
        echo "   export PYTHONPATH=./src"
        echo "   python -m uvicorn compass.main:app --reload"
        echo ""
        echo "3. Start frontend (Terminal 2):"
        echo "   cd frontend"
        echo "   npm run dev"
        echo ""
        echo "Access points:"
        echo "  Frontend:      http://localhost:5173"
        echo "  Prometheus:    http://localhost:9090"
        echo "  Jaeger:        http://localhost:16686"
        echo "  Grafana:       http://localhost:3001 (admin/admin)"
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Setup complete! Refer to INSTALLATION.md for detailed testing instructions.${NC}"
