# Product Roadmap — Seo Toolkit

Planned phases after v3.0.4. Priorities reflect user requests (2026-06).

## v3.0.5 — Fixes (current)

- [x] Task page back-link routes to correct tool (Content Cluster vs Index Diff)
- [x] Excel calendar sheet includes H1 + H2 headings + meta description
- [x] Persist full calendar JSON after cluster job (prep for board UI)
- [x] Editorial assignee on calendar Kanban cards (v4.4.0)

## v3.1 — Content Calendar Board

**Goal:** View, track, and annotate content on the web panel (not only Excel).

| Feature | Description |
|---------|-------------|
| Calendar page | `/projects/{slug}/calendar` or `/tools/content-cluster/calendar` |
| Kanban / table | Columns: planned → in_progress → review → published |
| Per-post fields | Title, H1, H2 list, keywords, publish date, assignee, notes |
| Status workflow | `planned`, `writing`, `review`, `scheduled`, `published` |
| Notes | Free-text + optional checklist per article |
| Excel sync | Import from cluster job output; export current state anytime |
| Filters | By difficulty, date range, status |

**Storage (phase 1):** JSON/SQLite per project under `projects/{slug}/content_calendar/`

## v3.2 — Light theme

- CSS variables for `[data-theme="light"]`
- Toggle in header (persist in `localStorage`)
- Respect `prefers-color-scheme` as default

## v3.3 — Multi-user auth & project ACL

| Feature | Description |
|---------|-------------|
| Login | Email/password or magic link (start simple) |
| Roles | `admin`, `editor`, `viewer` per project |
| Project access | User ↔ project mapping in DB |
| Audit log | Who changed calendar status / notes |
| API keys | Optional per-user GapGPT keys (encrypted) |

**Tech:** FastAPI + SQLite/PostgreSQL + session cookies or JWT; `users`, `project_members`, `sessions` tables.

## v3.4 — Excel input enhancements

- Optional column mapping UI for SEOSignal exports
- Support pre-filled `suggested_title` / `h2` columns in upload Excel
- Validate required headers before job start

---

## Suggested additions (optional)

1. ~~**Editorial assignee** — even before full auth, a “owner” dropdown on calendar rows~~ (v4.4.0)
2. **WordPress / CMS webhook** — mark `published` when post goes live
3. **Duplicate detection** — warn if cluster title overlaps existing site content
4. **Gap analysis** — compare clusters vs current sitemap URLs
5. **Notifications** — Telegram/email when cluster job completes

## Open questions for you

1. **Calendar UI:** Kanban (ستونی) یا جدول زمانی (تقویم ماهانه)؟
2. **Users:** چند نفر همزمان؟ فقط شما یا تیم ۵–۲۰ نفره؟
3. **Auth:** ورود با ایمیل/رمز کافی است یا Google/GitHub هم لازم است؟
4. **Published status:** دستی تغییر می‌دهید یا از سایت/API بخواند؟
5. **Excel headings:** H2های AI کافی است یا H3 و outline کامل هم می‌خواهید؟

---

See [CONTENT_CLUSTER.md](CONTENT_CLUSTER.md) for current Mode 7 usage.
