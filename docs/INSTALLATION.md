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
python main.py --mode content-cluster --excel input/keywords.xlsx --cluster-method hybrid --model gapgpt_gpt4o_mini
```

### GapGPT API (گپ جی‌پی‌تی)

Add in `config.yaml` or via **Settings** in the web UI:

```yaml
ai_models:
  default: gapgpt_gpt4o_mini
  gapgpt_gpt4o_mini:
    provider: gapgpt
    api_key: YOUR_GAPGPT_API_KEY
    base_url: https://api.gapgpt.app/v1
    model: gpt-4o-mini
```

See [CONTENT_CLUSTER.md](CONTENT_CLUSTER.md) for the full Mode 7 workflow.

## Web UI (optional)

```bash
pip install -r web/requirements-web.txt
uvicorn web.app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000 — use **Projects** in the sidebar to create sites and switch between them.

### Product Gap (Mode 10)

1. Run **Site Index** for the project (products must be indexed).
2. Open **شکاف محصولات / Product Gap** — upload SEOSignal keyword Excel files.
3. Click **به‌روزرسانی تحلیل / Update analysis** — a **progress bar** shows status while matching runs in the background (may take a few minutes).
4. Optional: **تطبیق دقیق‌تر با AI** is enabled by default — LLM matches keywords and classifies page types (product/category/blog) from URL, title, and name. Requires AI model in Settings.
5. After **Update analysis**, check the summary timestamp and **AI** badge — a new snapshot is saved each run (not a stale cache).
6. Review the **کیورد تحقیق / Keyword research** tab: full keyword list sorted by volume, **page type**, sibling keywords, product link via icon, and **تکرار محصول** (how many keywords map to the same URL).
7. Remove irrelevant keywords with the row **حذف** button or bulk **حذف انتخاب‌شده‌ها** (saved exclusions persist across refreshes).
8. **Bulk actions** (top toolbar): select rows with ☑ → **حذف دائمی**, **آرشیو**, **انتقال به تب…**, or **خروجی اکسل** — works on every tab.
9. **Move** rows between tabs (موجود / تامین / پیشنهاد دسته / **تولید بلاگ**) via bulk toolbar or per-row dropdown.
10. **Blog content** tab: keywords moved here for article production; export via `list_name=blog_suggestions`.
11. **Archive** from any tab; **restore** from unified **آرشیو** tab.
12. Check **needs procurement** list sorted by priority (search volume + competition).
13. Semantic matching groups variants like «جالیز» and «خرید بازی فکری جالیز» under the same product.

### Technical Issues Check — Persian PDF (v4.8.0 – v4.13.0)

1. Open **بررسی مشکلات فنی / Technical Issues Check** in the sidebar (login required).
2. Select a project — **آدرس سایت‌مپ پروژه** is pre-filled from the project (e.g. `/blog/sitemap_index.xml`); the crawl stays in that folder scope.
3. Choose sample size (10–5000 pages) **or check «کرال کامل همه صفحات سایت‌مپ»** to audit every URL from that sitemap.
4. Expand **تنظیمات جلد و هدر گزارش PDF** to edit cover title, prepared-by, agency, page headers, and section headings.
5. The tool auto-detects the CMS/stack (WordPress, Shopify, Next.js, Laravel, …) and adds platform-specific solutions to each issue.
6. Watch progress on the task page; when done, download the **ZIP package** (PDF + JSON + Excels), or individual PDF / technical / content / all Excel files.
7. In Excel, set **وضعیت** to `☑ انجام‌شده` for fixed rows (they turn green). Re-upload the file under **بررسی مجدد بعد از آپدیت اکسل** to re-scan open rows and get a notification for anything still broken.
8. Previous reports stay under `projects/{slug}/output/technical_audit/` with unique timestamps (history is no longer overwritten).

Requires `fpdf2` + `uharfbuzz` + `openpyxl` (in `requirements.txt`) and bundled Vazirmatn fonts in `assets/fonts/`.

