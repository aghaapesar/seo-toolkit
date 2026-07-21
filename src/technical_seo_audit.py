"""
Technical SEO auditor — site-level and page-level checks with prioritization.

Input:
    Site URL (and optional sitemap URL) + sample size.

Output:
    Structured audit result: issues by severity, health score,
    prioritized task list for the dev/content team.
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.services.http_client import DEFAULT_REQUEST_HEADERS, build_http_session

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ("critical", "high", "medium", "low")

SEVERITY_LABELS_FA = {
    "critical": "بحرانی",
    "high": "زیاد",
    "medium": "متوسط",
    "low": "کم",
}

# Issue catalog: id → (severity, category, title_fa, description_fa, recommendation_fa, owner_fa, effort_fa)
ISSUE_CATALOG: Dict[str, Dict[str, str]] = {
    "site_https_redirect": {
        "severity": "critical",
        "category": "زیرساخت",
        "title": "ریدایرکت HTTP به HTTPS برقرار نیست",
        "description": "نسخه HTTP سایت به HTTPS منتقل نمی‌شود؛ محتوای تکراری و افت اعتماد ایجاد می‌کند.",
        "recommendation": "ریدایرکت 301 سراسری از http:// به https:// در وب‌سرور (nginx/Apache) یا CDN تنظیم شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "site_www_canonical": {
        "severity": "high",
        "category": "زیرساخت",
        "title": "نسخه www و بدون www یکسان‌سازی نشده",
        "description": "هر دو نسخه www و بدون www پاسخ 200 می‌دهند؛ اعتبار لینک بین دو نسخه تقسیم می‌شود.",
        "recommendation": "یک نسخه را انتخاب و نسخه دیگر را با ریدایرکت 301 به آن منتقل کنید.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "site_robots_txt": {
        "severity": "high",
        "category": "خزش",
        "title": "فایل robots.txt در دسترس نیست",
        "description": "بدون robots.txt کنترل خزش موتورهای جستجو ممکن نیست و بودجه خزش هدر می‌رود.",
        "recommendation": "فایل robots.txt با قوانین مناسب و آدرس sitemap ایجاد شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "site_sitemap": {
        "severity": "high",
        "category": "خزش",
        "title": "نقشه سایت (sitemap.xml) در دسترس نیست",
        "description": "بدون sitemap کشف صفحات جدید توسط گوگل کند می‌شود.",
        "recommendation": "sitemap.xml معتبر تولید و در robots.txt و Search Console ثبت شود.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "site_404_handling": {
        "severity": "medium",
        "category": "خزش",
        "title": "صفحه ناموجود کد 404 برنمی‌گرداند",
        "description": "آدرس‌های ناموجود باید 404 بدهند؛ در غیر این صورت صفحات بی‌ارزش ایندکس می‌شوند (Soft 404).",
        "recommendation": "پاسخ 404 واقعی همراه صفحه خطای کاربرپسند پیاده‌سازی شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "site_favicon": {
        "severity": "low",
        "category": "برندینگ",
        "title": "favicon یافت نشد",
        "description": "favicon در نتایج جستجو و تب مرورگر نمایش داده می‌شود و به برند اعتبار می‌دهد.",
        "recommendation": "فایل favicon.ico (و آیکون‌های PWA) اضافه شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "page_broken": {
        "severity": "critical",
        "category": "خزش",
        "title": "صفحات خراب (4xx/5xx) در سایت",
        "description": "این صفحات برای کاربر و ربات گوگل غیرقابل دسترس هستند و اعتبار سایت را کاهش می‌دهند.",
        "recommendation": "صفحات خراب اصلاح، ریدایرکت 301 یا از لینک‌های داخلی حذف شوند.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "page_redirect_chain": {
        "severity": "medium",
        "category": "خزش",
        "title": "زنجیره ریدایرکت طولانی",
        "description": "ریدایرکت‌های چندمرحله‌ای بودجه خزش را هدر می‌دهند و سرعت را کم می‌کنند.",
        "recommendation": "لینک‌ها مستقیماً به مقصد نهایی اصلاح شوند (حداکثر یک ریدایرکت).",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "title_missing": {
        "severity": "critical",
        "category": "متا",
        "title": "تگ Title ندارد",
        "description": "Title مهم‌ترین عامل آن‌پیج است؛ بدون آن صفحه در نتایج درست نمایش داده نمی‌شود.",
        "recommendation": "برای هر صفحه Title یکتا با کیورد اصلی (۳۰ تا ۶۰ کاراکتر) بنویسید.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
    "title_duplicate": {
        "severity": "high",
        "category": "متا",
        "title": "Title تکراری بین صفحات",
        "description": "Title تکراری باعث سردرگمی گوگل در انتخاب صفحه مناسب برای رتبه می‌شود.",
        "recommendation": "برای هر صفحه Title یکتا بر اساس محتوای همان صفحه بنویسید.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
    "title_length": {
        "severity": "medium",
        "category": "متا",
        "title": "طول Title نامناسب (خیلی کوتاه/بلند)",
        "description": "Title خارج از بازه ۳۰ تا ۶۰ کاراکتر در نتایج بریده یا کم‌اثر می‌شود.",
        "recommendation": "Title صفحات به بازه ۳۰ تا ۶۰ کاراکتر اصلاح شود.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
    "meta_desc_missing": {
        "severity": "high",
        "category": "متا",
        "title": "Meta Description ندارد",
        "description": "بدون توضیحات متا، گوگل متن دلخواه نمایش می‌دهد و CTR کاهش می‌یابد.",
        "recommendation": "برای صفحات مهم توضیحات ۷۰ تا ۱۶۰ کاراکتری جذاب بنویسید.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
    "meta_desc_duplicate": {
        "severity": "medium",
        "category": "متا",
        "title": "Meta Description تکراری",
        "description": "توضیحات تکراری ارزش متمایزکننده صفحات را از بین می‌برد.",
        "recommendation": "برای هر صفحه توضیح یکتا متناسب با محتوا بنویسید.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
    "h1_missing": {
        "severity": "high",
        "category": "ساختار",
        "title": "تگ H1 ندارد",
        "description": "H1 موضوع اصلی صفحه را به گوگل و کاربر اعلام می‌کند.",
        "recommendation": "هر صفحه دقیقاً یک H1 حاوی کیورد اصلی داشته باشد.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "h1_multiple": {
        "severity": "medium",
        "category": "ساختار",
        "title": "بیش از یک H1 در صفحه",
        "description": "چند H1 تمرکز موضوعی صفحه را ضعیف می‌کند.",
        "recommendation": "فقط یک H1 نگه دارید؛ بقیه به H2/H3 تبدیل شوند.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "canonical_missing": {
        "severity": "medium",
        "category": "ایندکس",
        "title": "تگ Canonical ندارد",
        "description": "بدون canonical در صفحات با پارامتر/فیلتر، خطر محتوای تکراری وجود دارد.",
        "recommendation": "به تمام صفحات تگ canonical self-referencing اضافه شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "noindex_pages": {
        "severity": "high",
        "category": "ایندکس",
        "title": "صفحات دارای noindex",
        "description": "این صفحات از ایندکس گوگل خارج می‌شوند؛ اگر ناخواسته است باید اصلاح شود.",
        "recommendation": "لیست بررسی شود؛ صفحات ارزشمند از noindex خارج شوند.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "img_alt_missing": {
        "severity": "medium",
        "category": "محتوا",
        "title": "تصاویر بدون alt",
        "description": "alt برای سئوی تصاویر و دسترس‌پذیری ضروری است.",
        "recommendation": "برای تصاویر معنادار alt توصیفی حاوی کیورد بنویسید.",
        "owner": "تیم محتوا",
        "effort": "زیاد",
    },
    "viewport_missing": {
        "severity": "high",
        "category": "موبایل",
        "title": "متای viewport ندارد",
        "description": "بدون viewport صفحه در موبایل درست نمایش داده نمی‌شود؛ ایندکس Mobile-First آسیب می‌بیند.",
        "recommendation": "متای viewport استاندارد به head همه قالب‌ها اضافه شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "lang_missing": {
        "severity": "medium",
        "category": "بین‌الملل",
        "title": "ویژگی lang در html تعیین نشده",
        "description": "بدون lang، موتور جستجو زبان صفحه را حدس می‌زند.",
        "recommendation": "به تگ html مقدار lang=\"fa\" (یا زبان مناسب) اضافه شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "schema_missing": {
        "severity": "medium",
        "category": "داده ساختاریافته",
        "title": "داده ساختاریافته (JSON-LD) ندارد",
        "description": "بدون Schema، ریچ‌اسنیپت (ستاره، قیمت، FAQ و…) نمایش داده نمی‌شود.",
        "recommendation": "Schema مناسب نوع صفحه (Product، Article، Organization و…) پیاده شود.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "og_missing": {
        "severity": "low",
        "category": "شبکه اجتماعی",
        "title": "تگ‌های Open Graph ناقص",
        "description": "بدون OG، پیش‌نمایش اشتراک‌گذاری در شبکه‌های اجتماعی ضعیف است.",
        "recommendation": "og:title، og:description و og:image به صفحات اضافه شود.",
        "owner": "تیم فنی",
        "effort": "کم",
    },
    "mixed_content": {
        "severity": "high",
        "category": "امنیت",
        "title": "Mixed Content (منابع http در صفحه https)",
        "description": "بارگذاری منابع ناامن باعث هشدار مرورگر و افت اعتماد می‌شود.",
        "recommendation": "تمام منابع (تصویر، اسکریپت، CSS) به https منتقل شوند.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "slow_pages": {
        "severity": "high",
        "category": "سرعت",
        "title": "پاسخ کند سرور (بیش از ۳ ثانیه)",
        "description": "سرعت از عوامل رتبه‌بندی است و روی نرخ پرش اثر مستقیم دارد.",
        "recommendation": "کش سرور، بهینه‌سازی دیتابیس و CDN بررسی شود؛ هدف TTFB زیر ۰٫۸ ثانیه.",
        "owner": "تیم فنی",
        "effort": "زیاد",
    },
    "large_pages": {
        "severity": "medium",
        "category": "سرعت",
        "title": "حجم HTML بالای ۲ مگابایت",
        "description": "HTML سنگین زمان رندر و خزش را افزایش می‌دهد.",
        "recommendation": "HTML اضافی، اسکریپت inline و CSS بلااستفاده حذف شود.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "url_issues": {
        "severity": "low",
        "category": "ساختار URL",
        "title": "ساختار URL نامناسب",
        "description": "URL با حروف بزرگ، خیلی طولانی یا پر از پارامتر برای کاربر و گوگل ناخواناست.",
        "recommendation": "URLهای کوتاه، با حروف کوچک و خط تیره استفاده شود؛ نسخه‌های قدیمی ریدایرکت شوند.",
        "owner": "تیم فنی",
        "effort": "متوسط",
    },
    "broken_internal_links": {
        "severity": "critical",
        "category": "لینک داخلی",
        "title": "لینک داخلی شکسته",
        "description": "لینک به صفحات 404 تجربه کاربر را خراب و اعتبار صفحه را هدر می‌دهد.",
        "recommendation": "لینک‌های شکسته اصلاح یا حذف شوند.",
        "owner": "تیم محتوا",
        "effort": "متوسط",
    },
}

SEVERITY_WEIGHTS = {"critical": 15.0, "high": 8.0, "medium": 4.0, "low": 1.5}

# Hard safety cap for "crawl everything" mode.
ABSOLUTE_PAGE_CAP = 5000

# Detected platform keys → Persian display names.
STACK_LABELS_FA = {
    "wordpress": "وردپرس",
    "woocommerce": "ووکامرس",
    "shopify": "شاپیفای",
    "magento": "مجنتو",
    "joomla": "جوملا",
    "drupal": "دروپال",
    "nextjs": "Next.js",
    "nuxt": "Nuxt",
    "laravel": "لاراول",
    "django": "جنگو (Django)",
    "aspnet": "ASP.NET",
}

# Stack-specific solutions per issue (Persian) — shown next to the generic راهکار.
STACK_SOLUTIONS: Dict[str, Dict[str, str]] = {
    "site_https_redirect": {
        "wordpress": "افزونه Really Simple SSL را فعال کنید یا قانون ریدایرکت 301 را در فایل ‎.htaccess اضافه کنید.",
        "laravel": "در AppServiceProvider متد URL::forceScheme('https') را فعال و ریدایرکت را در middleware یا وب‌سرور تنظیم کنید.",
        "django": "SECURE_SSL_REDIRECT = True را در settings.py فعال کنید.",
        "nextjs": "ریدایرکت را در next.config.js (بخش redirects) یا در سطح Vercel/وب‌سرور تعریف کنید.",
    },
    "site_www_canonical": {
        "wordpress": "آدرس سایت را در تنظیمات عمومی وردپرس (siteurl/home) یکسان کنید و ریدایرکت 301 در ‎.htaccess بگذارید.",
        "laravel": "ریدایرکت www را در nginx/htaccess یا یک middleware سراسری اعمال کنید.",
        "nextjs": "در next.config.js با has/host شرط بگذارید یا در DNS/CDN (مثل Cloudflare) ریدایرکت تعریف کنید.",
    },
    "site_robots_txt": {
        "wordpress": "از Rank Math یا Yoast (بخش ابزارها ← ویرایش فایل) robots.txt بسازید.",
        "shopify": "قالب robots.txt.liquid را در تم ویرایش کنید (Online Store ← Themes ← Edit code).",
        "nextjs": "فایل app/robots.ts (App Router) یا public/robots.txt اضافه کنید.",
        "django": "یک view ساده یا پکیج django-robots اضافه کنید.",
        "laravel": "فایل public/robots.txt را ایجاد کنید.",
    },
    "site_sitemap": {
        "wordpress": "sitemap خودکار Rank Math / Yoast را فعال و در Search Console ثبت کنید.",
        "shopify": "شاپیفای sitemap.xml خودکار دارد — فقط در robots.txt و Search Console معرفی کنید.",
        "nextjs": "پکیج next-sitemap یا فایل app/sitemap.ts را اضافه کنید.",
        "laravel": "پکیج spatie/laravel-sitemap را نصب و یک command زمان‌بندی‌شده بسازید.",
        "django": "framework داخلی django.contrib.sitemaps را فعال کنید.",
    },
    "title_missing": {
        "wordpress": "در Rank Math / Yoast قالب عنوان (Title Template) را برای همه نوع‌های محتوا تنظیم کنید.",
        "shopify": "در تنظیمات هر محصول/صفحه بخش Search engine listing را کامل کنید.",
        "nextjs": "از Metadata API (فایل layout/page) یا next/head برای عنوان یکتای هر صفحه استفاده کنید.",
        "laravel": "در layout اصلی Blade متغیر عنوان صفحه را الزامی کنید (یا پکیج artesaos/seotools).",
        "django": "بلاک {% block title %} را در تمپلیت پایه الزامی کنید.",
    },
    "title_duplicate": {
        "wordpress": "قالب عنوان Rank Math / Yoast را بر اساس نام نوشته/محصول داینامیک کنید تا تکرار نشود.",
        "woocommerce": "برای محصولات، متغیرهای %title% و %category% را در قالب عنوان ترکیب کنید.",
        "nextjs": "عنوان را از دادهٔ صفحه (generateMetadata) بسازید، نه مقدار ثابت در layout.",
        "laravel": "عنوان را از مدل (نام محصول/مقاله) در کنترلر پاس بدهید.",
    },
    "title_length": {
        "wordpress": "در ویرایشگر Rank Math / Yoast پیش‌نمایش اسنیپت را ببینید و عنوان را در بازه ۳۰–۶۰ کاراکتر نگه دارید.",
    },
    "meta_desc_missing": {
        "wordpress": "قالب توضیحات متا را در Rank Math / Yoast تنظیم کنید و برای صفحات مهم دستی بنویسید.",
        "shopify": "بخش Search engine listing هر محصول/کالکشن را کامل کنید.",
        "nextjs": "description را در generateMetadata هر صفحه مقداردهی کنید.",
        "laravel": "متا دیسکریپشن را از فیلد excerpt/summary مدل در Blade رندر کنید.",
        "django": "بلاک meta description را در تمپلیت پایه تعریف و در صفحات پر کنید.",
    },
    "meta_desc_duplicate": {
        "wordpress": "توضیحات پیش‌فرض (Template) را داینامیک کنید — از %excerpt% یا فیلد محصول استفاده کنید.",
    },
    "h1_missing": {
        "wordpress": "در قالب (تم) مطمئن شوید the_title() داخل تگ h1 رندر می‌شود؛ در صفحه‌ساز (المنتور) ویجت Heading را H1 کنید.",
        "shopify": "در تم، product.title و collection.title باید داخل h1 باشند.",
        "nextjs": "کامپوننت صفحه باید یک h1 یکتا (معمولاً عنوان محتوا) رندر کند.",
    },
    "h1_multiple": {
        "wordpress": "در تم/المنتور فقط عنوان اصلی H1 بماند؛ لوگو و عنوان‌های بخش‌ها به div یا H2 تبدیل شوند.",
    },
    "canonical_missing": {
        "wordpress": "Rank Math / Yoast تگ canonical خودکار می‌سازد — بررسی کنید غیرفعال نشده باشد.",
        "shopify": "تم‌های استاندارد canonical_url دارند؛ در theme.liquid تگ canonical را بررسی کنید.",
        "nextjs": "alternates.canonical را در generateMetadata تنظیم کنید.",
        "laravel": "تگ canonical را در layout از url()->current() (بدون کوئری) بسازید.",
    },
    "noindex_pages": {
        "wordpress": "تنظیمات «خوانایی» وردپرس (Discourage search engines) و تب‌های Rank Math / Yoast هر برگه را بررسی کنید.",
    },
    "img_alt_missing": {
        "wordpress": "متن جایگزین را در کتابخانه رسانه وارد کنید؛ برای حجم زیاد از افزونه‌هایی مثل Image SEO استفاده کنید.",
        "woocommerce": "برای تصاویر محصول، alt را از نام محصول پر کنید (قابل اتومات با افزونه).",
        "nextjs": "پراپ alt در کامپوننت next/image را الزامی کنید (ESLint rule jsx-a11y/alt-text).",
    },
    "viewport_missing": {
        "wordpress": "متای viewport باید در header.php تم باشد؛ تم‌های استاندارد دارند — تم را بررسی کنید.",
        "nextjs": "در App Router به‌صورت خودکار اضافه می‌شود؛ اگر حذف شده، viewport export را برگردانید.",
    },
    "lang_missing": {
        "wordpress": "تابع language_attributes() باید در تگ html فایل header.php باشد.",
        "nextjs": "در layout ریشه <html lang=\"fa\"> را تنظیم کنید.",
        "laravel": "در layout اصلی Blade مقدار lang را از config('app.locale') بگذارید.",
    },
    "schema_missing": {
        "wordpress": "Schema داخلی Rank Math (یا افزونه Schema Pro) را برای نوع‌های محتوا فعال کنید.",
        "woocommerce": "ووکامرس Schema محصول (قیمت/موجودی) دارد — با Rich Results Test اعتبارسنجی کنید.",
        "shopify": "اکثر تم‌ها JSON-LD محصول دارند؛ در غیر این صورت snippet اضافه کنید یا اپ SEO نصب کنید.",
        "nextjs": "اسکریپت JSON-LD را در کامپوننت صفحه رندر کنید (dangerouslySetInnerHTML یا metadata).",
        "laravel": "پکیج spatie/schema-org برای تولید JSON-LD استفاده کنید.",
    },
    "og_missing": {
        "wordpress": "تب Social افزونه Rank Math / Yoast را فعال و تصویر پیش‌فرض OG تنظیم کنید.",
        "nextjs": "openGraph را در generateMetadata هر صفحه مقداردهی کنید.",
        "shopify": "تنظیمات Social sharing image در بخش Preferences فروشگاه.",
    },
    "mixed_content": {
        "wordpress": "با افزونه Better Search Replace همه http:// دیتابیس را به https:// تبدیل کنید.",
        "laravel": "مقدار ASSET_URL و آدرس‌های hard-code شده در Blade را به https اصلاح کنید.",
    },
    "slow_pages": {
        "wordpress": "افزونه کش (WP Rocket / LiteSpeed Cache) + بهینه‌سازی تصویر WebP + CDN؛ افزونه‌های سنگین را حذف کنید.",
        "woocommerce": "کش object (Redis) برای سبد خرید و کوئری‌های محصول؛ تعداد variation ها را بهینه کنید.",
        "nextjs": "صفحات را به SSG/ISR ببرید، از next/image و کش CDN استفاده کنید.",
        "laravel": "route:cache و config:cache، کش Redis برای کوئری‌ها، و CDN برای asset ها.",
        "django": "cache framework (Redis/Memcached) و select_related/prefetch_related در کوئری‌ها.",
        "shopify": "اپ‌های استفاده‌نشده را حذف و اسکریپت‌های تم را lazy کنید.",
    },
    "large_pages": {
        "wordpress": "صفحه‌سازها CSS/JS اضافه تولید می‌کنند — از افزونه Asset CleanUp یا Perfmatters استفاده کنید.",
        "nextjs": "باندل را با next build --profile آنالیز و کامپوننت‌های سنگین را dynamic import کنید.",
    },
    "url_issues": {
        "wordpress": "ساختار پیوند یکتا (Permalink) را روی «نام نوشته» بگذارید و از پارامترهای اضافه پرهیز کنید.",
    },
    "broken_internal_links": {
        "wordpress": "افزونه Broken Link Checker را اجرا و لینک‌ها را اصلاح کنید؛ ریدایرکت‌ها را با Rank Math Redirection بسازید.",
        "laravel": "برای مسیرهای حذف‌شده ریدایرکت 301 در routes یا جدول ریدایرکت تعریف کنید.",
    },
    "page_broken": {
        "wordpress": "برگه‌های حذف‌شده را با افزونه Redirection به صفحات مرتبط 301 کنید.",
        "shopify": "در بخش Navigation ← URL Redirects ریدایرکت بسازید.",
    },
    "page_redirect_chain": {
        "wordpress": "در افزونه Redirection زنجیره‌ها را ادغام کنید (مبدأ مستقیم به مقصد نهایی).",
    },
}


@dataclass
class PageAudit:
    """Raw per-page check results."""

    url: str
    status_code: int = 0
    response_time: float = 0.0
    size_bytes: int = 0
    redirect_hops: int = 0
    final_url: str = ""
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    h1_count: int = 0
    has_viewport: bool = False
    has_lang: bool = False
    has_json_ld: bool = False
    has_og: bool = False
    is_noindex: bool = False
    images_total: int = 0
    images_no_alt: int = 0
    mixed_content: int = 0
    internal_links: List[str] = field(default_factory=list)
    error: str = ""


@dataclass
class AuditIssue:
    """One aggregated issue for the report."""

    issue_id: str
    severity: str
    category: str
    title: str
    description: str
    recommendation: str
    owner: str
    effort: str
    count: int = 0
    sample_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for job result / JSON export."""
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "severity_fa": SEVERITY_LABELS_FA.get(self.severity, self.severity),
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "owner": self.owner,
            "effort": self.effort,
            "count": self.count,
            "sample_urls": self.sample_urls[:10],
        }


