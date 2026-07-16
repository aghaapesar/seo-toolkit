"""
Detect AI provider credit / quota exhaustion from error messages.

Input:
    Exception or HTTP error text.

Output:
    User-facing notification flags and messages.
"""

from __future__ import annotations

import re
from typing import Union

# Patterns that usually mean the API account needs recharge.
_CREDIT_PATTERNS = (
    r"insufficient[_\s-]?quota",
    r"quota[_\s-]?exceeded",
    r"exceeded.*quota",
    r"rate[_\s-]?limit",
    r"too many requests",
    r"out of credits",
    r"credit[s]?\s*(low|empty|depleted|insufficient)",
    r"balance\s*(low|insufficient|empty)",
    r"billing",
    r"payment required",
    r"402",
    r"429",
    r"شارژ",
    r"اعتبار",
    r"موجودی",
)


def is_credit_exhausted(error: Union[BaseException, str]) -> bool:
    """
    Return True when error likely means API credits/quota are exhausted.

    Input:
        error: Exception instance or message string.

    Output:
        Boolean credit-exhausted flag.
    """
    text = str(error).lower()
    for pattern in _CREDIT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def credit_exhausted_message(lang: str = "fa") -> str:
    """Localized message asking user to recharge the AI model."""
    if lang == "fa":
        return (
            "اعتبار مدل AI تمام شده یا سقف درخواست پر شده است. "
            "لطفاً در پنل GapGPT/OpenAI شارژ کنید و دوباره تلاش کنید."
        )
    return (
        "AI model credits or rate limit exceeded. "
        "Please recharge your GapGPT/OpenAI account and retry."
    )