### Internal Link Intelligence (Mode 11)

1. Run **Site Index** for the project (full sitemap scrape required).
2. Open **لینک داخلی هوشمند / Internal Link Hub**.
3. Tab **گراف لینک**: click **Analyze link graph** — orphans, hubs, content islands.
4. Tab **پیشنهاد لینک**: filter by page type → select target products/pages (multi-select).

### Knowledge Exporter (RAG Markdown)

Export sitemap pages to Markdown parts for chatbot Knowledge Base:

```bash
# Standalone module
python -m src.knowledge_exporter \
  --sitemap https://example.com/sitemap.xml \
  --output output/knowledge_export \
  --max-part-kb 500 \
  --max-pages-per-part 50 \
  --concurrency 4

# Via main CLI
python main.py --mode knowledge-export \
  --sitemap https://example.com/sitemap.xml \
  --knowledge-output output/knowledge_export
```

Output:
- `pages/{type}/{slug}.md` — one RAG Markdown file per URL (YAML frontmatter)
- `index.json` — registry of all pages, paths, hashes, status
- Optional `knowledge_part_01.md`, … (legacy multi-doc parts)
- `.cache/` — downloaded HTML for re-runs (ETag / Last-Modified)

Options: `--include-pattern`, `--exclude-pattern`, `--urls-file`, `--rate-limit`, `--timeout`, `--max-retries`.

### Knowledge Exporter — Web UI

1. Open **خروجی Knowledge Base / Knowledge Base Export** from the dashboard (Mode 12).
2. **Phase 1** — click **Analyze sitemap**; URLs grouped by path pattern; staleness report (new/stale/unchanged).
3. Select patterns (checkboxes); each row shows pattern, type badge, sample titles.
4. **Phase 2** — pick AI model, test connection, set filters (blog, noindex, product sample limit) → **Start export**.
5. Download individual `pages/…` files, ZIP selection, or legacy `knowledge_part_*.md` from the tool page.

### Service status monitoring

1. Open **وضعیت سرویس‌ها / Service status** from the sidebar (System section). Sign in if prompted.
2. Click **بررسی الان / Check now** (or wait for auto-refresh every 60s).
3. Review Local (app, DB, config), Network (GapGPT hosts), and AI model cards.
4. Sparklines show **24h uptime** from stored samples (`data/seo_toolkit.db`).
5. Optional: uncheck **Test AI models** for a faster network-only refresh.
6. Settings page still shows a compact GapGPT network panel with a link to this page.

### Project task board

1. Open **یادداشت تسک‌ها / Project tasks** from the sidebar.
2. Select project from the top bar.
3. Add tasks with title and optional notes.
4. Drag cards between **در انتظار / در حال انجام / انجام شده** columns.
5. Set **priority**, **tags**, **Jalali due date**, and **assignee** on each card.
6. Expand **Subtasks** to add checklist items with their own assignee.

### Internal Link Intelligence — Web UI (continued)

5. Upload **GSC Performance** Excel (Pages + Queries sheets).
6. Click **پیشنهاد لینک داخلی** — AI suggests which pages should link to your targets (with anchor text).

## Multi-Project

See [MULTI_PROJECT.md](MULTI_PROJECT.md). Quick example:

```bash
python main.py --mode index-diff --project my-shop
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `config.yaml not found` | `cp config.sample.yaml config.yaml` |
| No connected AI models | Verify API keys; run `python test_connection.py` |
| Empty sitemap URLs | Check sitemap URL and network access |
| GapGPT connection error | Disconnect international VPN; run `./scripts/run_web.sh` from Terminal.app; check Settings → network status |
| Import errors | Activate venv and reinstall requirements |

## Project Layout

See [ARCHITECTURE.md](ARCHITECTURE.md) and [API_MODULES.md](API_MODULES.md).
