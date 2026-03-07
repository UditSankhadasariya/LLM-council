#!/bin/bash

# LLM Council — single command to start backend + frontend
# Usage:  ./start.sh        (start both)
#         Ctrl+C             (stop both)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Stopped."
}
trap cleanup SIGINT SIGTERM EXIT

# Backend (port 8001) — launches Chrome browsers for ChatGPT & Gemini
echo "Starting backend on http://localhost:8001 ..."
.venv/bin/python -m backend.main &
BACKEND_PID=$!

# Give the backend a moment before starting the frontend
sleep 2

# Frontend (port 5173)
echo "Starting frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo ""
echo "LLM Council is running!"
echo "  Backend:  http://localhost:8001"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

wait
