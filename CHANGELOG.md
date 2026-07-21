# Changelog - Seo Toolkit

All notable changes to this project will be documented in this file.

## v4.12.0 (2026-07-21)

### Naming, categories & access refactor
- Renamed **ممیزی سئو تکنیکال** → **بررسی مشکلات فنی** / Technical Issues Check (UI, PDF defaults, CTAs, progress copy)
- Cleared name collisions: Content Audit → **تطبیق تقویم محتوا** / Calendar Sync; SEO Scraping → **استخراج متادیتا** / Metadata Export; Link Inserter vs Internal Link Hub
- New `web/app/tool_registry.py`: single `LOGIN_REQUIRED_TOOLS` + `JOB_TYPE_TO_TOOL` (content-audit, site-index, content-cluster now login-gated on the page like their APIs)
- Sidebar group label **ایندکس و بررسی فنی**; TOOLS order places technical check next to site-index
- Descriptions clarify non-overlapping roles (Excel field export vs full technical PDF vs calendar sync vs link hub)

## v4.11.0 (2026-07-21)

### Technical SEO Audit — use project sitemap (path-scoped)
- Crawl base keeps subdirectory from project sitemap/domain (e.g. `https://zitro.ir/blog` from `/blog/sitemap_index.xml`) instead of collapsing to domain root
- Site-level sitemap check prefers the **project’s configured sitemap URL** before probing `/sitemap.xml`
- URL sample filtered to the same path scope so pages outside the project sitemap folder are not mixed in
- New form field **آدرس سایت‌مپ پروژه** pre-filled from the project; optional one-off override supported
- Result JSON records `sitemap_url`, `base_path`, and `sitemap_url_count` for transparency

## v4.10.0 (2026-07-21)

### Technical SEO Audit — editable PDF branding
- New form section **تنظیمات جلد و هدر گزارش PDF** on `/tools/technical-audit`
- Editable before generation: cover title, client/project name, prepared-by, agency/company, cover footer, page header (right/left), and section headings (summary / issues / task plan)
- Values passed into the PDF renderer (`ReportBranding`); blank fields fall back to Persian defaults or project name / site URL
- Last branding choices remembered in `localStorage` for the next run
- API: branding fields accepted on `POST /api/v1/technical-audit/start`; `GET /api/v1/technical-audit/branding-defaults` returns defaults

## v4.9.0 (2026-07-21)

### Technical SEO Audit — full crawl, stack-aware solutions, Persian fix
- **Full sitemap crawl**: new checkbox «کرال کامل همه صفحات سایت‌مپ» — audits every sitemap URL (safety cap 5000); manual sample raised to 10–5000 pages
- **CMS/stack detection**: homepage HTML + headers → WordPress, WooCommerce, Shopify, Magento, Joomla, Drupal, Next.js, Nuxt, Laravel, Django, ASP.NET
- **Stack-specific solutions (Persian)**: each issue now shows «راهکار در {پلتفرم}» tailored to the detected stack (e.g. Rank Math/Yoast for WordPress, next-sitemap for Next.js, spatie packages for Laravel); included in issue cards and the prioritized task table; detected platform shown in executive summary
- **Fix Persian half-space (نیم‌فاصله)**: fpdf2's bidi pass drops ZWNJ, gluing words (نمی‌شود → نمیشود); ZWNJ is now mapped to narrow no-break space (U+202F) so half-spaced words render correctly throughout the PDF

## v4.8.0 (2026-07-21)

### Technical SEO Audit — Persian PDF report
- New tool **ممیزی سئو تکنیکال / Technical SEO Audit** at `/tools/technical-audit` (sidebar → Index)
- **27-check engine** (`src/technical_seo_audit.py`):
  - Site level: HTTP→HTTPS redirect, www canonicalization, robots.txt, sitemap.xml, soft-404, favicon
  - Page level (sitemap sample up to 300): status/redirect chains, title (missing/duplicate/length), meta description (missing/duplicate), H1, canonical, noindex, image alt, viewport, `lang`, JSON-LD schema, Open Graph, mixed content, response time, HTML size, URL structure, broken internal links
- **Health score 0–100** weighted by severity and prevalence
- **Persian RTL PDF report** (`src/seo_pdf_report.py`, fpdf2 + Vazirmatn + text shaping):
  cover with score ring, executive summary with severity KPIs, issue cards with راهکار/مسئول/حجم کار, prioritized task table for the dev & content teams
- Reports saved per project: `projects/{slug}/output/technical_audit/audit_*.pdf|.json` with download API
- Background job with live Persian progress; result on shared task page with PDF/JSON downloads
- API: `POST /api/v1/technical-audit/start`, `GET /api/v1/technical-audit/reports`, `GET /api/v1/technical-audit/download`
- Fix: register previously-unregistered routers in `main.py` (`content_audit`, `content_cluster`, `site_index`, `product_gap`, `internal_links`) — their APIs returned 404
- New deps: `fpdf2>=2.7.9`, `uharfbuzz` (Persian text shaping); bundled `assets/fonts/Vazirmatn-*.ttf`
- Tests: `tests/test_technical_audit.py` (aggregation, scoring, task plan, PDF output)

## v4.7.0 (2026-07-17)

### Service status monitoring (Phase 2)
- New page **وضعیت سرویس‌ها / Service status** at `/tools/service-status` (sidebar → System)
- Live probes: app, SQLite, `config.yaml`, GapGPT DNS/HTTPS, configured AI models
- SQLite history (`service_check_history`) with **24h uptime** sparklines; auto-refresh every 60s
- API: `GET/POST /api/v1/services/status`, `GET /api/v1/services/history`
- Settings page: restore `initSettingsPage` (network panel + model list) and link to full monitor

## v4.6.1 (2026-07-16)

### Fix — Knowledge Export settings API 404
- Register `settings_api` router in `main.py` so `/api/v1/settings/models` works (model picker on Knowledge Export page)

## v4.6.0 (2026-07-16)

### Knowledge Export — RAG per-URL export (Phase 1)
- **Per-URL Markdown**: `pages/{page_type}/{slug}.md` with RAG frontmatter (`url`, `title`, `page_type`, `lang`, `crawled_at`, `sitemap_lastmod`, `content_hash`, `source`)
- **LLM structuring** via GapGPT (product vs blog templates); model picker + connection test before export
- **SQLite registry** (`knowledge_export_pages`) for export state, staleness, and first-download tracking
- **Filters**: exclude blog/noindex by default; optional product sample limit for testing
- **Incremental export**: skip unchanged pages when lastmod + content hash match registry
- **Downloads**: single file, multi-select ZIP with folder structure; legacy `knowledge_part_*.md` optional
- **Staleness report** after sitemap analyze (new / stale / unchanged counts)
- Register `knowledge_export` router in web app

## v4.5.2 (2026-07-07)

### Fix — header controls (project, theme)
- Fixed JavaScript syntax error in `app.js` that blocked the entire script from loading
- Project switcher and theme toggle wired via `initTopbar()` (no broken inline handlers)

## v4.5.1 (2026-07-07)

### Fix — 500 SessionMiddleware
- Register `SessionMiddleware` and `auth` router so login/session and protected pages work

## v4.5.0 (2026-07-07)

### Panel UX redesign — navigation, accessibility, live dashboard
- Sidebar tools grouped by category (Core SEO, Index, Content, Growth, Workflow) with search filter
- Skip-to-content link, focus-visible styles, reduced-motion support, `aria-current` on active nav
- **Dashboard** filled with live KPIs, bar/donut charts, and recent background jobs (`GET /api/v1/dashboard/summary`)
- Tool cards on home page grouped by the same categories

## v4.4.1 (2026-07-07)

### Project tasks — compact quick-add
- Add-task form is now a single input + button (title only)
- Priority, assignee, due date, tags, notes — edit inside each card under **Details**

## v4.4.0 (2026-07-07)

### Content calendar — assignee per card
- Kanban cards on **تقویم محتوا / Content calendar board** can be assigned to project members
- Assignee chip on card header + dropdown in card details
- API: `GET /api/v1/calendar/members`, `PATCH` item `assigned_user_id`

