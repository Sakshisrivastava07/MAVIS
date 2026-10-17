#!/usr/bin/env sh
# Open web, API, and agent in separate terminal windows where supported.
cd "$(dirname "$0")/.."
python -m http.server 5500 --directory web &
python -m uvicorn api.server:app --host 127.0.0.1 --port 8001 &
python agent/agent.py dev &
wait
