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

# Cursor/IDE shells inject local HTTP_PROXY that breaks outbound sitemap downloads.
# config.yaml app.http_proxy is the supported way to set a real VPN proxy.
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
unset SOCKS_PROXY SOCKS5_PROXY socks_proxy socks5_proxy

echo "Seo Toolkit → http://127.0.0.1:8000"
exec ./venv/bin/uvicorn web.app.main:app --host 127.0.0.1 --port 8000 --reload