## v4.3.0 (2026-07-07)

### Project tasks — UI, subtasks, assignee, Jalali dates
- Redesigned task cards with collapsible details
- **Subtasks** with checkbox, per-subtask assignee, progress counter
- **Assign task** to project members
- All due-date pickers use **Jalali (Shamsi)** calendar

## v4.2.2 (2026-07-07)

### Project tasks — menu
- **یادداشت تسک‌ها** added to dashboard tool grid and sidebar tools list

## v4.2.1 (2026-07-07)

### Project tasks — priority, tags, due date
- Task cards: **priority** (high/medium/low), **tags**, **due date** with overdue highlight
- Sort by priority and due date within columns

## v4.2.0 (2026-07-07)

### Project task board (per-project Kanban)
- New page **یادداشت تسک‌ها / Project tasks** at `/tools/project-tasks`
- 3-column Kanban (pending / in progress / done) isolated per project
- Add title + notes, drag-drop, autosave notes
- Sidebar nav link; API: `/api/v1/project-tasks/*`

## v4.1.3 (2026-07-05)

### Knowledge Exporter — URL pattern segments + live sampling
- Segments grouped by **URL path pattern** (`/product/*`, `/blog/*`, …) — not by sub-sitemap file
- **Samples 3 pages per pattern**, detects content type from JSON-LD + page structure
- UI shows pattern, inferred type badge, sample titles

## v4.1.2 (2026-07-05)

### Knowledge Exporter — sitemap analysis & segment selection
- **Phase 1**: Analyze sitemap → segments by sub-sitemap, content type (product/category/blog/other), URL path prefix
- **Phase 2**: Select segments with checkboxes → export only chosen URLs
- API: `POST /api/v1/knowledge-export/analyze`

## v4.1.1 (2026-07-05)

### Knowledge Exporter — Web UI
- New tool **خروجی Knowledge Base / Knowledge Base Export** at `/tools/knowledge-export` (Mode 12)
- Background job with progress page, download links for `knowledge_part_*.md` and `index.json`
- API: `/api/v1/knowledge-export/*`

## v4.1.0 (2026-07-05)

### Knowledge Exporter (RAG Markdown export)
- New module **`knowledge_exporter`**: sitemap → RAG-ready Markdown parts for chatbot Knowledge Base
- Reuses existing **`sitemap_fetch`** for URL discovery
- Main content extraction via **trafilatura** + **readability-lxml** fallback + BeautifulSoup heuristics
- Per-page YAML frontmatter (`url`, `title`, `description`, `crawled_at`, `lang`)
- Part files `knowledge_part_01.md`, … with `\n\n---\n\n` document separators (max 500 KB or 50 pages per part)
- **`index.json`** manifest with URL, title, part file, char count, status
- Page cache (ETag / Last-Modified), duplicate content hash dedup, boilerplate line removal
- CLI: `python -m src.knowledge_exporter` or `python main.py --mode knowledge-export`

## v4.0.0 (2026-07-04)

### Internal Link Intelligence (Mode 11)
- New tool **لینک داخلی هوشمند / Internal Link Hub** at `/tools/internal-links`
- **Graph analysis**: orphan pages, inbound link hubs, content islands from indexed `internal_links`
- **GSC Performance** Excel import (Pages + Queries sheets)
- **AI inbound link recommendations**: select target URLs → LLM suggests source pages, anchor text, placement
- API: `/api/v1/internal-links/*`

## v3.9.5 (2026-07-04)

### Fix — Product Gap page 500
- Fixed missing `list_uploads` import in `pages.py` (product-gap tool page)

## v3.9.4 (2026-07-04)

### Product Gap — strict project isolation (follow-up)
- Delete per-upload and delete-all API + UI buttons on upload list
- Switching project updates URL/cookie without stale data from previous project
- Legacy Content Cluster files can only import into one project (global registry)
- List/results endpoints no longer auto-import on every page load

## v3.9.3 (2026-07-04)

### Product Gap — project isolation fix
- New projects no longer auto-import Excel files from global `output/web_uploads` (Content Cluster legacy folder)
- Each project only shows uploads from its own `projects/{slug}/keyword_research/` folder
- UI clears previous project data when switching projects; slug resolution prefers URL/cookie over stale select
- Legacy cluster import only via explicit sync with `import_legacy=true`

## v3.9.2 (2026-07-04)

### Product Gap — fix bulk move dropdown reset
- Bulk toolbar «انتقال به» dropdown no longer resets when choosing a tab (row-only auto-move handler)

## v3.9.1 (2026-07-04)

### Product Gap — selection + blog move fixes
- **لغو انتخاب** button; selections clear on page refresh, tab switch, and after move/archive
- Bulk move groups by source tab (fixes move to **تولید بلاگ** from keyword research tab)
- Backend saves prepared blog row on move; error when move finds no keywords
- Static assets cache-bust via `?v=` version query

## v3.9.0 (2026-07-04)

### Product Gap — تب «تولید بلاگ» (blog content)
- New tab **تولید بلاگ / Blog content** for keywords moved to blog/article production lists
- Manual move and bulk move support: on-site ↔ product ↔ category ↔ **blog**
- Archive, restore, and Excel export include `blog_suggestions` list
- Rows show `suggested_blog_title` and status **تولید بلاگ** in the main keyword table

## v3.8.5 (2026-07-03)

### Product Gap — fix SQLite «database is locked»
- Connection timeout + `busy_timeout=30s`, WAL on every open
- Schema migration runs once per process (not on every request)
- Archive no longer opens nested DB connections inside one transaction
- Connections closed after archive/restore writes

## v3.8.4 (2026-07-03)

### Product Gap — fix archive API error
- Fixed missing `Optional` import on `ArchiveKeywordsRequest` / `MoveKeywordsBulkRequest` (Pydantic TypeAdapter error on archive)

## v3.8.3 (2026-07-03)

### Product Gap — move dropdown styling
- Unified **gap-move-select** styling for bulk toolbar and per-row move dropdowns
- Matches app theme (colors, border, focus ring, chevron, RTL)

## v3.8.2 (2026-07-03)

### Product Gap — bulk actions toolbar (all tabs)
- Unified top bar: **select visible**, **delete**, **archive**, **move to tab**, **export**
- Works on every tab with checkboxes (keyword research, on-site, procurement, categories, archive)
- New API: `POST /api/v1/product-gap/move-bulk` for multi-keyword moves
- Archive auto-detects source tab when selecting from «کیورد تحقیق»

## v3.8.1 (2026-07-03)

### Product Gap — tab persistence + category move fix
- After move/archive/restore/delete the UI **stays on the same tab** (saved per project in sessionStorage)
- Fixed row lookup when moving keywords to **پیشنهاد دسته / category suggestions**
- Page no longer scrolls/jumps to the first tab on every action

## v3.8.0 (2026-07-03)

### Product Gap — manual move between tabs + unified archive
- **انتقال دستی** between tabs: on-site ↔ product procurement ↔ category suggestions (dropdown per row)
- **`POST /api/v1/product-gap/move`** persists manual placement across re-analyze
- **آرشیو یکپارچه** for all tabs (on-site, تامین محصول, پیشنهاد دسته) with source column
- Archive/restore/export generalized: `source_list` on archive, `archived_all` export
- DB: `product_gap_manual_rows` for curated tab placement

## v3.7.5 (2026-07-03)

### Product Gap — soft-delete archive + Excel export
- **تامین محصول**: انتقال به **آرشیو** (soft delete) — با re-import برنمی‌گردد مگر «بازگردانی»
- Tab **آرشیو تامین** with restore per row or bulk
- **خروجی اکسل** for product procurement and archived lists (`GET /export?list_name=…`)
- Hard delete (جدول اصلی) remains permanent exclusion; archive is restorable

## v3.7.4 (2026-07-02)

