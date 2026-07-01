# URL Index Diff - Guide

## Problem

You export sitemap URLs to a text file and submit them to an indexing tool. On the next run you cannot tell which URLs were already submitted.

## Solution (Mode 6)

Seo Toolkit stores submitted URLs per domain and diffs each new sitemap fetch.

## CLI Usage

### First-time import (optional)

If you already submitted URLs manually:

```bash
python main.py --mode index-diff \
  --domain example.com \
  --import previous_batch.txt
```

### Regular workflow

```bash
python main.py --mode index-diff --domain example.com
```

Steps:
1. Enter sitemap URL (supports sitemap indexes)
2. Review counts: total / new / already submitted
3. Files written to `output/index_diff/example_com/`:
   - `new_urls_YYYYMMDD_HHMMSS.txt`
   - `already_submitted_YYYYMMDD_HHMMSS.txt`
4. Submit `new_urls_*.txt` to your indexing tool
5. Confirm marking URLs as submitted (updates `index_history/`)

### Non-interactive mark

```bash
python main.py --mode index-diff \
  --domain example.com \
  --mark-submitted
```

## Storage

```
index_history/
  example_com/
    history.json
```

## URL Normalization

- Lowercase hostname
- Strip trailing slash
- Decode percent-encoded paths (Persian URLs)

## Web UI

Open `/tools/index-diff` in the FastAPI dashboard for the same workflow in the browser.

### Background task + progress page (v2.7+)

1. Submit the form — a background job is created
2. You are redirected to `/tasks/{job_id}` with a **progress bar** and step list
3. The browser **recursively** downloads sitemap indexes and all nested sub-sitemaps
4. When finished, download `new_urls_*.txt` and submit to your indexing tool
5. Use **Mark last diff batch** (or upload the same txt) to register URLs as indexed
6. Next run: only new sitemap URLs appear in the diff

### Sitemap snapshots (v2.8+)

Every successful fetch stores:
- `index_history/{project}/sitemap_latest.txt`
- `index_history/{project}/snapshots/sitemap_YYYYMMDD_HHMMSS.txt`

### Import with optional registration

- Checkbox **on**: URLs saved as already indexed
- Checkbox **off**: URLs excluded from diff only (until you mark a batch)

API:
- `POST /api/v1/index-diff/mark-batch` — `use_pending=true` or upload `batch_file`
- `GET /api/v1/index-diff/status/{domain}?project_slug=`

### Import multiple txt files

In the **Import previous URLs** section you can select **several `.txt` files at once** (Ctrl/Cmd+click or Shift+click). Each file should contain one URL per line. Duplicates across files are merged automatically.

API: `POST /api/v1/index-diff/import` with multipart field `urls_files` (repeatable).

Sitemap downloads use browser-like HTTP headers. If a site blocks bots, the API returns a detailed error (403, SSL, timeout).

**Workaround:** Save `sitemap.xml` from your browser and upload it on the Index Diff page.

Optional proxy in `config.yaml`:

```yaml
app:
  http_proxy: "http://127.0.0.1:7890"
  trust_system_proxy: false
```

---

# راهنمای فارسی - تفکیک URL ایندکس

## کاربرد

وقتی خروجی sitemap را به ابزار ایندکس می‌دهید، دفعه بعد فقط URLهای جدید را جدا می‌کند.

## دستور

```bash
python main.py --mode index-diff --domain example.com
```

## خروجی

- `new_urls_*.txt` → بدهید به ابزار ایندکس
- `already_submitted_*.txt` → قبلاً ارسال شده

### صفحه پیشرفت (نسخه ۲.۷+)

بعد از اجرا به `/tasks/{job_id}` می‌روید — نوار پیشرفت و خروجی `new_urls.txt`.

### snapshot و ثبت batch (نسخه ۲.۸+)

- لیست کامل sitemap در `sitemap_latest.txt` + آرشیو dated
- import با چک‌باکس: ثبت دائمی یا فقط حذف از diff
- بعد از ایندکس: **ثبت آخرین batch** یا آپلود همان txt
- پروژه در منوها sticky است (`?project=` + cookie)

## import داده قبلی

```bash
python main.py --mode index-diff --domain example.com --import old_urls.txt
```

### import چند فایل در وب

در صفحه `/tools/index-diff` بخش import را باز کنید و **چند فایل txt همزمان** انتخاب کنید.

