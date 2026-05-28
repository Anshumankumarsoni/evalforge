#!/usr/bin/env bash
# ============================================================
# EvalForge — local development startup script
# Usage: ./run_local.sh
# ============================================================
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BOLD}🔬 EvalForge — Local Dev Startup${NC}"
echo "──────────────────────────────────────"

# ── 1. Check Python version ──────────────────────────────────
PYTHON=$(command -v python3.11 || command -v python3 || command -v python)
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PY_VERSION ($PYTHON)"

# ── 2. Check .env exists ─────────────────────────────────────
if [ ! -f .env ]; then
  echo -e "${YELLOW}⚠  .env not found — copying from .env.example${NC}"
  cp .env.example .env
  echo -e "${RED}   ➜  Add your API keys to .env before running suites!${NC}"
fi

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Set port defaults
API_PORT=${API_PORT:-8080}
DASHBOARD_PORT=${DASHBOARD_PORT:-8501}


# ── 3. Install dependencies if needed ────────────────────────
if ! $PYTHON -c "import fastapi" 2>/dev/null; then
  echo "Installing API dependencies…"
  $PYTHON -m pip install -r requirements-api.txt -q
fi
if ! $PYTHON -c "import streamlit" 2>/dev/null; then
  echo "Installing dashboard dependencies…"
  $PYTHON -m pip install -r requirements-dashboard.txt -q
fi
echo -e "${GREEN}✓${NC} Dependencies ready"

# ── 4. Create data directory ─────────────────────────────────
mkdir -p data
echo -e "${GREEN}✓${NC} Data directory ready"

# ── 5. Launch API in background ──────────────────────────────
echo ""
echo "Starting FastAPI on http://localhost:$API_PORT …"
$PYTHON -m uvicorn api.main:app --host 0.0.0.0 --port $API_PORT --reload &
API_PID=$!
echo -e "${GREEN}✓${NC} API started (PID $API_PID)"

# Give the API a moment to bind
sleep 2

# ── 6. Launch Streamlit dashboard ────────────────────────────
echo "Starting Streamlit on http://localhost:$DASHBOARD_PORT …"
$PYTHON -m streamlit run dashboard/app.py \
  --server.port $DASHBOARD_PORT \
  --server.headless true \
  --server.address 0.0.0.0 &
DASH_PID=$!
echo -e "${GREEN}✓${NC} Dashboard started (PID $DASH_PID)"

echo ""
echo -e "${BOLD}──────────────────────────────────────${NC}"
echo -e "  API       → ${BOLD}http://localhost:$API_PORT${NC}"
echo -e "  API Docs  → ${BOLD}http://localhost:$API_PORT/docs${NC}"
echo -e "  Dashboard → ${BOLD}http://localhost:$DASHBOARD_PORT${NC}"
echo -e "${BOLD}──────────────────────────────────────${NC}"
echo ""
echo "Press Ctrl+C to stop both services."
echo ""

# ── 7. Trap Ctrl+C and kill both processes ───────────────────
trap "echo ''; echo 'Stopping…'; kill $API_PID $DASH_PID 2>/dev/null; echo 'Done.'; exit 0" INT

# Wait for background jobs
wait