### Product Gap — suggest new category pages
- Category-intent keywords **without** a matching archive (e.g. «بازی دخترانه فکری») no longer match random products
- New tab **پیشنهاد دسته / New categories** with suggested category title and action text
- Main table: status **ایجاد دسته** + suggestion column; **تامین محصول** tab for SKU-level gaps only

## v3.7.3 (2026-07-02)

### Product Gap — category-intent keyword routing
- Broad keywords like **«بازی دخترانه فکری»** (no brand/SKU) now route to **category** pages, not random products (e.g. Lego Barbie)
- `match_intent`: category vs product; generic token overlap no longer matches single SKU pages
- AI prompt rejects product URLs when `category_intent=true`
- Category pages always included for intent routing even if «include categories» is unchecked

## v3.7.2 (2026-06-30)

### Product Gap — real AI pass + fresh results
- **AI enabled by default** on analyze; checkbox value parsed reliably from FormData
- When AI is on: **all keywords with candidates** go through LLM matching (not only borderline rows)
- **AI page-type classification** from URL path, title, product name, and H1 (product / category / blog)
- AI match results **override** rule scores when lookup exists
- `/results` returns `Cache-Control: no-store`; browser fetch uses cache-bust timestamp
- Summary shows **AI badge**, snapshot id suffix, and `analyzed_at` so you can confirm a new run

## v3.7.1 (2026-06-30)

### Product Gap — fix empty table body
- Restored missing `gapTruncate()` helper — chunked table render (1000+ rows) failed silently and showed headers only
- Safer per-cell error handling during chunked row build

## v3.7.0 (2026-06-30)

### Product Gap — AI matching, page types, sibling keywords, exclusions
- Optional **تطبیق دقیق‌تر با AI** (LLM + RAG) for borderline keyword ↔ page matches
- Table columns: **نوع صفحه** (product / blog / category) and **کیوردهای همان محصول** with volumes
- Exact duplicate keywords removed when merging multiple Excel uploads
- **Delete** single or selected keywords from the table (`POST /api/v1/product-gap/exclude`, persisted in SQLite)
- Catalog matching includes blog pages; categories optional via checkbox
- UI toolbar: select visible rows, delete selected; per-row delete button

## v3.6.8 (2026-07-02)

### Product Gap — fix NaN JSON error on refresh
- Excel empty cells produced `NaN` in snapshot JSON → API failed with «not JSON compliant»
- Sanitize NaN/Inf on save, load, and API response (existing snapshots repaired on read)

## v3.6.7 (2026-07-02)

### Product Gap — faster table load
- API returns slim payload (~half size) — no duplicate on_site/missing arrays
- Only the main «کیورد تحقیق» tab renders on load; other tabs load on click
- Live row progress: «۱۲۰ از ۱۰۶۸ ردیف (۱۱٪)» while the table builds

## v3.6.6 (2026-07-02)

### Product Gap — results table always visible
- Login required on product gap page (API data needs session)
- Results section visible when a project is selected (no longer hidden below fold)
- Server-side snapshot summary + «↓ مشاهده جدول» jump link
- Reliable load from saved snapshot on page open

## v3.6.5 (2026-07-02)

### Product Gap — fix empty results after analysis
- After job completes, reload results from `/api/v1/product-gap/results` (reliable display)
- Job payload no longer embeds full 2MB+ analysis (prevents poll/render failures)
- Chunked table rendering for 200+ rows + «در حال ساخت جدول…» loading state

## v3.6.4 (2026-07-02)

### Product Gap — keyword table + progress bar
- Main table: full keyword research list first (sorted by volume)
- Product link as icon only (clean table); product name shown as short text
- Column **تکرار محصول در کیوردها** — how many research keywords map to the same site product
- Background analysis with **real progress bar** (poll job, no page hang)

## v3.6.3 (2026-07-02)

### Product Gap — full tables (all rows)
- Removed 300-row display cap — all keywords shown in scrollable tables
- New tab **همه کیوردها** with complete master table (status, product, priority)
- Product groups as flat table (one row per keyword per product)
- Search filter across table rows; sticky table headers
- Fixed silent load errors on page refresh

## v3.6.2 (2026-07-02)

### Product Gap — visible results section
- Results moved to a full-width **«نتایج تحلیل»** panel below the form (auto-scroll after analyze)
- Tabbed tables: **موجود در سایت** | **نیاز به تامین** | **گروه‌های محصول**
- Loading hint during long analysis (3+ minutes)

## v3.6.1 (2026-06-30)

### Fix — Product Gap «No keyword Excel uploads»
- Auto-sync keyword Excel from `projects/{slug}/keyword_research/` and project `input/`
- **Legacy import:** existing `output/web_uploads/seo_signal_*.xlsx` files are copied and registered on first sync
- Content Cluster uploads are now registered for Product Gap when a project is selected
- Analyze button syncs disk files before running; project slug resolved from form, hidden field, or cookie
- Fixed crash in analysis loop (`file_path` variable)

## v3.6.0 (2026-06-30)

### Semantic product matching (Product Gap)
- Keyword ↔ product matching uses distinctive token overlap (not exact string match)
- Strips commerce modifiers (خرید، ارزان، بازی فکری، …) to find core product identity
- Example: «جالیز», «بازی فکری جالیز», «خرید بازی فکری جالیز» → same product
- UI shows semantic product groups with combined search volume

### Kanban H2 heading editor
- Per-heading **Delete**, **Rewrite** (AI), and **Add H2** buttons on each card
- API: `PATCH /api/v1/calendar/items/{id}` with `h2_headings`, `POST .../h2-rewrite`
- Accessible labels (`aria-label`, `role="group"`, keyboard focus rings)

### Accessibility improvements
- Kanban columns/cards: `aria-labelledby`, `aria-label`, `aria-busy` on rewrite
- Product gap tables: `scope="col"`, live region for stats
- Focus-visible styles on icon buttons and sidebar toggle

## v3.5.0 (2026-06-30)

### Product Gap Analysis (Mode 10)
- Upload one or more keyword research Excel files (SEOSignal) per project
- **Update analysis** button: merges all uploads with latest Site Index products
- Lists **on site** vs **needs procurement** with priority (search volume + competition)
- API: `POST /api/v1/product-gap/upload`, `POST /api/v1/product-gap/analyze`, `GET /api/v1/product-gap/results`

### Kanban — 3 columns
- Columns simplified to: **در انتظار** / **در حال انجام** / **انجام شده**
- Legacy statuses migrated automatically in SQLite

### Collapsible sidebar
- Toggle button to hide/show navigation for more reading space
- Preference saved in `localStorage`

## v3.4.0 (2026-06-30)

### Site Index (Mode 9) — full crawl + product extraction
- Sitemap fetch (existing engine) → scrape every page with body, JSON-LD, product fields
- SQLite `site_pages` + `site_index_runs` per project with pause/resume checkpoint
- Task UI: progress bar, Pause, Resume from last URL, Refresh index button
- AI credit exhaustion detection + user notification to recharge

### Internal link suggestions on calendar cards
- Button on each Kanban card: AI + rule-based product/category link suggestions
- Uses indexed site pages; saves `suggested_links` on the card
- API: `POST /api/v1/calendar/items/{id}/link-suggestions`

## v3.3.0 (2026-06-30)

### Content Audit (Mode 8)
- New tool: fetch sitemap → scrape pages → match calendar campaign cards
- Suggests updating the **same** Kanban card when live title/H1/meta differ from plan
- Apply: link URL + move to review, or adopt live SEO fields
- Reuses `fetch_all_sitemap_urls` + `PageScraper` (same as Index Diff / Scraping)
- Calendar items gain `url`, `scrape_snapshot`, `last_scraped_at` fields

## v3.2.2 (2026-06-30)

### Calendar — delete campaigns & items
- Delete button (×) on each Kanban card
- Delete button on each campaign tab (removes campaign + all items)
- API: `DELETE /api/v1/calendar/items/{id}` and `DELETE /api/v1/calendar/campaigns/{id}`

## v3.2.1 (2026-06-30)

