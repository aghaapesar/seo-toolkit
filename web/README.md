# Seo Toolkit Web UI

Bilingual (English / فارسی) dashboard for all Seo Toolkit features.

## Run

```bash
cd ~/Projects/seo-toolkit
source venv/bin/activate
pip install -r web/requirements-web.txt
uvicorn web.app.main:app --reload --host 127.0.0.1 --port 8000
```

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000 | Dashboard |
| http://127.0.0.1:8000/tools/index-diff | URL Index Diff |
| http://127.0.0.1:8000/tools/scraping | SEO Scraping |
| http://127.0.0.1:8000/docs | OpenAPI |

Use `?lang=en` or `?lang=fa` for language. Default: Persian (FA).

## Features in UI

| Mode | Web | CLI fallback |
|------|-----|--------------|
| Content Analysis | Upload + CLI guide | Full AI workflow |
| SEO Scraping | Full API | — |
| Content Generation | Upload + CLI guide | Full AI workflow |
| Internal Linking | Full API | — |
| Synonym Finder | Full API (needs AI keys) | — |
| Index Diff | Full API | — |
