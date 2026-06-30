# Seo Toolkit - Architecture

## Overview

Seo Toolkit is a Python CLI and web-assisted SEO automation suite optimized for Persian/Farsi content workflows.

```
main.py
  └── src/app/toolkit.py (SeoToolkit)
        ├── src/cli/          Interactive prompts and logging
        ├── src/services/     Index diff and shared services
        └── src/*.py          Domain modules (AI, sitemap, export, ...)
```

## Operational Modes

| Mode | CLI flag | Primary modules |
|------|----------|-----------------|
| Content optimization | `--mode content` | `data_loader`, `analyzer`, `ai_processor`, `clustering`, `knowledge_base` |
| SEO scraping | `--mode scraping` | `sitemap_manager`, `page_scraper` |
| Content generation | `--mode generation` | `content_generator`, `document_exporter`, `internal_linker` |
| Internal linking | `--mode linking` | `internal_linker` |
| Synonym finder | `--mode synonyms` | `synonym_finder`, `ai_model_manager` |
| URL index diff | `--mode index-diff` | `sitemap_manager`, `url_index_tracker` |

## Data Flow - Content Mode

1. Load Search Console Excel from `input/`
2. Identify high-potential queries (`analyzer`)
3. Match queries to sitemap URLs
4. Generate AI improvements for matched URLs
5. Cluster unmatched keywords into new article ideas
6. Deduplicate via `knowledge_base`
7. Export Excel reports to `output/`

## Data Flow - Index Diff Mode

1. Load submitted URL history from `index_history/{domain}/`
2. Fetch and parse sitemap (`sitemap_manager`)
3. Normalize and diff URLs (`url_index_tracker`)
4. Export `new_urls_*.txt` and `already_submitted_*.txt`
5. Optionally mark new URLs as submitted

## Configuration

- `config.yaml` (local, gitignored) from `config.sample.yaml`
- Legacy `ai` block + modern `ai_models` multi-provider config
- `app.sitemap_url`, `app.min_position`, clustering thresholds

## Web Layer (FastAPI)

- `web/app/main.py` exposes REST + HTML dashboard
- Reuses `UrlIndexTracker` and `SitemapManager` services
- API docs at `/docs`

## Persistence

| Path | Purpose |
|------|---------|
| `knowledge_base/` | Per-project content history |
| `index_history/` | Per-domain submitted URL tracking |
| `sitemaps/` | Cached sitemap XML |
| `output/` | Excel, documents, index diff exports |
| `logs/seo_toolkit.log` | Application log |