### Fix — SQLite migration for `campaign_id`
- Existing v3.1 databases failed with `no such column: campaign_id`
- Index creation moved to post-`ALTER TABLE` migration step
- Added `scripts/migrate_db.py` for one-shot repair

## v3.2.0 (2026-06-30)

### Content calendar campaigns (per project)
- Multiple campaigns per project (کمپین ۱، ۲، …)
- Campaign tabs with drag-reorder; drag cards onto tabs to move between campaigns
- Auto-create campaign on cluster import; optional campaign select in cluster form
- Legacy boards backfilled into campaigns on first load

### Jalali start date picker
- Content Cluster form uses Jalali year/month/day selects (hidden ISO for API)

### Light theme
- Toggle in top bar (☾/☀); persisted in `localStorage`

### H2 heading limits
- Min/max H2 fields in cluster form (0 = unlimited / no minimum)
- Wired into AI refine prompt and post-processing

### UI — info tooltips
- Field (i) hints are hover/focus CSS tooltips only (no click popover)

## v3.1.0 (2026-06-30)

### Content calendar Kanban board
- SQLite persistence: boards, items, status, notes, checklist
- 5 columns: planned → writing → review → scheduled → published
- Jalali dates on cards; drag-and-drop or dropdown move
- Auto-create board after cluster job completes

### Multi-user login (username/password)
- `/login` + session cookies
- `scripts/create_user.py create USER PASS [--admin] [--project SLUG]`
- Calendar board requires login; project ACL for editors

### Content Cluster UI
- Info (i) tooltips on method, model, calendar fields
- Link to calendar board from tool page and task completion

## v3.0.5 (2026-06-30)

### Fix — Content Cluster task page
- Back link and done message no longer redirect to Index Diff
- Job type maps to correct tool (`content_cluster` → `/tools/content-cluster`)
- Excel calendar sheet: H1, H2 headings, meta description columns

## v3.0.4 (2026-06-30)

### UI — form inputs & Content Cluster layout
- Unified styles for `select`, `number`, `date`, `password` in all tool forms
- Content Cluster page: 3-section layout (file / clustering / calendar)
- File picker button styling; responsive 2-column form grid
- Hide AI fields when rule/ML method selected

## v3.0.3 (2026-06-30)

### Fix — GapGPT works when DNS blocked (Cursor sandbox / VPN)
- `gapgpt_curl.py`: curl `--resolve` fallback with known GapGPT IPs
- Content cluster AI step uses curl transport for `gapgpt` provider
- Network check: DNS fallback IP + HTTPS probe via `--resolve`
- `scripts/restart_web.sh` for full port-8000 reset

## v3.0.2 (2026-06-30)

### Fix — GapGPT + VPN conflict
- `gapgpt_cdn` preset now maps to `gapgpt` provider (was "Unknown provider")
- Clearer Persian errors: DNS fail vs Cursor proxy 403 vs timeout
- Settings page: **GapGPT network status** panel (`GET /api/v1/settings/network-check`)
- Docs: VPN off → test GapGPT; run `./scripts/run_web.sh` from Terminal.app
- Fix duplicate error text on failed model test; preserve DNS error in network check

## v3.0.1 (2026-07-02)

### Fix — GapGPT / OpenAI connection error in Cursor
- OpenAI SDK now uses httpx with `trust_env=False` (ignores IDE-injected proxy)
- GapGPT test falls back to `https://api.gapapi.com/v1` CDN endpoint
- Clearer error message when proxy blocks outbound API calls

## v3.0.0 (2026-07-02)

### Mode 7 — Content Cluster & Calendar
- Import SEOSignal Excel (keyword, volume, competition, word count)
- Clustering methods: rule, ML, AI, **hybrid** (recommended)
- Difficulty scoring (easy → hard) + content calendar export (1 post/day default)
- CLI: `--mode content-cluster` with `--excel`, `--cluster-method`, `--posts-per-day`
- Web UI: `/tools/content-cluster` with background job + Excel download

### GapGPT API + Settings UI
- `gapgpt` provider (`https://api.gapgpt.app/v1`) in AIModelManager
- Settings page: add/test/delete AI models and API keys from the browser
- `GET/POST /api/v1/settings/models` API

## v2.9.5 (2026-07-01)

### Fix — Index Diff form completely broken
- Fixed JavaScript syntax error (`markSubmitted` declared twice) that prevented `app.js` from loading
- Form was falling back to GET navigation instead of starting background jobs

## v2.9.4 (2026-06-30)

### Index Diff — sitemap list + stuck spinner fix
- Main panel shows all fetched sitemap XML files (index + sub-sitemaps) and page URL preview
- Task completion page shows live sitemap fetch list and full sources after diff
- Sitemap sources saved in one step during diff (browser + server fetch paths)
- Progress spinner no longer stuck after back navigation or timeout (30s job start limit)

## v2.9.3 (2025-07-01)

### Index Diff — sitemap list in sidebar, fix stuck spinner
- Sidebar shows fetched sitemap XML files (root + sub-sitemaps) and URL preview
- Download link for full sitemap URL list
- Progress spinner no longer stuck after redirect/error
- Sub-sitemap sources saved during browser fetch

## v2.9.2 (2025-07-01)

### Fix — import shows `undefined` and ignores checkbox
- Parse `mark_submitted=false` correctly from multipart forms (was always true)
- Import result shows URLs in file, added/excluded, skipped per file
- Supports drip-feed txt exports (one URL per line)

## v2.9.1 (2025-07-01)

### Fix — task page 500 (Undefined is not JSON serializable)
- Safe i18n merge (EN fallback) for template strings
- `default` filter on task page `tojson` labels

## v2.9.0 (2025-07-01)

### Index Diff — downloadable file list and URL status archive
- Each diff run registers all output files with download links
- `url_status.csv` / `.json` per run — status: indexed, pending_index, excluded
- Export history on Index Diff page and task completion page
- `GET /api/v1/index-diff/files/{domain}` and `/download?path=`

## v2.8.0 (2025-07-01)

### Index Diff — sitemap snapshots, batch marking, sticky project
- Save full sitemap URL list (`sitemap_latest.txt` + dated archives)
- Optional import checkbox: register as indexed or diff-only exclusion
- Mark last diff batch or upload txt after indexing tool submission
- Sticky project via cookie + `?project=` on all nav links
- Sidebar status: sitemap count, submitted, pending batch

## v2.7.1 (2025-07-01)

### Fix — Index Diff `Not Found` on stale server
- Fallback to legacy diff flow when `/api/v1/jobs/index-diff/start` returns 404
- Clear hint to restart `./scripts/run_web.sh` for the progress page

## v2.7.0 (2025-07-01)

### Index Diff — recursive sitemaps, task progress page, background jobs
- **Recursive sub-sitemap expansion** in browser (nested sitemap indexes, relative `<loc>` URLs)
- **Server proxy** `/api/v1/sitemap/proxy` when CORS blocks sub-sitemap downloads
- **Background jobs** API (`POST /api/v1/jobs/index-diff/start`) with polling
- **Progress page** `/tasks/{job_id}` — progress bar, step list, done message

## v2.6.9 (2025-07-01)

### Index Diff — visible progress and browser sitemap index expansion
- Persistent progress panel + sidebar status (no silent “processing” disappear)
- Browser downloads full sitemap index + sub-sitemaps, sends URL list to server
- API accepts `urls_file` txt to skip server-side download

## v2.6.8 (2025-07-01)

### Fix — Index Diff 502 when browser can open sitemap
- Web UI fetches sitemap URL **in the browser** (CORS) and uploads XML to the server
- Avoids Python/server DNS issues when Terminal `curl` works but uvicorn cannot download

## v2.6.7 (2025-07-01)

### Fix — Index Diff `Not Found` (404)
- Stale uvicorn missed `/api/v1/index-diff/diff-form`; restart with `./scripts/run_web.sh`
- Web UI falls back to JSON `/diff` if `/diff-form` returns 404

## v2.6.6 (2025-07-01)

