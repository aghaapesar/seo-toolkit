# Seo Toolkit - Installation Guide

## Requirements

- Python 3.8+
- Internet access for AI APIs and sitemap downloads

## Setup

```bash
cd ~/Projects/seo-toolkit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp config.sample.yaml config.yaml
```

Edit `config.yaml` with your AI provider keys or use environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Quick Start

```bash
python main.py --mode content --test
python main.py --mode index-diff --domain example.com
```

## Web UI (optional)

```bash
pip install -r web/requirements-web.txt
uvicorn web.app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `config.yaml not found` | `cp config.sample.yaml config.yaml` |
| No connected AI models | Verify API keys; run `python test_connection.py` |
| Empty sitemap URLs | Check sitemap URL and network access |
| Import errors | Activate venv and reinstall requirements |

## Project Layout

See [ARCHITECTURE.md](ARCHITECTURE.md) and [API_MODULES.md](API_MODULES.md).
