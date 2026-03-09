#!/bin/bash

# LLM Council — kill any existing backend on 8001 and restart in background
# Usage:  ./start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Kill anything on port 8001
PIDS=$(lsof -ti :8001 2>/dev/null)
if [ -n "$PIDS" ]; then
  echo "Killing existing process(es) on port 8001: $PIDS"
  kill -9 $PIDS
fi

# Start backend in background, detached from terminal
(nohup uv run python -m backend.main > council.log 2>&1 &)

echo "Backend started in background → http://localhost:8001"
echo "Logs: tail -f $SCRIPT_DIR/council.log"
