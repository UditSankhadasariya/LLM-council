#!/bin/bash

# LLM Council — single command to start backend + frontend with visible logs
# Usage:  ./start.sh        (start both with color-coded logs)
#         Ctrl+C             (stop both)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "LLM Council is starting..."
echo "  Backend:  http://localhost:8001"
echo "  Frontend: http://localhost:5173"
echo ""

npx concurrently \
  -n "backend,frontend" \
  -c "cyan,magenta" \
  "python -m backend.main" \
  "cd frontend && npm run dev"