### Fix — sitemap download when curl works but Python fails
- `run_web.sh` unsets IDE-injected HTTP_PROXY before starting uvicorn
- HTTP client forces direct connection (no accidental Cursor proxy)
- macOS curl fallback when `requests` cannot resolve/connect (matches Terminal `curl` behavior)

## v2.6.5 (2025-06-30)

### Fix — blocked sitemap hosts (e.g. sargarmia.com)
- Shared HTTP client: browser headers, `trust_env=False` by default, optional `app.http_proxy` in config.yaml
- HTTPS→HTTP fallback and clearer connection errors
- **Upload sitemap.xml** on Index Diff when download fails (Save As from browser)
- Web uses `POST /api/v1/index-diff/diff-form` (URL and/or file)

## v2.6.4 (2025-06-30)

### Fix — sitemap download failures in web Index Diff
- Browser-like `User-Agent` and headers for sitemap HTTP requests
- Web diff uses non-interactive `fetch_all_sitemap_urls` (no CLI prompts on sitemap index)
- Auto-fetch all sub-sitemaps from sitemap index
- Namespace-agnostic XML parsing fallback
- Detailed 502 error message (SSL, 403, timeout, etc.)

## v2.6.3 (2025-06-30)

### Fix — Index Diff import `[object Object]` error toast
- Parse FastAPI validation errors (`detail` array) into readable messages
- Build multipart FormData explicitly for multiple txt files

## v2.6.2 (2025-06-30)

### Fix — Index Diff page 500 error
- Removed fragile `tojson` in template (caused `Undefined is not JSON serializable` on stale reload)
- Import labels passed via `data-*` attributes with safe defaults

## v2.6.1 (2025-06-30)

### Index Diff — multi-file import (web)
- Upload **multiple `.txt` files at once** on `/tools/index-diff`
- API accepts `urls_files[]` and returns per-file + total counts
- New `UrlIndexTracker.import_from_txt_files()` helper

## v2.6.0 (2025-06-30)

### Multi-project support
- Define multiple projects with isolated data folders under `projects/{slug}/`
- Each project: separate `input/`, `output/`, `knowledge_base/`, `index_history/`, `sitemaps/`
- CLI: `--project my-slug` flag on all modes
- Web: `/projects` page, project switcher in header, per-tool project select
- API: `GET/POST /api/v1/projects`
- Docs: `docs/MULTI_PROJECT.md`, updated `ARCHITECTURE.md` and `API_MODULES.md`

## v2.5.1 (2025-06-30)

### Web UI overhaul
- Full bilingual (EN/FA) dashboard with RTL support and Vazirmatn font
- Dedicated pages for all 6 operational modes
- REST API endpoints for scraping, linking, synonyms, index-diff
- Dark modern design system with responsive layout

## v2.5.0 (2025-06-30)

### Rebrand to Seo Toolkit
- Project renamed from `simple-seo-tool` / SEO Content Analysis & Optimization Tool to **Seo Toolkit**
- New log file: `logs/seo_toolkit.log`
- `SEOContentOptimizer` alias kept; primary class is `SeoToolkit`

### Architecture refactor
- Thin `main.py` CLI entry
- `src/app/toolkit.py` application core
- `src/cli/` prompts, sections, logging setup
- `src/services/url_index_tracker.py` shared service layer
- `docs/` architecture, installation, API modules

### New Mode 6: URL Index Diff
- Compare sitemap URLs against previously submitted indexing URLs
- Per-domain history in `index_history/`
- Export `new_urls_*.txt` and `already_submitted_*.txt`
- CLI flags: `--domain`, `--import`, `--mark-submitted`
- See `docs/INDEX_DIFF.md`

### Web MVP (FastAPI)
- Dashboard at `/`
- Index diff UI at `/index-diff`
- REST API at `/api/v1/index-diff/*` and `/docs`

### Tests
- pytest suite for analyzer, sitemap parser, knowledge base, URL tracker

## v2.4.0 (2024-10-13)

### ✨ New Mode 5: Keyword Synonym Finder 🔍

