"""
GapGPT HTTP transport via curl with DNS --resolve fallback.

Input:
    OpenAI-compatible chat request (base_url, api_key, model, messages).

Output:
    Parsed JSON response dict or raises RuntimeError.

When system DNS cannot resolve api.gapgpt.app (Cursor sandbox / foreign VPN),
curl --resolve uses known IPs while preserving TLS SNI.
"""

from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from src.services.http_client import _clean_proxy_env

logger = logging.getLogger(__name__)

# Known GapGPT API hosts → IPv4 (updated when GapGPT changes infra).
GAPGPT_HOST_IPS: Dict[str, str] = {
    "api.gapgpt.app": "185.143.234.235",
    "api.gapapi.com": "188.114.99.0",
}


def _host_from_base_url(base_url: str) -> str:
    """Extract hostname from OpenAI-style base URL."""
    return (urlparse(base_url or "").hostname or "").lower()


def _curl_chat(
    base_url: str,
    api_key: str,
    payload: Dict[str, Any],
    *,
    use_resolve: bool = False,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    POST /chat/completions via curl.

    Input:
        base_url: e.g. https://api.gapgpt.app/v1
        api_key: Bearer token.
        payload: JSON body.
        use_resolve: If True, pass --resolve host:443:ip for known hosts.

    Output:
        Parsed JSON dict from API response.
    """
    if not shutil.which("curl"):
        raise RuntimeError("curl not found")

    host = _host_from_base_url(base_url)
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(payload, ensure_ascii=False)

    cmd = [
        "curl",
        "-sS",
        "--max-time",
        str(timeout),
        "-X",
        "POST",
        url,
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
        "-d",
        body,
        "-w",
        "\n__HTTP__%{http_code}",
    ]

    if use_resolve and host in GAPGPT_HOST_IPS:
        cmd[1:1] = [
            "--resolve",
            f"{host}:443:{GAPGPT_HOST_IPS[host]}",
        ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=_clean_proxy_env(),
        check=False,
    )
    out = proc.stdout or ""
    stderr = (proc.stderr or "").strip()

    if "__HTTP__" not in out:
        raise RuntimeError(stderr or "curl failed with no response")

    raw_body, _, code_str = out.rpartition("__HTTP__")
    code = code_str.strip()

    if code == "200":
        return json.loads(raw_body or "{}")

    if (stderr and "Could not resolve host" in stderr) or code in ("000", ""):
        if not use_resolve and host in GAPGPT_HOST_IPS:
            return _curl_chat(
                base_url, api_key, payload, use_resolve=True, timeout=timeout
            )

    if code in ("401", "403"):
        raise RuntimeError(f"HTTP {code}: invalid API key or access denied")
    if code == "404":
        model = payload.get("model", "")
        raise RuntimeError(f"HTTP 404: model '{model}' not found on GapGPT — try gpt-4o-mini")

    detail = (raw_body.strip() or stderr or f"HTTP {code or 'failed'}")[:300]
    raise RuntimeError(detail or f"HTTP {code or 'failed'}")


def gapgpt_chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None,
    timeout: int = 90,
) -> str:
    """
    Call GapGPT chat/completions and return assistant message content.

    Input:
        base_url, api_key, model, messages: OpenAI-compatible fields.

    Output:
        Assistant text content string.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if response_format:
        payload["response_format"] = response_format

    # Try direct curl first; auto-retry with --resolve on DNS failure.
    try:
        data = _curl_chat(base_url, api_key, payload, use_resolve=False, timeout=timeout)
    except RuntimeError as exc:
        if "Could not resolve" in str(exc) or "resolve" in str(exc).lower():
            data = _curl_chat(base_url, api_key, payload, use_resolve=True, timeout=timeout)
        else:
            raise

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("GapGPT returned no choices")
    return (choices[0].get("message") or {}).get("content") or ""


def gapgpt_test_connection(
    base_url: str,
    api_key: str,
    model: str,
    timeout: int = 25,
) -> bool:
    """
    Lightweight connectivity test for Settings UI.

    Output:
        True if API returns choices; raises RuntimeError on auth/model errors.
    """
    if platform.system() != "Darwin" or not shutil.which("curl"):
        return False
    data = _curl_chat(
        base_url,
        api_key,
        {
            "model": model,
            "messages": [{"role": "user", "content": "سلام"}],
            "max_tokens": 5,
        },
        use_resolve=False,
        timeout=timeout,
    )
    return bool(data.get("choices"))