def _make_issue(issue_id: str, count: int, sample_urls: List[str]) -> AuditIssue:
    """Build AuditIssue from catalog entry."""
    meta = ISSUE_CATALOG[issue_id]
    return AuditIssue(
        issue_id=issue_id,
        severity=meta["severity"],
        category=meta["category"],
        title=meta["title"],
        description=meta["description"],
        recommendation=meta["recommendation"],
        owner=meta["owner"],
        effort=meta["effort"],
        count=count,
        sample_urls=sample_urls[:10],
    )


class TechnicalSeoAuditor:
    """
    Run technical SEO checks on a site sample.

    Input:
        site_url: Homepage URL (https://example.com).
        urls: Page URLs to audit (from sitemap); homepage added automatically.
        max_pages: Sample cap.
        timeout / concurrency: HTTP tuning.
    """

    def __init__(
        self,
        site_url: str,
        urls: Optional[List[str]] = None,
        *,
        max_pages: int = 100,
        timeout: int = 20,
        concurrency: int = 6,
        link_check_limit: int = 40,
        configured_sitemap_url: str = "",
    ) -> None:
        """
        Input:
            site_url: Crawl base (may include path, e.g. https://ex.com/blog).
            urls: Page URLs from the project sitemap.
            configured_sitemap_url: Project sitemap used for crawl + site checks.
        """
        raw = site_url if "://" in site_url else f"https://{site_url}"
        parsed = urlparse(raw)
        self.scheme = parsed.scheme or "https"
        self.host = parsed.netloc
        # Keep subdirectory scope (e.g. /blog) — do not strip to domain root
        self.base_path = (parsed.path or "").rstrip("/")
        self.site_url = (
            f"{self.scheme}://{self.host}{self.base_path}"
            if self.base_path
            else f"{self.scheme}://{self.host}"
        )
        self.homepage = self.site_url if self.site_url.endswith("/") else self.site_url + "/"
        self.configured_sitemap_url = (configured_sitemap_url or "").strip()
        self.urls = list(urls or [])
        # max_pages <= 0 → crawl the whole sitemap (bounded by ABSOLUTE_PAGE_CAP)
        self.max_pages = ABSOLUTE_PAGE_CAP if max_pages <= 0 else min(max_pages, ABSOLUTE_PAGE_CAP)
        self.timeout = timeout
        self.concurrency = max(1, concurrency)
        self.link_check_limit = max(0, link_check_limit)
        self.session = build_http_session()
        self.session.headers.update(DEFAULT_REQUEST_HEADERS)
        self.detected_stacks: List[str] = []

    # ---------------- stack / CMS detection ----------------

    def detect_stack(self) -> List[str]:
        """
        Detect CMS / tech stack from homepage HTML and response headers.

        Output:
            Ordered list of stack keys (e.g. ["wordpress", "woocommerce"]).
        """
        resp = self._head_or_get(self.homepage)
        if resp is None:
            return []
        html = (resp.text or "")[:400_000].lower()
        headers = {k.lower(): v.lower() for k, v in resp.headers.items()}
        cookies = "; ".join(resp.cookies.keys()).lower()
        powered = headers.get("x-powered-by", "") + " " + headers.get("server", "")

        stacks: List[str] = []

        def hit(key: str, condition: bool) -> None:
            if condition and key not in stacks:
                stacks.append(key)

        hit("wordpress", "wp-content" in html or "wp-includes" in html or "wp-json" in html)
        hit("woocommerce", "woocommerce" in html)
        hit("shopify", "cdn.shopify.com" in html or "x-shopid" in headers or "myshopify" in html)
        hit("magento", "mage-" in html or "magento" in html or "x-magento" in " ".join(headers))
        hit("joomla", "joomla" in html or "/media/jui/" in html)
        hit("drupal", "drupal" in html or "x-drupal-cache" in headers)
        hit("nextjs", "__next_data__" in html or "_next/static" in html or "next.js" in powered)
        hit("nuxt", "__nuxt" in html or "_nuxt/" in html)
        hit("laravel", "laravel_session" in cookies or "laravel" in powered or "xsrf-token" in cookies)
        hit("django", "csrftoken" in cookies or "wsgiserver" in powered)
        hit("aspnet", "asp.net" in powered or "x-aspnet-version" in headers)

        self.detected_stacks = stacks
        return stacks

    def _stack_solution_for(self, issue_id: str) -> Tuple[str, str]:
        """
        Pick best stack-specific solution for an issue.

        Output:
            (stack_label_fa, solution_text) — empty strings when none.
        """
        solutions = STACK_SOLUTIONS.get(issue_id) or {}
        for stack in self.detected_stacks:
            text = solutions.get(stack)
            if text:
                return STACK_LABELS_FA.get(stack, stack), text
        return "", ""

    # ---------------- site-level checks ----------------

    def _head_or_get(self, url: str, *, allow_redirects: bool = True):
        """GET with redirects; returns response or None."""
        try:
            return self.session.get(
                url, timeout=self.timeout, allow_redirects=allow_redirects
            )
        except Exception as exc:
            logger.debug("Request failed %s: %s", url, exc)
            return None

    def check_site_level(self) -> List[AuditIssue]:
        """
        Run robots/sitemap/https/www/404/favicon checks.

        Output:
            List of failed site-level issues.
        """
        issues: List[AuditIssue] = []

        # HTTP → HTTPS redirect
        http_resp = self._head_or_get(f"http://{self.host}/", allow_redirects=True)
        if http_resp is not None:
            final = urlparse(http_resp.url)
            if final.scheme != "https":
                issues.append(_make_issue("site_https_redirect", 1, [f"http://{self.host}/"]))

        # www canonicalization
        alt_host = self.host[4:] if self.host.startswith("www.") else f"www.{self.host}"
        alt_resp = self._head_or_get(f"{self.scheme}://{alt_host}/", allow_redirects=True)
        if alt_resp is not None and alt_resp.status_code == 200:
            if urlparse(alt_resp.url).netloc == alt_host:
                issues.append(
                    _make_issue(
                        "site_www_canonical",
                        1,
                        [f"{self.scheme}://{alt_host}/", self.site_url],
                    )
                )

        # robots.txt always lives at host root
        robots = self._head_or_get(f"{self.scheme}://{self.host}/robots.txt")
        robots_ok = robots is not None and robots.status_code == 200 and robots.text.strip()
        if not robots_ok:
            issues.append(
                _make_issue("site_robots_txt", 1, [f"{self.scheme}://{self.host}/robots.txt"])
            )

        # Prefer the project's configured sitemap (e.g. /blog/sitemap_index.xml),
        # then path-scoped candidates, then domain root — never ignore the project setting.
        sitemap_urls: List[str] = []
        if self.configured_sitemap_url:
            sitemap_urls.append(self.configured_sitemap_url)
        if self.base_path:
            sitemap_urls.extend(
                [
                    f"{self.scheme}://{self.host}{self.base_path}/sitemap.xml",
                    f"{self.scheme}://{self.host}{self.base_path}/sitemap_index.xml",
                ]
            )
        sitemap_urls.extend(
            [
                f"{self.scheme}://{self.host}/sitemap.xml",
                f"{self.scheme}://{self.host}/sitemap_index.xml",
            ]
        )
        if robots_ok:
            for line in robots.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    if sm and sm not in sitemap_urls:
                        sitemap_urls.append(sm)

        sitemap_ok = False
        checked: List[str] = []
        for sm in sitemap_urls:
            if sm in checked:
                continue
            checked.append(sm)
            resp = self._head_or_get(sm)
            if resp is not None and resp.status_code == 200 and b"<" in resp.content[:200]:
                sitemap_ok = True
                break
            # Cap probes so we don't hammer remote hosts
            if len(checked) >= 5:
                break
        if not sitemap_ok:
            issues.append(
                _make_issue(
                    "site_sitemap",
                    1,
                    checked[:3]
                    or [self.configured_sitemap_url or f"{self.scheme}://{self.host}/sitemap.xml"],
                )
            )

        # 404 handling under the scoped site path
        probe = self._head_or_get(
            f"{self.site_url.rstrip('/')}/seo-toolkit-404-probe-{int(time.time())}"
        )
        if probe is not None and probe.status_code == 200:
            issues.append(_make_issue("site_404_handling", 1, [probe.url]))

        # favicon at host root
        fav = self._head_or_get(f"{self.scheme}://{self.host}/favicon.ico")
        if fav is None or fav.status_code != 200:
            issues.append(
                _make_issue("site_favicon", 1, [f"{self.scheme}://{self.host}/favicon.ico"])
            )

        return issues

    # ---------------- page-level checks ----------------

    def _audit_page(self, url: str) -> PageAudit:
        """
        Fetch one page and extract on-page signals.

        Output:
            PageAudit with parsed metrics (error set on failure).
        """
        page = PageAudit(url=url)
        t0 = time.perf_counter()
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        except Exception as exc:
            page.error = str(exc)
            return page

        page.response_time = time.perf_counter() - t0
        page.status_code = resp.status_code
        page.redirect_hops = len(resp.history)
        page.final_url = resp.url
        page.size_bytes = len(resp.content or b"")

        if resp.status_code >= 400 or not resp.content:
            return page

        try:
            soup = BeautifulSoup(resp.content, "html.parser")
        except Exception as exc:
            page.error = f"parse: {exc}"
            return page

        title_tag = soup.find("title")
        page.title = title_tag.get_text(strip=True) if title_tag else ""

        desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        page.meta_description = (desc.get("content") or "").strip() if desc else ""

        canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
        page.canonical = (canonical.get("href") or "").strip() if canonical else ""

        page.h1_count = len(soup.find_all("h1"))
        page.has_viewport = bool(
            soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        )
        html_tag = soup.find("html")
        page.has_lang = bool(html_tag and (html_tag.get("lang") or "").strip())
        page.has_json_ld = bool(
            soup.find("script", attrs={"type": "application/ld+json"})
        )
        page.has_og = bool(
            soup.find("meta", attrs={"property": re.compile(r"^og:title$", re.I)})
        )

        for meta in soup.find_all("meta"):
            name = (meta.get("name") or "").lower()
            if "robots" in name and "noindex" in (meta.get("content") or "").lower():
                page.is_noindex = True
                break

        imgs = soup.find_all("img")
        page.images_total = len(imgs)
        page.images_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())

        # Mixed content on https pages
        if urlparse(resp.url).scheme == "https":
            mixed = 0
            for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src")):
                for el in soup.find_all(tag):
                    val = el.get(attr) or ""
                    if val.startswith("http://"):
                        mixed += 1
            page.mixed_content = mixed

        # Internal links (same host)
        seen: Set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(resp.url, href)
            p = urlparse(absolute)
            if p.netloc == self.host and absolute not in seen:
                seen.add(absolute)
        page.internal_links = list(seen)[:100]

        return page

    def _check_internal_links(self, pages: List[PageAudit]) -> Tuple[int, List[str]]:
        """
        HEAD-check a sample of internal links for 404s.

        Output:
            (broken_count, sample broken URLs).
        """
        if self.link_check_limit <= 0:
            return 0, []

        audited = {p.url for p in pages} | {p.final_url for p in pages}
        candidates: List[str] = []
        seen: Set[str] = set()
        for p in pages:
            for link in p.internal_links:
                if link not in seen and link not in audited:
                    seen.add(link)
                    candidates.append(link)
        candidates = candidates[: self.link_check_limit]
        broken: List[str] = []

        def _probe(u: str) -> Optional[str]:
            try:
                r = self.session.head(u, timeout=self.timeout, allow_redirects=True)
                if r.status_code == 405:
                    r = self.session.get(u, timeout=self.timeout, allow_redirects=True)
                return u if r.status_code >= 400 else None
            except Exception:
                return None  # network failure ≠ broken link

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            for fut in as_completed([pool.submit(_probe, u) for u in candidates]):
                res = fut.result()
                if res:
                    broken.append(res)

        return len(broken), broken

    def _aggregate_page_issues(self, pages: List[PageAudit]) -> List[AuditIssue]:
        """
        Convert raw page audits into aggregated issues.

        Output:
            Issue list (only issues with count > 0).
        """
        ok_pages = [p for p in pages if not p.error and p.status_code < 400]
        issues: List[AuditIssue] = []

        def add(issue_id: str, urls: List[str]) -> None:
            if urls:
                issues.append(_make_issue(issue_id, len(urls), urls))

        add("page_broken", [p.url for p in pages if p.status_code >= 400 or p.error])
        add("page_redirect_chain", [p.url for p in pages if p.redirect_hops >= 2])
        add("title_missing", [p.url for p in ok_pages if not p.title])
        add(
            "title_length",
            [p.url for p in ok_pages if p.title and not (30 <= len(p.title) <= 60)],
        )

        # Duplicates
        title_map: Dict[str, List[str]] = {}
        for p in ok_pages:
            if p.title:
                title_map.setdefault(p.title, []).append(p.url)
        dup_title_urls = [u for urls in title_map.values() if len(urls) > 1 for u in urls]
        add("title_duplicate", dup_title_urls)

        add("meta_desc_missing", [p.url for p in ok_pages if not p.meta_description])
        desc_map: Dict[str, List[str]] = {}
        for p in ok_pages:
            if p.meta_description:
                desc_map.setdefault(p.meta_description, []).append(p.url)
        dup_desc_urls = [u for urls in desc_map.values() if len(urls) > 1 for u in urls]
        add("meta_desc_duplicate", dup_desc_urls)

        add("h1_missing", [p.url for p in ok_pages if p.h1_count == 0])
        add("h1_multiple", [p.url for p in ok_pages if p.h1_count > 1])
        add("canonical_missing", [p.url for p in ok_pages if not p.canonical])
        add("noindex_pages", [p.url for p in ok_pages if p.is_noindex])
        add(
            "img_alt_missing",
            [p.url for p in ok_pages if p.images_total and p.images_no_alt > 0],
        )
        add("viewport_missing", [p.url for p in ok_pages if not p.has_viewport])
        add("lang_missing", [p.url for p in ok_pages if not p.has_lang])
        add("schema_missing", [p.url for p in ok_pages if not p.has_json_ld])
        add("og_missing", [p.url for p in ok_pages if not p.has_og])
        add("mixed_content", [p.url for p in ok_pages if p.mixed_content > 0])
        add("slow_pages", [p.url for p in ok_pages if p.response_time > 3.0])
        add("large_pages", [p.url for p in ok_pages if p.size_bytes > 2 * 1024 * 1024])

        url_problem: List[str] = []
        for p in ok_pages:
            parsed = urlparse(p.url)
            path = parsed.path or ""
            if (
                any(c.isupper() for c in path)
                or len(p.url) > 120
                or len((parsed.query or "").split("&")) > 3
                or "_" in path
            ):
                url_problem.append(p.url)
        add("url_issues", url_problem)

        return issues

    # ---------------- scoring / tasks ----------------

    @staticmethod
    def compute_score(issues: List[AuditIssue], total_pages: int) -> int:
        """
        Health score 0..100 weighted by severity and prevalence.

        Output:
            Integer score (higher is better).
        """
        score = 100.0
        for issue in issues:
            weight = SEVERITY_WEIGHTS.get(issue.severity, 2.0)
            if issue.issue_id.startswith("site_"):
                factor = 1.0
            else:
                share = issue.count / max(1, total_pages)
                factor = 0.35 + 0.65 * min(1.0, share)
            score -= weight * factor
        return max(0, int(round(score)))

    @staticmethod
    def build_task_plan(issues: List[AuditIssue]) -> List[Dict[str, Any]]:
        """
        Prioritized task list for dev/content team.

        Output:
            Ordered tasks: priority number, action, owner, effort, category.
        """
        sev_rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
        ordered = sorted(
            issues, key=lambda i: (sev_rank.get(i.severity, 9), -i.count)
        )
        tasks: List[Dict[str, Any]] = []
        for n, issue in enumerate(ordered, start=1):
            tasks.append(
                {
                    "priority": n,
                    "severity": issue.severity,
                    "severity_fa": SEVERITY_LABELS_FA.get(issue.severity, issue.severity),
                    "title": issue.title,
                    "action": issue.recommendation,
                    "owner": issue.owner,
                    "effort": issue.effort,
                    "category": issue.category,
                    "count": issue.count,
                }
            )
        return tasks

    # ---------------- orchestration ----------------

    def run(
        self,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full audit: site checks + page sample + aggregation.

        Input:
            on_progress: Optional callback(percent, message).

        Output:
            Result dict: score, issues, task plan, stats.
        """
        def report(pct: int, msg: str) -> None:
            if on_progress:
                on_progress(pct, msg)

        report(3, "تشخیص CMS و استک فنی سایت…")
        self.detect_stack()

        report(5, "بررسی‌های سطح سایت (robots، sitemap، HTTPS)…")
        site_issues = self.check_site_level()

        # Build page sample: scoped homepage first
        sample: List[str] = [self.homepage]
        for u in self.urls:
            if u not in sample:
                sample.append(u)
            if len(sample) >= self.max_pages:
                break

        report(15, f"بررسی {len(sample)} صفحه…")
        pages: List[PageAudit] = []
        done = 0
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {pool.submit(self._audit_page, u): u for u in sample}
            for fut in as_completed(futures):
                pages.append(fut.result())
                done += 1
                if done % 5 == 0 or done == len(sample):
                    pct = 15 + int(55 * done / max(1, len(sample)))
                    report(pct, f"بررسی صفحات: {done}/{len(sample)}")

        report(75, "بررسی لینک‌های داخلی…")
        broken_count, broken_urls = self._check_internal_links(pages)
        page_issues = self._aggregate_page_issues(pages)
        if broken_count:
            page_issues.append(
                _make_issue("broken_internal_links", broken_count, broken_urls)
            )

        all_issues = site_issues + page_issues
        sev_rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
        all_issues.sort(key=lambda i: (sev_rank.get(i.severity, 9), -i.count))

        report(90, "محاسبه امتیاز و اولویت‌بندی…")
        score = self.compute_score(all_issues, len(sample))
        tasks = self.build_task_plan(all_issues)

        # Attach stack-specific solutions to issues and tasks
        issue_dicts = []
        stack_solution_by_title: Dict[str, Dict[str, str]] = {}
        for issue in all_issues:
            data = issue.to_dict()
            stack_label, solution = self._stack_solution_for(issue.issue_id)
            data["stack_label"] = stack_label
            data["stack_solution"] = solution
            issue_dicts.append(data)
            if solution:
                stack_solution_by_title[issue.title] = {
                    "stack_label": stack_label,
                    "stack_solution": solution,
                }
        for task in tasks:
            extra = stack_solution_by_title.get(task["title"]) or {}
            task["stack_label"] = extra.get("stack_label", "")
            task["stack_solution"] = extra.get("stack_solution", "")

        severity_counts = {s: 0 for s in SEVERITY_ORDER}
        for issue in all_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        ok_pages = [p for p in pages if not p.error and p.status_code < 400]
        avg_time = (
            sum(p.response_time for p in ok_pages) / len(ok_pages) if ok_pages else 0.0
        )

        result = {
            "site_url": self.site_url,
            "homepage": self.homepage,
            "sitemap_url": self.configured_sitemap_url,
            "base_path": self.base_path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pages_checked": len(sample),
            "pages_ok": len(ok_pages),
            "avg_response_time": round(avg_time, 2),
            "score": score,
            "severity_counts": severity_counts,
            "issues": issue_dicts,
            "tasks": tasks,
            "checked_links": self.link_check_limit,
            "broken_links": broken_count,
            "detected_stacks": self.detected_stacks,
            "detected_stacks_fa": [
                STACK_LABELS_FA.get(s, s) for s in self.detected_stacks
            ],
        }
        report(95, "ممیزی کامل شد")
        return result
