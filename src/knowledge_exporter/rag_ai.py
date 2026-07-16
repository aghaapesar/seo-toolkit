"""
LLM structuring for RAG Markdown export.

Input:
    Extracted page text + page type + site URL.

Output:
    Clean structured Markdown body (no frontmatter).

Rules:
    - Site data is authoritative; never contradict source page.
    - No invented price/stock; use referral phrase when missing.
    - Web search is OFF (phase 1).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.ai_errors import is_credit_exhausted
from src.services.gapgpt_curl import gapgpt_chat_completion

logger = logging.getLogger(__name__)

_PRODUCT_SYSTEM = """You are an SEO content editor preparing Persian/Farsi knowledge-base documents for RAG.
Rules:
- Use ONLY facts from the provided page content. Never invent price, stock, SKU, or specs.
- If a spec is missing, write «ذکر نشده» or «برای اطلاعات دقیق به صفحه محصول مراجعه کنید».
- Do NOT add external URLs. Only reference the given page URL when needed.
- Output Markdown body only (no YAML frontmatter).
- Start with one H1 matching the product full name.
- Include sections: ## مشخصات کلی (bullet list), ## معرفی, ## سوالات متداول (2-4 Q&A).
- Repeat the full product name at least once in the intro.
- Remove menus, share buttons, related products, ads, boilerplate.
- UTF-8 Persian prose; keep factual tone."""

_BLOG_SYSTEM = """You are an SEO editor preparing blog articles for a shopping assistant RAG system.
Rules:
- Use ONLY facts from the provided article. Never invent products or prices.
- Output Markdown body only (no YAML frontmatter).
- Start with H1 = article title.
- Keep ## sections from source where useful.
- Add ## راهنمای خرید at the end ONLY if the article discusses products/topics where purchase guidance makes sense; suggest visiting the site, no fake product links.
- Remove boilerplate (menus, share, related posts widgets).
- UTF-8 Persian."""

_GENERIC_SYSTEM = """You are an SEO editor cleaning page content for RAG.
Output Markdown body only. H1 + logical ## sections. Facts from source only. UTF-8."""


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


def structure_page_markdown(
    *,
    url: str,
    title: str,
    description: str,
    raw_markdown: str,
    page_type: str,
    model: Any,
    lang: str = "fa",
) -> str:
    """
    Rewrite extracted markdown into RAG-standard structure via LLM.

    Input:
        url, title, description, raw_markdown, page_type, model.

    Output:
        Structured markdown body (H1 + sections).

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

    user_prompt = f"""Page URL: {url}
Title: {title}
Meta description: {description}
Language: {lang}
Page type: {page_type}

--- RAW EXTRACTED CONTENT ---
{raw_markdown[:12000]}
--- END ---

Produce the cleaned RAG Markdown body now."""

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
            temperature=0.2,
        )
    except Exception as exc:
        if is_credit_exhausted(exc):
            raise RuntimeError("credit_exhausted") from exc
        logger.warning("LLM structure failed for %s: %s — using raw markdown", url, exc)
        return _fallback_body(title, raw_markdown)

    body = _strip_code_fences(raw)
    if len(body) < 80:
        return _fallback_body(title, raw_markdown)
    return body


def _fallback_body(title: str, raw_markdown: str) -> str:
    """Rule-based fallback when LLM unavailable."""
    heading = f"# {title}\n\n" if title else ""
    return heading + raw_markdown.strip()
