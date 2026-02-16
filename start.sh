#!/bin/bash
# FlowStorm - Start both backend and frontend
# Usage: ./start.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  FlowStorm - Starting Up${NC}"
echo -e "${CYAN}========================================${NC}"

# ---- Create venv if needed (must be sequential) ----
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[Backend]${NC} Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ---- Install deps in parallel ----
BACKEND_MARKER="$VENV_DIR/.deps_installed"
NEED_PIP=false
NEED_NPM=false

if [ ! -f "$BACKEND_MARKER" ] || [ "$BACKEND_DIR/requirements.txt" -nt "$BACKEND_MARKER" ]; then
    NEED_PIP=true
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ] || [ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ]; then
    NEED_NPM=true
fi

if $NEED_PIP || $NEED_NPM; then
    echo -e "\n${YELLOW}Installing dependencies in parallel...${NC}"

    if $NEED_PIP; then
        (
            echo -e "${YELLOW}[pip]${NC} Installing Python packages..."
            pip install -q -r "$BACKEND_DIR/requirements.txt" 2>&1
            touch "$BACKEND_MARKER"
            echo -e "${GREEN}[pip]${NC} Done"
        ) &
        PIP_PID=$!
    fi

    if $NEED_NPM; then
        (
            echo -e "${YELLOW}[npm]${NC} Installing Node packages..."
            cd "$FRONTEND_DIR" && npm install --silent 2>&1
            echo -e "${GREEN}[npm]${NC} Done"
        ) &
        NPM_PID=$!
    fi

    # Wait for both
    [ -n "$PIP_PID" ] && wait $PIP_PID
    [ -n "$NPM_PID" ] && wait $NPM_PID

    echo -e "${GREEN}All dependencies ready${NC}"
else
    echo -e "${GREEN}Dependencies up to date${NC}"
fi

# ---- Start services ----
echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}  Starting services...${NC}"
echo -e "${CYAN}========================================${NC}"

cd "$BACKEND_DIR"
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd "$FRONTEND_DIR"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo -e "\n${CYAN}========================================${NC}"
echo -e "${GREEN}  FlowStorm is running!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:3000"
echo -e "  Press Ctrl+C to stop"
echo -e "${CYAN}========================================${NC}\n"

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Stopped.${NC}"
}

trap cleanup EXIT INT TERM
wait
