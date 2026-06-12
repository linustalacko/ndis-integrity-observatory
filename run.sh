#!/usr/bin/env bash
# NDIS Provider Integrity Observatory — start API + frontend.
set -e
cd "$(dirname "$0")"

echo "→ API on http://localhost:8000"
uv run uvicorn api.server:app --port 8000 --reload &
API_PID=$!

echo "→ Frontend on http://localhost:5173"
( cd frontend && npm run dev -- --port 5173 ) &
WEB_PID=$!

trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
wait
