"""Bilingual UI strings for Seo Toolkit web interface."""

from typing import Any, Dict

SUPPORTED_LANGS = ("en", "fa")

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_name": "Seo Toolkit",
        "app_tagline": "Persian-first SEO automation suite",
        "nav_dashboard": "Dashboard",
        "nav_content": "Content Analysis",
        "nav_scraping": "SEO Scraping",
        "nav_generation": "Content Generation",
        "nav_linking": "Internal Linking",
        "nav_synonyms": "Synonym Finder",
        "nav_index_diff": "Index Diff",
        "nav_settings": "Settings",
        "nav_projects": "Projects",
        "nav_api": "API Docs",
        "lang_en": "English",
        "lang_fa": "فارسی",
        "hero_title": "Grow organic traffic with data-driven SEO",
        "hero_sub": "Analyze Search Console, scrape metadata, generate Persian content, and track indexing URLs — all in one toolkit.",
        "run_tool": "Open tool",
        "submit": "Run",
        "test_mode": "Test mode (10 items)",
        "domain": "Domain / project name",
        "sitemap_url": "Sitemap URL",
        "project_name": "Project name",
        "upload_excel": "Upload Excel file",
        "upload_html": "Upload HTML file",
        "mark_submitted": "Mark new URLs as submitted",
        "import_urls": "Import previous URLs (txt files)",
        "import_txt_label": "Upload txt files (multiple allowed)",
        "import_txt_hint": "Select one or more .txt files — one URL per line.",
        "import_submit": "Import",
        "import_files_selected": "file(s) selected",
        "import_no_files": "Select at least one .txt file",
        "import_total_added": "Total new URLs",
        "import_files_processed": "Files processed",
        "processing": "Processing…",
        "success": "Completed successfully",
        "error": "Something went wrong",
        "download": "Download result",
        "total": "Total",
        "new_urls": "New URLs",
        "already": "Already submitted",
        "back": "Back to dashboard",
        "content_desc": "Analyze Google Search Console exports and get AI improvement ideas plus new article clusters.",
        "scraping_desc": "Download your sitemap and audit titles, meta descriptions, and H1 tags for every page.",
        "generation_desc": "Turn content outlines from Excel into full Persian SEO articles with export to Word/HTML.",
        "linking_desc": "Add smart internal links to existing HTML content using your sitemap structure.",
        "synonyms_desc": "Discover Persian, Finglish, typo, and English variations for your target keywords.",
        "index_diff_desc": "Separate new sitemap URLs from ones you already sent to your indexing tool.",
        "settings_desc": "Configuration status and CLI reference.",
        "config_ok": "config.yaml found",
        "config_missing": "config.yaml missing — copy config.sample.yaml",
        "version": "Version",
        "features": "All tools",
        "result_files": "Output files",
        "cli_hint": "Advanced workflows also available via CLI:",
        "projects_title": "Projects",
        "projects_sub": "Manage separate sites with isolated data folders.",
        "create_project": "Create project",
        "project_name_label": "Project name",
        "select_project": "Active project",
        "no_project": "— No project —",
        "project_created": "Project created",
        "project_data_path": "Data folder",
    },
    "fa": {
        "app_name": "Seo Toolkit",
        "app_tagline": "سوئیت خودکارسازی سئو با تمرکز فارسی",
        "nav_dashboard": "داشبورد",
        "nav_content": "تحلیل محتوا",
        "nav_scraping": "اسکرپ سئو",
        "nav_generation": "تولید محتوا",
        "nav_linking": "لینک‌سازی داخلی",
        "nav_synonyms": "مترادف‌یاب",
        "nav_index_diff": "تفکیک ایندکس",
        "nav_settings": "تنظیمات",
        "nav_projects": "پروژه‌ها",
        "nav_api": "مستندات API",
        "lang_en": "English",
        "lang_fa": "فارسی",
        "hero_title": "ترافیک ارگانیک را با سئوی داده‌محور رشد دهید",
        "hero_sub": "Search Console را تحلیل کنید، متادیتا بکشید، محتوای فارسی بسازید و URLهای ایندکس را ردیابی کنید — همه در یک ابزار.",
        "run_tool": "باز کردن ابزار",
        "submit": "اجرا",
        "test_mode": "حالت تست (۱۰ مورد)",
        "domain": "دامنه / نام پروژه",
        "sitemap_url": "آدرس sitemap",
        "project_name": "نام پروژه",
        "upload_excel": "آپلود فایل Excel",
        "upload_html": "آپلود فایل HTML",
        "mark_submitted": "URLهای جدید را به‌عنوان ارسال‌شده ثبت کن",
        "import_urls": "import URLهای قبلی (فایل txt)",
        "import_txt_label": "آپلود فایل txt (چند فایل همزمان)",
        "import_txt_hint": "یک یا چند فایل .txt انتخاب کنید — هر خط یک URL.",
        "import_submit": "Import",
        "import_files_selected": "فایل انتخاب شده",
        "import_no_files": "حداقل یک فایل txt انتخاب کنید",
        "import_total_added": "مجموع URL جدید",
        "import_files_processed": "فایل پردازش‌شده",
        "processing": "در حال پردازش…",
        "success": "با موفقیت انجام شد",
        "error": "خطایی رخ داد",
        "download": "دانلود نتیجه",
        "total": "مجموع",
        "new_urls": "URL جدید",
        "already": "قبلاً ارسال شده",
        "back": "بازگشت به داشبورد",
        "content_desc": "خروجی Search Console را تحلیل کنید و پیشنهاد بهبود + ایده مقاله جدید بگیرید.",
        "scraping_desc": "sitemap را بگیرید و title، meta و H1 همه صفحات را ممیزی کنید.",
        "generation_desc": "طرح محتوای Excel را به مقاله سئو فارسی کامل با خروجی Word/HTML تبدیل کنید.",
        "linking_desc": "لینک داخلی هوشمند به HTML موجود با استفاده از sitemap اضافه کنید.",
        "synonyms_desc": "انواع فارسی، فینگلیش، غلط املایی و انگلیسی کلیدواژه‌ها را پیدا کنید.",
        "index_diff_desc": "URLهای جدید sitemap را از URLهای قبلاً داده‌شده به ابزار ایندکس جدا کنید.",
        "settings_desc": "وضعیت پیکربندی و راهنمای CLI.",
        "config_ok": "config.yaml موجود است",
        "config_missing": "config.yaml نیست — config.sample.yaml را کپی کنید",
        "version": "نسخه",
        "features": "همه ابزارها",
        "result_files": "فایل‌های خروجی",
        "cli_hint": "جریان‌های پیشرفته از CLI هم در دسترس است:",
        "projects_title": "پروژه‌ها",
        "projects_sub": "چند سایت را با داده جدا مدیریت کنید.",
        "create_project": "ساخت پروژه",
        "project_name_label": "نام پروژه",
        "select_project": "پروژه فعال",
        "no_project": "— بدون پروژه —",
        "project_created": "پروژه ساخته شد",
        "project_data_path": "پوشه داده",
    },
}

