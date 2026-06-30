# Multi-Project Support

Seo Toolkit v2.6+ lets you manage **multiple websites** with **isolated data** — ideal when you run SEO for 2–3+ clients or domains.

## Folder Layout

```
projects/
  registry.json          # project list (local, not committed)
  my-shop/
    input/               # Search Console Excel uploads
    output/              # reports, scraped audits, generated files
    knowledge_base/      # content history per project
    index_history/       # URL index diff submission history
    sitemaps/            # cached sitemap data
  blog-site/
    ...
```

Global folders (`input/`, `output/`, etc.) still work when **no project** is selected.

## CLI

Create projects interactively on first run, or pass `--project`:

```bash
# Run content analysis for project "my-shop"
python main.py --mode content --test --project my-shop

# Index diff scoped to project history
python main.py --mode index-diff --project my-shop

# Scraping writes Excel to projects/my-shop/output/
python main.py --mode scraping --project my-shop
```

At startup without `--project`, the CLI prompts you to pick or create a project.

## Web UI

1. Open **Projects** (`/projects`) in the sidebar.
2. Create a project: name, domain, sitemap URL.
3. Use the **header switcher** to set the active project (stored in cookie).
4. Each tool page has a project dropdown; outputs go to that project's folders.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{slug}` | Get one project |
| POST | `/api/v1/projects` | Create (JSON body) |
| POST | `/api/v1/projects/form` | Create (form) |

Tool endpoints accept optional `project_slug` (form field or JSON) to scope file paths.

## Notes

- Project slugs are auto-generated from the display name (e.g. `My Shop` → `my-shop`).
- Deleting a project removes its registry entry and **all** data under `projects/{slug}/`.
- Add `projects/*` to `.gitignore` so client data stays local.
