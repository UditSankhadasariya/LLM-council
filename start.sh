#!/bin/bash

# LLM Council — kill any existing backend on 8001 and restart in background
# Usage:  ./start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Kill anything on port 8001 (backend)
PIDS=$(lsof -ti :8001 2>/dev/null)
if [ -n "$PIDS" ]; then
  echo "Killing existing backend on port 8001: $PIDS"
  kill -9 $PIDS
fi

# Kill leftover Chrome instances bound to our debug ports (9222 = ChatGPT, 9223 = Gemini)
for PORT in 9222 9223; do
  CHROME_PIDS=$(lsof -ti :$PORT 2>/dev/null)
  if [ -n "$CHROME_PIDS" ]; then
    echo "Killing leftover Chrome on port $PORT: $CHROME_PIDS"
    kill -9 $CHROME_PIDS
  fi
done

# Kill any stray Chrome processes pinned to our profile dirs (in case they're
# not listening on the debug port but still holding the SingletonLock)
pkill -9 -f "user-data-dir=$HOME/.chatgpt_profile" 2>/dev/null
pkill -9 -f "user-data-dir=$HOME/.gemini_profile"  2>/dev/null

# Remove stale SingletonLock files so a fresh Chrome can claim the profile
rm -f "$HOME/.chatgpt_profile/Singleton"{Lock,Cookie,Socket} 2>/dev/null
rm -f "$HOME/.gemini_profile/Singleton"{Lock,Cookie,Socket}  2>/dev/null

# Give the OS a moment to release the ports
sleep 1

# Start backend in background, detached from terminal
(nohup uv run python -m backend.main > council.log 2>&1 &)

echo "Backend started in background → http://localhost:8001"
echo "Logs: tail -f $SCRIPT_DIR/council.log"
echo

# --- Post-launch verification ---------------------------------------------
# Wait until BOTH browser providers are actually usable. We check three things:
#   1. /api/health reports the provider as ready
#   2. Chrome is listening on the provider's debug port (CDP /json/version)
#   3. There is a tab in that Chrome whose URL matches the target site
# If any check fails after the timeout, print actionable hints.
#
# Note: a tab the user opens in their *regular* Chrome window is invisible to
# the backend — only tabs inside the script-launched Chrome (with the matching
# --remote-debugging-port) can be controlled.

WAIT_SECS=120        # generous: covers cold Chrome boot + first-time login wait
POLL_INTERVAL=2

check_provider() {
  # $1 = provider key in /api/health (chatgpt|gemini)
  # $2 = debug port (9222|9223)
  # $3 = host substring expected in a CDP tab URL (chatgpt.com|gemini.google.com)
  local name=$1 port=$2 host=$3

  local health
  health=$(curl -s --max-time 2 "http://localhost:8001/api/health" 2>/dev/null) || return 1
  echo "$health" | grep -q "\"$name\"" || return 1
  # Crude JSON probe: look for "<name>": { ... "ready": true ... } block
  echo "$health" | python3 -c "
import json,sys
d=json.load(sys.stdin)
p=d['providers'].get('$name',{})
sys.exit(0 if p.get('ready') else 1)
" 2>/dev/null || return 1

  # CDP listening?
  curl -s --max-time 2 "http://127.0.0.1:$port/json/version" >/dev/null 2>&1 || return 2

  # Tab matching the target site?
  curl -s --max-time 2 "http://127.0.0.1:$port/json" 2>/dev/null \
    | grep -q "\"url\":[^,]*$host" || return 3

  return 0
}

print_status() {
  local label=$1 rc=$2 port=$3 host=$4
  case $rc in
    0) echo "  ✓ $label ready (port $port, $host)" ;;
    1) echo "  … $label still initializing" ;;
    2) echo "  ✗ $label: Chrome not listening on debug port $port" ;;
    3) echo "  ✗ $label: Chrome up but no tab matching $host" ;;
    *) echo "  ✗ $label: unknown error (rc=$rc)" ;;
  esac
}

echo "Waiting for browser providers (up to ${WAIT_SECS}s)…"
deadline=$(( $(date +%s) + WAIT_SECS ))
chat_rc=99
gem_rc=99
while [ "$(date +%s)" -lt "$deadline" ]; do
  check_provider chatgpt 9222 chatgpt.com
  chat_rc=$?
  check_provider gemini  9223 gemini.google.com
  gem_rc=$?
  if [ $chat_rc -eq 0 ] && [ $gem_rc -eq 0 ]; then
    echo "  ✓ ChatGPT ready (port 9222, chatgpt.com)"
    echo "  ✓ Gemini  ready (port 9223, gemini.google.com)"
    echo "All browser providers are up."
    exit 0
  fi
  sleep $POLL_INTERVAL
done

echo
echo "Provider readiness timed out after ${WAIT_SECS}s:"
print_status "ChatGPT" $chat_rc 9222 chatgpt.com
print_status "Gemini " $gem_rc  9223 gemini.google.com
echo
echo "Hints:"
echo "  • If a Chrome window opened to the wrong page, leave it — the backend"
echo "    will navigate it once login is detected. Do NOT open the site in a"
echo "    different Chrome window — only the script-launched window (with"
echo "    --remote-debugging-port) is reachable from the backend."
echo "  • If you need to log in, do it in the launched Chrome window, then"
echo "    re-run: $0"
echo "  • Inspect: tail -f $SCRIPT_DIR/council.log"
exit 1

