#!/usr/bin/env bash
# Start Seo Toolkit web UI (kills stale process on port 8000 first)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "Run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt -r web/requirements-web.txt"
  exit 1
fi

if [[ ! -f config.yaml ]]; then
  cp config.sample.yaml config.yaml
  echo "Created config.yaml from sample — add your API keys."
fi

lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Seo Toolkit → http://127.0.0.1:8000"
exec ./venv/bin/uvicorn web.app.main:app --host 127.0.0.1 --port 8000 --reload
