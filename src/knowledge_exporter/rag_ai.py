"""
LLM structuring for RAG Markdown export.

Input:
    Extracted page text + page type + site URL.

Output:
    Clean Markdown body (no frontmatter) matching docs/RAG_CONTENT_STANDARD.md
    (official chatbot knowledge-base content standard).

Frontmatter (url + title only) is added by RagWriter — not by the LLM.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List

from src.ai_errors import is_credit_exhausted
from src.services.gapgpt_curl import gapgpt_chat_completion

logger = logging.getLogger(__name__)

# Repo copy of the official standard (also used for docs / operators).
_STANDARD_PATH = Path(__file__).resolve().parents[2] / "docs" / "RAG_CONTENT_STANDARD.md"

# Cleanup patterns from the standard §6 (Sargarmia-style site chrome).
# Applied after LLM (or on fallback) so leftover template text is stripped.
DEFAULT_CLEANUP_PATTERNS: List[str] = [
    r"اشتراک\s*گذاری\s*اشتراک\s*گذاری در شبکه های اجتماعی:[^\n]*?کدکالا:",
    r"از\s+\d+\s+رای",
    r"(?s)برچسبها\s*:.*$",
    r"(?s)بخشها\s*:.*$",
    r"(?s)محصولات\s*مرتبط\s*:.*$",
    r"(?s)دیدگاه\s*ها\s*:.*$",
]

# Product body must mirror §7 sample structure exactly.
_PRODUCT_SYSTEM = """تو ویرایشگر محتوای فارسی برای پایگاه دانش چت‌بات (RAG) هستی.
خروجی باید دقیقاً مطابق «استاندارد تهیه محتوا برای پایگاه دانش (RAG)» باشد.

## اصول (الزامی)
1. هر سند فقط یک موضوع/محصول است؛ موضوعات مختلف را مخلوط نکن.
2. خروجی فقط بدنه Markdown UTF-8 است — بدون YAML frontmatter (سیستم جداگانه url/title را می‌گذارد).
3. متن تمیز: منو، اشتراک‌گذاری، محصولات مرتبط، تبلیغات، امتیاز/رای، برچسب‌ها و قالب سایت را حذف کن.
4. نام کامل محصول را در H1 و حداقل یک‌بار در ابتدای متن معرفی تکرار کن؛ فقط «این محصول» ننویس.
5. قیمت و موجودی را ننویس یا صریح بنویس: «برای قیمت به‌روز به صفحه محصول مراجعه شود».
6. طول پیشنهادی ۲۰۰ تا ۲۰۰۰ کلمه؛ کوتاه بودن اشکال ندارد، مخلوط شدن موضوعات اشکال دارد.
7. لینک خارجی نساز.

## ساختار اجباری (مثل نمونه استاندارد §۷)
# {نام کامل محصول}

