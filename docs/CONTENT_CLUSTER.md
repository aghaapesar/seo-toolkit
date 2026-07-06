# Content Cluster & Calendar

Mode 7 — cluster SEOSignal keyword exports into content topics and a publish calendar.

## Input

Excel export from SEOSignal with columns:

| Column | Description |
|--------|-------------|
| کلمه کلیدی | Target keyword |
| سرچ ولوم | Monthly search volume (integer) |
| رقابت | معمولی / سخت / خیلی سخت |
| درصد رقابت | Optional 1–100 |
| تعداد کلمات | Word count |

## Methods

| Method | Description |
|--------|-------------|
| `rule` | Fast token/n-gram grouping — no API cost |
| `ml` | Persian char TF-IDF + DBSCAN |
| `ai` | Full LLM clustering (GapGPT / OpenAI / etc.) |
| `hybrid` | Rule + ML pre-cluster, then AI refines top clusters (recommended) |

## CLI

```bash
python main.py --mode content-cluster \
  --excel input/keywords.xlsx \
  --cluster-method hybrid \
  --model gapgpt_gpt4o_mini \
  --posts-per-day 1 \
  --start-date 2026-07-05
```

## Web UI

1. **Settings** → add GapGPT API key (`https://api.gapgpt.app/v1`)
2. **Content Cluster** → upload Excel, choose hybrid, select model
3. **Calendar start** — Jalali date picker (year / month / day)
4. **Campaign** — assign to existing project campaign or auto-create `کمپین N`
5. **H2 limits** — min/max headings (0 = unlimited / no minimum) for AI refine
6. **Content calendar** → Kanban board with per-project campaign tabs; assign each card to a team member (v4.4.0)
7. Poll `/tasks/{job_id}` → download `content_calendar_*.xlsx`

## GapGPT setup

In Settings or `config.yaml`:

```yaml
ai_models:
  default: gapgpt_gpt4o_mini
  gapgpt_gpt4o_mini:
    provider: gapgpt
    api_key: YOUR_GAPGPT_API_KEY
    base_url: https://api.gapgpt.app/v1
    model: gpt-4o-mini
    temperature: 0.3
```

CDN alternative: `https://api.gapapi.com/v1`

## VPN and network (important)

GapGPT is an **Iranian** API. On many networks:

| VPN state | Cursor IDE | GapGPT API |
|-----------|------------|------------|
| International VPN **on** | Works | Often **blocked** (DNS / routing) |
| VPN **off** (Iran) | May need proxy | Usually **works** |

**Recommended test flow:**

1. **Disconnect** international VPN
2. Start the web server from **Terminal.app** (not Cursor's terminal):
   ```bash
   cd ~/Projects/seo-toolkit
   ./scripts/run_web.sh
   ```
3. Open `http://127.0.0.1:8000/settings` — check **GapGPT network status** panel
4. Click **Test** on your model (`gap-gpt-gift` or `gpt-4o-mini`)

If model test returns HTTP 404, try model `gpt-4o-mini` instead of custom names like `gpt-5.3-chat-latest`.

`run_web.sh` clears IDE-injected `HTTP_PROXY` variables. OpenAI SDK uses `trust_env=False` so Cursor's proxy does not block GapGPT when VPN is off.

Only set `app.http_proxy` in `config.yaml` when you **need** a local VPN proxy for other sites — leave it empty for GapGPT with VPN off.

## Output

Excel with two sheets:

- **content_calendar** — publish_date, title, keywords, difficulty, priority
- **clusters** — full cluster metadata + H2 headings

Calendar defaults to **1 post/day**, sorted easy → hard. Increase `posts_per_day` for denser schedules.