**Major Feature:**
- Find all semantic equivalents for keywords using AI
- Support for 8 categories of variations:
  1. Persian synonyms (مترادف‌های فارسی)
  2. Finglish standard (گوشی → gooshi, gushi)
  3. English keyboard typing (گوشی → ',ad)
  4. Colloquial abbreviations (اختصارات عامیانه)
  5. Common misspellings (غلط‌های املایی رایج)
  6. English equivalents (معادل انگلیسی)
  7. Abbreviations (مخفف‌ها)
  8. Related terms (واژگان مرتبط)

**How it Works:**
- Read keywords from Excel file (column 1)
- AI generates all possible variations
- Output Excel with 9 columns (original + 8 variation types)
- Comprehensive keyword coverage for SEO

**Use Cases:**
- Optimize content for all search variations
- Cover different ways users might search
- Improve keyword coverage
- Content localization and variations

### 📝 Content Generation Improvements

**Enhanced Prompts:**
- Stronger emphasis on NO conclusion per heading
- Clear instruction that conclusion comes ONLY at end
- Prevent phrases like "در نتیجه", "خلاصه" in section endings
- Added <p> tag instruction for clean HTML
- Improved conclusion prompt for comprehensive summary

**Result:**
- Clean, flowing content without multiple conclusions
- Single comprehensive conclusion at article end
- Better HTML rendering in browser

### 🔗 Internal Linking Improvements

**Duplicate Link Prevention:**
- Added final cleanup pass to remove duplicate URL links
- Keeps only first occurrence of each URL
- Replaces duplicate links with plain anchor text
- Better protection against same URL with different anchor texts

---

## v2.3.3 (2024-10-13)

### Added
- **New Mode 4: Internal Linking Only** 🔗
  - Standalone internal linking for existing content files
  - Supports HTML, Word (.docx), and text files
  - Interactive file selection from output/documents folder
  - Automatic link distribution and relevance checking
  - Preserves original file structure while adding internal links

### Enhanced
- **Content Generation Instructions**
  - Users can now provide additional content generation instructions
  - Instructions are automatically included in AI prompts
  - Supports custom structure requirements (FAQ, step-by-step guides, etc.)

### Fixed
- **Internal Linking Improvements**
  - Fixed KeyError for 'other' URL type in link distribution
  - Enhanced semantic matching for Persian content
  - Improved anchor text selection with 2-3 syllable product name priority
  - Even distribution of links throughout content (not just beginning/end)
  - One link per destination page limit implemented
  - Better relevance scoring with exact matches and keyword bonuses

### Technical
- Added comprehensive content harmony checking
- Enhanced error handling and user feedback
- Improved file export status reporting
- Better debugging and logging for internal linking process

## [2.3.2] - 2024-10-13

### 🔗 Advanced Internal Linking System

#### Smart Product Name Linking
- **2-3 Syllable Priority**: First 2-3 words of product names get highest priority for linking
- **Product Name Recognition**: 50+ Persian product words with syllable-based matching
- **Semantic Anchor Text**: Intelligent selection based on product relevance and context
- **Example**: "بذر پیاز سفید گرانوله" → links "بذر پیاز" (not "سفید")

#### Even Link Distribution
- **Content-Wide Spacing**: Links distributed evenly across entire content, not clustered
- **Two-Pass Algorithm**: First identifies all potential links, then selects for even distribution
- **Target Spacing**: Calculates optimal spacing based on content length and link count
- **Quality Preservation**: Maintains high-quality matches while ensuring even spread

#### Enhanced Word Export
- **Better Error Handling**: Added detailed logging for Word export process
- **Progress Feedback**: Real-time status updates during document creation
- **Exception Recovery**: Graceful handling of export failures with clear error messages

### Technical Improvements
- Enhanced `_find_best_anchor_text()` with product name prioritization
- Added `_find_semantic_anchor_text()` for 2-3 syllable product word matching
- Implemented `_select_links_with_even_distribution()` for optimal link placement
- Improved Persian product word database with syllable classification

---

## [2.3.1] - 2024-10-13

### 🔧 Bug Fixes & Improvements

#### Internal Linking System Enhancement
- **Improved Semantic Matching**: Enhanced algorithm for better content-to-URL relevance
- **Persian Word Relationships**: Added semantic groups for Persian content (گل، بذر، کاشت، آبیاری، خاک، کود، باغچه)
- **Better Phrase Matching**: Exact phrase matches now get 0.8 score (was lower)
- **Partial Word Support**: Added support for partial keyword matches (0.2 score)
- **URL Path Relevance**: URLs with matching terms in path get bonus points
- **Lowered Threshold**: Reduced matching threshold from 0.3 to 0.15 for more links
- **Debug Information**: Added detailed logging for link match scores and URLs

#### Word Export Fix
- **Fixed Missing Dependency**: Installed python-docx package (was causing ModuleNotFoundError)
- **Word Document Creation**: Fixed Word export functionality that was completely broken
- **Document Exporter**: Now fully functional for creating .docx files

#### Version Management
- **Dynamic Version Reading**: main.py now reads version from VERSION file automatically
- **Version File Update**: Updated VERSION file to 2.3.1
- **Banner Update**: Application banner now shows current version dynamically

### Technical Details
- Enhanced `_calculate_match_score()` method with better Persian language support
- Added `_has_semantic_similarity()` method for context-aware linking
- Improved debug logging throughout internal linking process
- Fixed python-docx import error in DocumentExporter

---

## [2.3.0] - 2024-10-12

### 🔧 Updates & Improvements (2024-10-13)

#### Content Generation Workflow Redesign
- **Automatic Topic Reading**: Main topic automatically read from first column (no manual input)
- **Header Detection**: First row treated as column headers
- **Interactive Word Count**: Ask for total article words, then distribute per heading
- **Per-Heading Generation**: Generate content for each heading separately with custom word counts
- **Introduction & Conclusion**: Automatically generated based on article content
- **Complete Articles**: Each row becomes one complete article with intro, body, and conclusion

#### Fixes
- Fixed: Content generation now reads Excel files from `output/` folder instead of `input/`
- Fixed: File selector shows files from output directory for Mode 3
- Improved: Better user guidance when no files are found

#### User Experience
- **Excel Structure**:
  - Row 1: Column headers
  - Column 1: Article topic (automatically used)
  - Columns 2-6: Additional data (predictions, clusters, content type, search intent, word count)
  - Columns 7+: H2 headings (only these used for content generation)
  - Each row = One complete article
- **Smart Column Detection**: Automatically identifies heading columns by "هدینگ H2" pattern
- **Interactive Process**: Confirm each article, set word counts, review progress
- **Smart Prompts**: Separate prompts for headings, introduction, and conclusion

### 🎉 Major Features

#### AI Content Generation System ✨ NEW
- **Content Generator**: Full Persian SEO content generation from Excel headings
- **Multi-Format Export**: Automatic export to Excel, Word (.docx), and HTML formats
- **Smart Content Prompt**: Specialized Persian SEO prompt with E-E-A-T principles
- **Natural Writing**: Random spacing variations for natural appearance
- **Batch Processing**: Process multiple headings in one run with progress tracking

#### Multi-Model AI Support 🤖 NEW
- **Multiple Provider Support**: OpenAI, Claude (Anthropic), Gemini (Google), Grok
- **Model Configuration**: Configure unlimited AI models in `config.yaml`
- **Connection Testing**: Test all configured models before use
- **Default Model**: Set a default model for all operations
- **Per-Operation Selection**: Choose different models for different tasks
- **Environment Variables**: Support for `env:VAR_NAME` to read API keys securely

#### Smart Internal Linking System 🔗 NEW
- **Sitemap Analysis**: Parse and categorize URLs from sitemap
- **URL Categorization**: Automatic detection of categories, products, blogs
- **Semantic Matching**: Links based on content relevance
- **Smart Rules Implementation**:
  - 1 link per 300-400 words
  - No links in headings
  - Priority system: Categories > Products > Blog posts
  - Anchor text optimization (max 5 syllables)
- **Fuzzy Matching**: Intelligent anchor text selection with similarity matching

#### Document Export System 📄 NEW
- **Word Export**: Formatted .docx documents with proper structure
- **HTML Export**: Editor-ready HTML (no wrapper tags)
- **SEO Information**: Separate title and meta description sections
- **Batch Export**: Export all generated content at once
- **Structure Preservation**: Maintains headings, bold text, lists, links

### 🛠️ New Modules

- `src/ai_model_manager.py`: Multi-provider AI model management
- `src/content_generator.py`: AI content generation engine
- `src/internal_linker.py`: Smart internal linking system
- `src/document_exporter.py`: Word and HTML export functionality

### 🔧 Configuration Changes

- Added `ai_models` section in `config.yaml` for multi-model configuration
- Legacy `ai` section maintained for backward compatibility
- Support for environment variable API keys with `env:` prefix

### 📦 Dependencies

- Added `python-docx>=0.8.11` for Word document generation
- Added `google-generativeai>=0.3.0` for Gemini support

### 🎨 User Interface

- New mode selection option: "AI Content Generation"
- Interactive model selection interface
- Progress bars for content generation and export
- Connection status display for all configured models
- Comprehensive statistics after content generation

### 📝 Content Generation Features

- Custom word count per heading
- Persian-aware content structure
- SEO title generation (max 60 chars)
- Meta description generation (max 160 chars)
- HTML content with proper tags (H2, H3, p, strong, ul, li, a)
- JSON response parsing with fallback
- Error handling and retry logic

### 🔗 Internal Linking Features

- URL type detection (category, product, blog, other)
- Semantic relevance scoring
- Anchor text extraction from URLs
- Distribution balancing (equal spread across types)
- Section-based link placement (avoid headers)
- Statistics reporting

### 📊 Export Features

- Excel: Combined output with SEO info and content
- Word: Formatted documents with sections
- HTML: Clean output for CMS/editors
- Batch processing with error handling
- Safe filename generation from titles

### 🐛 Bug Fixes

- Fixed pandas import in main.py for content generation
- Improved error messages for missing dependencies
- Better handling of malformed JSON responses from AI

### 📖 Documentation

- Complete README update with Mode 3 documentation
- Persian documentation for new features
- Configuration examples for all supported providers
- Workflow examples for content generation
- Troubleshooting section updates

### 🚀 Performance

- Parallel processing support for content generation
- Efficient sitemap parsing and caching
- Optimized internal link matching algorithms

---

## [2.2.3] - 2024-10-11

### 🔄 Smart Clustering & Fallback Strategy
- **Intelligent Duplicate Detection**: Improved threshold system (default 0.95, adjustable to 0.85)
- **Fallback Clustering**: Multiple retry strategies when all clusters are filtered as duplicates
- **User-Guided Recovery**: Interactive options to adjust clustering parameters
- **Test Mode Support**: Clustering now works properly in test mode with limited data
- **Threshold Adjustment**: Option to lower duplicate detection threshold on demand

### 🐛 Bug Fixes
- Fixed issue where all clusters were being filtered as duplicates
- Fixed empty output folder when clustering fails
- Improved duplicate detection algorithm to be less aggressive
- Added proper fallback when no unique clusters are found

### 🎯 Clustering Improvements
- Better duplicate detection with weighted similarity scoring
- More lenient threshold for title similarity (0.8 weight vs 0.3 for keywords)
- Interactive retry options for failed clustering attempts
- Support for different AI parameters when retrying

### 📊 User Experience
- Clear error messages when clustering fails
- Interactive recovery options instead of silent failures
- Test mode properly limits clustering data
- Better feedback on clustering success/failure

---

## [2.2.0] - 2024-10-11

### 🎯 Persian Language Optimization (Enhanced)
- **Complete Persian AI Prompts**: All AI prompts rewritten specifically for Persian content
- **Persian Search Intent**: Focus on Iranian user behavior and search patterns  
- **Farsi SEO Best Practices**: Optimized for Google's algorithms for Persian content
- **Localized Output**: All suggestions and recommendations in Persian
- **Persian URL Decoding**: Proper handling of Persian URLs in scraping mode
- **Fully Persian Excel Output**: All column headers and content in Persian

### 🔧 Technical Improvements
- **URL Encoding Fix**: Added `_decode_persian_url()` method to properly display Persian URLs
- **Enhanced AI Prompts**: Improved prompts for better Persian content suggestions
- **Excel Localization**: All Excel column headers now in Persian
- **Better Error Handling**: Improved error messages and logging

### 📊 Output Improvements
- **Persian Column Headers**: Excel files now have Persian column names
- **Enhanced Content Suggestions**: More detailed and actionable suggestions
- **Better Keyword Clustering**: Improved clustering for Persian keywords
- **Comprehensive Analysis**: More detailed analysis for existing content

### 🐛 Bug Fixes
- Fixed Persian URL encoding issues in scraping mode
- Improved AI response parsing for Persian content
- Better handling of Persian characters in Excel output
- Enhanced error messages for Persian users

### 📚 Documentation Updates
- Updated README.md for v2.2
- Enhanced Persian documentation sections
- Added troubleshooting for Persian-specific issues
- Updated examples with Persian content

### 🔄 Migration Notes
- No breaking changes from v2.1
- All existing configurations remain compatible
- Enhanced Persian support is automatic
- Excel output format improved but backward compatible

### 📈 Performance
- Faster Persian URL processing
- Improved AI response times for Persian prompts
- Better memory usage for large Persian datasets
- Enhanced caching for Persian content analysis

### 🎯 Use Cases Enhanced
- **Persian E-commerce**: Better product content optimization
- **Persian Blogs**: Improved article suggestions and structure
- **Persian News Sites**: Enhanced content clustering and suggestions
- **Persian Educational Sites**: Better learning content optimization

### 🔒 Privacy & Security
- No changes to data handling
- All Persian content processed locally
- Enhanced logging for Persian content debugging
- Better error reporting for Persian-specific issues

---

## [2.1.0] - 2025-10-11

### 🎉 Persian Language & Knowledge Base Release

Major update focusing on Persian/Farsi content optimization and intelligent project memory.

---

### ✨ New Features

#### Persian Language Optimization 🇮🇷
- **Persian-Aware AI Prompts**
  - Complete rewrite of AI prompts in Persian
  - Deep understanding of Farsi content nuances
  - Recognition of different Persian spellings and variations
  - Analysis of Iranian user search behavior and intent
  
- **Comprehensive Persian SEO Analysis**
  - LSI keywords specific to Persian language
  - H2/H3 headings optimized for Farsi search patterns
  - Meta descriptions with character limits (60 for title, 160 for description)
  - FAQ suggestions based on Persian "People Also Ask"
  - Internal linking with proper Persian anchor texts
  - Schema markup recommendations for Persian content
  
- **Enhanced Content Suggestions**
  - Content type classification (راهنما/آموزش/مقایسه/لیست/تحلیل)
  - Search intent analysis (informational/commercial/transactional)
  - Recommended word count based on Persian content standards
  - Technical SEO suggestions for Farsi pages
  - User experience improvements for Iranian audience

#### Knowledge Base System 🧠
- **Project Memory** (`src/knowledge_base.py` - 450+ lines)
  - Track content generation history per project
  - Store metadata, clusters, and performance metrics
  - Separate directory for each project in `knowledge_base/`
  - JSON-based storage for easy access and portability
  
- **Duplicate Detection**
  - Automatic detection of similar content titles
  - Hash-based exact duplicate matching
  - Similarity scoring (configurable threshold)
  - Prevention of repetitive content suggestions
  
- **Performance Tracking**
  - Store predicted impressions vs actual results
  - Track improvement suggestions and their outcomes
  - Build training data for CTR prediction models
  - Historical analysis for better future predictions
  
- **Smart Analytics**
  - Content generation statistics
  - Keyword usage tracking
  - Performance metrics export
  - Comprehensive JSON reports

#### Interactive Project Management
- **Project Name Input**
  - Interactive prompt for project identification
  - Name validation and confirmation
  - Used as key for knowledge base organization
  
- **Knowledge Base Integration in Workflow**
  - Automatic loading of project history
  - Real-time duplicate checking during generation
  - Seamless saving of all generated content
  - Progress messages for knowledge base operations

---

### 🔧 Improvements

#### AI Processor
- Completely rewritten prompts for Persian content (`src/ai_processor.py`)
- System prompts now in Farsi with cultural context
- Enhanced JSON structure with more fields:
  - `meta_description`
  - `content_type`
  - `search_intent`
  - `recommended_word_count`
  - `lsi_keywords`
  - `internal_linking`
  - `user_experience`
  - `estimated_impact`

#### Main Application
- Added `get_project_name_interactive()` function
- Knowledge base initialization in SEOContentOptimizer class
- Import of KnowledgeBase module
- Updated banner to show v2.1
- Enhanced workflow messages

#### Documentation
- Brand names replaced with generic examples throughout
- README.md updated with v2.1 features (Persian AI + Knowledge Base)
- QUICKSTART.md enhanced with new workflow steps
- CHANGELOG.md (this file) with detailed v2.1 notes
- All examples now use "example" instead of specific brand names

#### Project Structure
- New `knowledge_base/` directory with .gitkeep
- `knowledge_base/README.md` explaining directory purpose
- Updated `.gitignore` to exclude knowledge base data (except structure)
- Better organization of project artifacts

---

### 📁 New Files

#### Core Modules
- `src/knowledge_base.py` (450+ lines)
  - KnowledgeBase class with full functionality
  - Project-specific data management
  - Duplicate detection algorithms
  - Performance tracking methods
  - Export and reporting functions

#### Documentation
- `knowledge_base/README.md`
  - Explains knowledge base directory structure
  - Usage guidelines
  - Data storage format

#### Configuration
- `.gitkeep` files in new directories
- Updated `.gitignore` patterns

---

### 🌍 Localization

#### Persian Content Focus
- All AI prompts now in Persian
- Understanding of Farsi-specific SEO challenges
- Recognition of Iranian search patterns
- Local content recommendations
- Cultural context in suggestions

#### Bilingual Documentation
- README maintains English + Persian sections
- Both sections updated with v2.1 features
- Examples in both languages
- Clear indicators for Persian-optimized features

---

### 🔄 Migration Notes (v2.0 → v2.1)

#### No Breaking Changes
- All v2.0 features remain intact
- New features are additive
- Existing workflows continue to work
- Knowledge base is optional (auto-created)

#### New Workflow Steps
1. Run application as before
2. **NEW**: Enter project name when prompted
3. Continue with file selection (as before)
4. AI now uses Persian-optimized prompts
5. **NEW**: Knowledge base auto-saves everything
6. Review enhanced output with Persian insights

#### First Run
```bash
python3 main.py --mode content

# You'll see:
📋 PROJECT IDENTIFICATION
Enter a name for this project: example.com
✅ Project name: example.com

# Knowledge base auto-created at:
# knowledge_base/example.com/
```

---

### 📊 Statistics

- **New Lines of Code**: ~500 (knowledge_base.py)
- **Updated Modules**: 3 (ai_processor.py, main.py, .gitignore)
- **Documentation Updates**: 4 files (README, QUICKSTART, CHANGELOG, PROJECT_STRUCTURE)
- **New Directories**: 1 (knowledge_base/)
- **Test Coverage**: Manual testing completed

---

### 🎯 Use Cases Enhanced

#### For Persian Content Creators
- Create SEO-optimized Farsi content
- Get culturally relevant suggestions
- Understand Iranian user intent
- Track all content in one place

#### For SEO Professionals
- Manage multiple projects efficiently
- Avoid duplicate content automatically
- Track performance predictions
- Build knowledge over time

#### For Agencies
- Separate knowledge base per client
- Consistent quality across projects
- Historical data for reporting
- Scalable content strategy

---

### 🔐 Privacy & Data

#### Knowledge Base Storage
- All data stored locally
- JSON format for transparency
- Easy to backup and migrate
- No external data transmission

#### Git Safety
- `knowledge_base/` directory in .gitignore
- Only structure files (.gitkeep, README) tracked
- Sensitive project data never committed

---

## [2.0.0] - 2025-10-11

### 🎉 Major Release - Complete Redesign

This version represents a complete overhaul with focus on user experience, interactivity, and new capabilities.

---

### ✨ New Features

#### Dual Operational Modes
- **Content Optimization Mode**: Existing functionality enhanced with better UX
- **SEO Data Collection Mode**: NEW - Scrape page titles, meta tags, and SEO elements from sitemaps

#### Interactive User Interface
- **File Selection**: Visual, interactive selection from `input/` folder
  - Multi-select support (comma-separated numbers)
  - File metadata display (size, date)
  - "Select all" and "finish" commands
  
- **Mode Selection**: Interactive prompt if mode not specified via CLI
  - Clear descriptions of each mode
  - User-friendly selection interface
  
- **Sitemap Management**: Complete redesign
  - Interactive URL input with validation
  - Automatic caching (no re-downloads)
  - 10-retry logic with exponential backoff
  - User prompts for manual retry after failures
  - Sitemap index detection with selective sub-sitemap downloads

#### Test Mode
- Limit processing to 10 items (queries or pages)
- Available in both operational modes
- Perfect for validation before full runs
- Activated via `--test` flag

#### Resume Capability
- SEO scraping can be paused and resumed
- Existing scraped pages are skipped automatically
- No lost work if interrupted (Ctrl+C, crash, etc.)
- Progress saved after each batch

#### Enhanced Progress Tracking
- Real-time progress bars using `tqdm`
- Detailed status messages with emoji indicators
- Section headers for each processing stage
- Statistics summaries at completion
- Clear error messages with suggested fixes

#### Organized Folder Structure
- `input/` - Place Excel files here
- `sitemaps/` - Cached sitemap downloads
- `output/` - Generated Excel reports
- Automatic directory creation
- Prevents file conflicts

#### Page Scraping (New Module)
- Extract title, meta description, H1, canonical URL
- Open Graph tags (og:title, og:description)
- Twitter Card tags (twitter:title, twitter:description)
- Batch processing with configurable sizes
- User-controlled pause/continue
- Error handling with status tracking
- Separate output files per sitemap/domain

---

### 🔧 Improvements

#### Data Loader
- Better column name detection
  - Supports "Top queries" → "Query" mapping
  - Case-insensitive matching
  - Multiple alternative names for each column
- Improved error messages with available columns listed
- More robust Excel parsing

#### Sitemap Manager (New Module)
- Smart caching with MD5 hash filenames
- Domain-based readable filenames
- Retry logic with exponential backoff
- Sitemap index support
- Progress tracking for multiple sitemaps
- User control at every step

#### File Selector (New Module)
- Automatic detection of `.xlsx` and `.xls` files
- Metadata display (size, modification date)
- Sorted by modification time (newest first)
- Multi-select with validation
- Clear user prompts and error handling

#### AI Processor
- Fixed "json" keyword requirement for OpenAI-compatible APIs
- Better error messages
- More robust JSON parsing with fallbacks

#### Terminal Output
- Colored output with ANSI codes (via test_connection.py pattern)
- Consistent emoji usage for status indicators
- Section dividers for clarity
- Step indicators (e.g., [1/7])
- Real-time progress updates

#### Logging
- More descriptive log messages
- Better error context
- Success confirmations
- File paths in logs for traceability

---

### 🏗️ Architecture Changes

#### New Modules
- `src/sitemap_manager.py` - Interactive sitemap downloading and caching
- `src/file_selector.py` - Interactive Excel file selection
- `src/page_scraper.py` - Web page scraping for SEO data

#### Refactored main.py
- Complete rewrite with modular design
- Two clear operational modes
- Enhanced error handling
- Better separation of concerns
- Comprehensive docstrings and comments

#### Configuration Changes
- Removed `sitemap_url` from required config (now interactive)
- `input_excel_path` optional (interactive file selection)
- Added test mode settings
- Better documentation in sample config

---

### 📚 Documentation

#### New Files
- `FEATURES.md` - Comprehensive feature documentation
- `CHANGELOG.md` - This file
- `README_NEW.md` → `README.md` - Completely rewritten

#### Updated Files
- `QUICKSTART.md` - Fully updated for v2.0
- `EXAMPLES.md` - Updated with new workflows
- `config.sample.yaml` - Better comments and examples

#### README Highlights
- Dual-mode documentation
- Step-by-step workflows
- Troubleshooting section expanded
- Use case examples
- Configuration examples for all providers

---

### 🐛 Bug Fixes

- Fixed column name matching for Google Search Console exports
- Fixed API JSON mode requirements for Liara.ir and compatible APIs
- Improved error handling for missing files
- Better validation for user inputs
- Fixed sitemap download timeout handling

---

### 🔄 Breaking Changes

#### Command Line Interface
**Old (v1.x)**:
```bash
python main.py -i search_console_data.xlsx
```

**New (v2.0)**:
```bash
# Interactive (recommended)
python3 main.py

# Or specify mode
python3 main.py --mode content
python3 main.py --mode scraping

# Test mode
python3 main.py --mode content --test
```

#### File Organization
- Excel files must now be in `input/` folder
- Sitemaps cached in `sitemaps/` folder
- Output remains in `output/` folder

#### Configuration
- `sitemap_url` no longer required (interactive input)
- `input_excel_path` no longer required (interactive selection)

---

### 📦 Dependencies

#### Added
- `beautifulsoup4>=4.12.0` - For HTML parsing in page scraper

#### Updated
- All existing dependencies to latest compatible versions

---

### ⚡ Performance

- Sitemap caching reduces redundant downloads
- Resume capability prevents duplicate work
- Batch processing for memory efficiency
- Rate limiting respects API quotas

---

### 🔐 Security

- API keys never logged in plain text
- Config file in `.gitignore`
- Local processing, minimal external calls
- Backup creation before processing

---

### 🎯 Migration Guide (v1.x → v2.0)

#### Step 1: Update Files
```bash
git pull  # or download new version
pip3 install -r requirements.txt
```

#### Step 2: Move Excel Files
```bash
mkdir -p input
mv your_search_console_data.xlsx input/
```

#### Step 3: Update config.yaml
- Remove or comment out `sitemap_url` (now interactive)
- Remove or comment out `input_excel_path` (now interactive)

#### Step 4: Run New Interface
```bash
python3 main.py
```

Follow interactive prompts!

---

### 📊 Statistics

- **Lines of Code**: ~2,500+ (from ~800)
- **New Modules**: 3 (sitemap_manager, file_selector, page_scraper)
- **Documentation Pages**: 5 (README, QUICKSTART, FEATURES, CHANGELOG, EXAMPLES)
- **Test Coverage**: Manual testing completed for all features

---

### 🙏 Acknowledgments

- Built for SEO professionals and content marketers
- Inspired by feedback from v1.x users
- Designed for ease of use and reliability

---

### 📅 Future Roadmap

#### Planned for v2.1
- [ ] Async page scraping for faster performance
- [ ] Export to CSV in addition to Excel
- [ ] Scheduled runs (cron integration)
- [ ] Email notifications on completion

#### Under Consideration
- [ ] Web UI (Flask/Streamlit)
- [ ] Integration with Google Search Console API (direct)
- [ ] Multi-language support in AI prompts
- [ ] Custom AI prompt templates
- [ ] Historical tracking and comparison

---

### 🐛 Known Issues

None currently. Please report issues via GitHub or email.

---

### 📞 Support

- **Documentation**: See README.md, QUICKSTART.md, FEATURES.md
- **Logs**: Check `logs/seo_toolkit.log` for debugging
- **Test**: Use `--test` flag for validation
- **Connection**: Run `test_connection.py` to verify AI setup

---

## [1.0.0] - 2025-10-11 (Earlier Version)

### Initial Release
- Basic Search Console data analysis
- AI-powered content suggestions
- Keyword clustering
- Excel output generation
- Support for multiple AI providers

---

**For detailed feature documentation, see [FEATURES.md](FEATURES.md)**

