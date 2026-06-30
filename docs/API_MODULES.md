# Seo Toolkit - Module Reference

## Core Application

### `src/app/toolkit.py` - `SeoToolkit`
- **Input:** `config.yaml` path
- **Output:** Dispatches all operational modes
- **Alias:** `SEOContentOptimizer` (backward compatible)

## CLI

### `src/cli/prompts.py`
- `print_banner()`, `get_project_name_interactive()`, `select_mode_interactive()`, `select_project_interactive()`

### `src/cli/sections.py`
- `print_section(title, step)`

### `src/cli/logging_setup.py`
- `configure_logging(verbose)` → writes `logs/seo_toolkit.log`

## Services

### `src/services/url_index_tracker.py` - `UrlIndexTracker`
- **Input:** domain name, sitemap URL list, optional import txt; `base_dir` + `flat=True` for project-scoped history
- **Output:** new/submitted URL lists, history JSON, txt exports
- **Key methods:** `diff()`, `import_from_txt()`, `mark_batch_submitted()`, `export_txt()`, `get_status()`

### `src/services/project_manager.py` - `ProjectManager`
- **Input:** project name, domain, optional sitemap URL
- **Output:** CRUD on `projects/registry.json`; per-project folder layout via `get_paths()`
- **Key methods:** `create_project()`, `list_projects()`, `get_project()`, `update_project()`, `delete_project()`

## Domain Modules (`src/`)

| Module | Role |
|--------|------|
| `data_loader.py` | Load Search Console Excel exports |
| `analyzer.py` | Opportunity scoring, URL matching |
| `ai_processor.py` | AI content improvements and clustering |
| `ai_model_manager.py` | Multi-provider model selection |
| `clustering.py` | Keyword cluster validation and ranking |
| `excel_writer.py` | Excel report generation |
| `sitemap_manager.py` | Sitemap download, cache, index parsing |
| `page_scraper.py` | On-page SEO metadata scraping |
| `knowledge_base.py` | Project memory and duplicate detection |
| `content_generator.py` | AI article generation from Excel headings |
| `document_exporter.py` | Word/HTML export |
| `internal_linker.py` | Semantic internal link insertion |
| `file_selector.py` | Interactive file picker |
| `synonym_finder.py` | Persian keyword variation discovery |

## Web (`web/app/`)

| File | Role |
|------|------|
| `main.py` | FastAPI app, dashboard routes |
| `routers/projects.py` | Multi-project CRUD API |
| `routers/modes.py` | All mode endpoints (project-scoped uploads) |
| `routers/index_diff.py` | Index diff API endpoints |
| `routers/health.py` | Health check |