{۱ تا چند جمله معرفی با نام کامل — بدون سرتیتر ## معرفی}

## مشخصات کلی
- تعداد بازیکن: …
- رده سنی: …
- مدت بازی: …
- سبک: …
(و سایر مشخصات ساخت‌یافته مثل جنس، ابعاد، محتویات جعبه در صورت وجود)

## نحوه بازی
خلاصه قوانین / گیم‌پلی…

## سوالات متداول
**سؤال پرتکرار؟**
پاسخ کوتاه.

## تکمیل کمبودها
- اول فقط از محتوای صفحه استخراج کن.
- اگر مشخصات کلیدی نبود: نام اصلی/خارجی را از عنوان بگیر و با دانش همان محصول تکمیل کن؛
  هر خط تکمیل‌شده را با پسوند « (تکمیل‌شده از دانش عمومی)» علامت بزن.
- اگر مطمئن نیستی بنویس «ذکر نشده» و به صفحه محصول ارجاع بده."""

_BLOG_SYSTEM = """تو ویرایشگر بلاگ برای پایگاه دانش RAG (دستیار خرید) هستی؛ مطابق استاندارد RAG.
قوانین:
- خروجی Markdown بدون frontmatter؛ یک موضوع در هر سند.
- H1 = عنوان مقاله؛ بخش‌بندی با ## .
- منو، اشتراک‌گذاری، ویجت مرتبط را حذف کن.
- قیمت جعلی نساز. در پایان در صورت مرتبط بودن ## راهنمای خرید اضافه کن و به صفحه/سایت ارجاع بده بدون لینک جعلی.
- UTF-8 فارسی."""

_GENERIC_SYSTEM = """تو ویرایشگر اسناد عمومی برای RAG هستی (قوانین، راهنما، سیاست‌ها).
مطابق بخش ۳ استاندارد: بدون نیاز به frontmatter در بدنه؛ با # و ## بخش‌بندی کن.
متن قالب سایت را حذف کن. موضوعات مختلف را مخلوط نکن. UTF-8."""


def _model_params(model: Any) -> tuple[str, str, str]:
    """Extract base_url, api_key, llm_model from AIModel."""
    return (
        getattr(model, "base_url", "") or "",
        getattr(model, "api_key", "") or "",
        getattr(model, "model", "") or getattr(model, "llm_model", "") or "",
    )


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def apply_cleanup_patterns(text: str, patterns: List[str] | None = None) -> str:
    """
    Strip site chrome using regex patterns from the RAG standard §6.

    Input:
        text: Markdown body.
        patterns: Optional override list; default = Sargarmia-style patterns.

    Output:
        Cleaned text (invalid patterns are skipped).
    """
    out = text or ""
    for raw in patterns or DEFAULT_CLEANUP_PATTERNS:
        try:
            out = re.sub(raw, "", out, flags=re.MULTILINE)
        except re.error as exc:
            logger.warning("Invalid cleanup pattern skipped: %s (%s)", raw, exc)
    # Collapse excessive blank lines left by removals
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def extract_foreign_name(title: str) -> str:
    """
    Best-effort extract of Latin/foreign product name from a Persian title.

    Input:
        title: e.g. «بازی فکری جالیز - Jaliz Board Game»

    Output:
        Latin fragment or empty string.
    """
    text = (title or "").strip()
    if not text:
        return ""
    for sep in (" - ", " – ", " — ", " | ", "("):
        if sep in text:
            part = text.split(sep, 1)[-1].rstrip(")").strip()
            latin = re.sub(r"[^A-Za-z0-9][^A-Za-z0-9 ]*", " ", part)
            latin = re.sub(r"\s+", " ", latin).strip()
            if re.search(r"[A-Za-z]{3,}", latin):
                return latin[:120]
    matches = re.findall(r"[A-Za-z][A-Za-z0-9 &'\\-]{2,}", text)
    if matches:
        return max(matches, key=len)[:120]
    return ""


def structure_page_markdown(
    *,
    url: str,
    title: str,
    description: str,
    raw_markdown: str,
    page_type: str,
    model: Any,
    lang: str = "fa",
    allow_knowledge_fill: bool = True,
) -> str:
    """
    Rewrite extracted markdown into RAG-standard structure via LLM.

    Input:
        url, title, description, raw_markdown, page_type, model.
        allow_knowledge_fill: Fill missing product specs from foreign name + knowledge.

    Output:
        Structured markdown body (H1 + sections). Frontmatter is NOT included.

    Raises:
        RuntimeError: credit exhausted.
    """
    page_type = (page_type or "other").lower()
    if page_type == "product":
        system = _PRODUCT_SYSTEM
    elif page_type == "blog":
        system = _BLOG_SYSTEM
    else:
        system = _GENERIC_SYSTEM

    foreign = extract_foreign_name(title)
    fill_note = ""
    if page_type == "product" and allow_knowledge_fill:
        fill_note = (
            f"\nOriginal/foreign name hint: {foreign or '(extract from title yourself)'}\n"
            "Complete missing specs from knowledge of that exact product; tag with "
            "« (تکمیل‌شده از دانش عمومی)».\n"
        )
    elif page_type == "product":
        fill_note = "\nDo NOT fill from external knowledge. Missing → «ذکر نشده».\n"

    # Point the model at the official sample shape
    sample_hint = ""
    if page_type == "product":
        sample_hint = """
Reference shape (body only — no frontmatter in your output):
# بازی فکری جالیز

بازی فکری جالیز یک بازی کارتی رقابتی با تم کشاورزی و معامله است.

## مشخصات کلی
- تعداد بازیکن: ۳ تا ۷ نفر
- رده سنی: ۹ سال به بالا
- مدت بازی: ۳۰ تا ۶۰ دقیقه
- سبک: کارتی، اقتصادی، تعاملی

## نحوه بازی
...

## سوالات متداول
**آیا برای بچه‌های زیر ۹ سال مناسب است؟**
خیر، ...
"""

    user_prompt = f"""Page URL (for referral only, do not invent other links): {url}
Title: {title}
Meta description: {description}
Language: {lang}
Page type: {page_type}
{fill_note}
{sample_hint}
--- RAW EXTRACTED CONTENT (primary source) ---
{raw_markdown[:14000]}
--- END ---

Produce the cleaned RAG Markdown body now (complete for this single topic)."""

    base_url, api_key, llm_model = _model_params(model)
    try:
        raw = gapgpt_chat_completion(
            base_url,
            api_key,
            llm_model,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.25,
        )
    except Exception as exc:
        if is_credit_exhausted(exc):
            raise RuntimeError("credit_exhausted") from exc
        logger.warning("LLM structure failed for %s: %s — using raw markdown", url, exc)
        return apply_cleanup_patterns(_fallback_body(title, raw_markdown, page_type=page_type))

    body = apply_cleanup_patterns(_strip_code_fences(raw))
    # Strip accidental frontmatter if the model ignored instructions
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
    if len(body) < 80:
        return apply_cleanup_patterns(_fallback_body(title, raw_markdown, page_type=page_type))
    return body


def _fallback_body(title: str, raw_markdown: str, *, page_type: str = "other") -> str:
    """
    Rule-based fallback when LLM unavailable — still matches standard shape.
    """
    heading = f"# {title}\n\n" if title else ""
    body = raw_markdown.strip()
    if page_type == "product":
        return (
            f"{heading}"
            f"{title} — خلاصه استخراج‌شده از صفحه محصول.\n\n"
            f"## مشخصات کلی\n- ذکر نشده\n\n"
            f"## نحوه بازی\n{body}\n\n"
            f"## سوالات متداول\n"
            f"**قیمت به‌روز چقدر است؟**\n"
            f"برای قیمت به‌روز به صفحه محصول مراجعه شود.\n"
        )
    return heading + body