TOOLS = [
    {
        "id": "content",
        "icon": "chart",
        "route": "/tools/content",
        "mode": "content",
        "title_en": "Content Analysis",
        "title_fa": "تحلیل محتوا",
        "desc_key": "content_desc",
        "gradient": "g-emerald",
    },
    {
        "id": "scraping",
        "icon": "search",
        "route": "/tools/scraping",
        "mode": "scraping",
        "title_en": "SEO Scraping",
        "title_fa": "اسکرپ سئو",
        "desc_key": "scraping_desc",
        "gradient": "g-blue",
    },
    {
        "id": "generation",
        "icon": "pen",
        "route": "/tools/generation",
        "mode": "generation",
        "title_en": "Content Generation",
        "title_fa": "تولید محتوا",
        "desc_key": "generation_desc",
        "gradient": "g-violet",
    },
    {
        "id": "linking",
        "icon": "link",
        "route": "/tools/linking",
        "mode": "linking",
        "title_en": "Internal Linking",
        "title_fa": "لینک‌سازی داخلی",
        "desc_key": "linking_desc",
        "gradient": "g-amber",
    },
    {
        "id": "synonyms",
        "icon": "tags",
        "route": "/tools/synonyms",
        "mode": "synonyms",
        "title_en": "Synonym Finder",
        "title_fa": "مترادف‌یاب",
        "desc_key": "synonyms_desc",
        "gradient": "g-rose",
    },
    {
        "id": "index-diff",
        "icon": "diff",
        "route": "/tools/index-diff",
        "mode": "index-diff",
        "title_en": "URL Index Diff",
        "title_fa": "تفکیک ایندکس",
        "desc_key": "index_diff_desc",
        "gradient": "g-cyan",
    },
]


def get_lang(request) -> str:
    """Resolve language from query param or cookie."""
    lang = request.query_params.get("lang") or request.cookies.get("lang", "fa")
    return lang if lang in SUPPORTED_LANGS else "fa"


def t(lang: str, key: str) -> str:
    """Translate a key for the given language."""
    return STRINGS.get(lang, STRINGS["en"]).get(key, key)


def page_context(request, page_title: str, **extra: Any) -> Dict[str, Any]:
    """Build standard template context."""
    from src import __version__
    from src.services.project_manager import ProjectManager

    lang = get_lang(request)
    manager = ProjectManager()
    projects = manager.list_projects()
    active_slug = request.query_params.get("project") or request.cookies.get("active_project")
    active_project = manager.get_project(active_slug) if active_slug else None

    return {
        "lang": lang,
        "dir": "rtl" if lang == "fa" else "ltr",
        "page_title": page_title,
        "strings": STRINGS[lang],
        "tools": TOOLS,
        "version": __version__,
        "config_exists": Path_exists_config(),
        "tool_id": extra.pop("tool_id", None),
        "projects": projects,
        "active_project": active_project,
        "active_project_slug": active_slug or "",
        **extra,
    }


def Path_exists_config() -> bool:
    """Check if config.yaml exists in project root."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    return (root / "config.yaml").exists()
