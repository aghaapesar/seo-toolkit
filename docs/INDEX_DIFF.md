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

Open `/index-diff` in the FastAPI dashboard for the same workflow in the browser.

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

## import داده قبلی

```bash
python main.py --mode index-diff --domain example.com --import old_urls.txt
```
