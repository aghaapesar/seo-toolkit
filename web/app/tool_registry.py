"""
Central registry for web tools: login gates and job→tool mapping.

Input / Output:
    Constants consumed by pages.py, task progress, and (optionally) APIs.
    Keeps access rules in one place so sidebar groups and page gates stay aligned.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

# Tools whose HTML page redirects to /login when the session has no user.
# APIs for these tools already use require_user; keep page + API in sync.
LOGIN_REQUIRED_TOOLS: FrozenSet[str] = frozenset(
    {
        "technical-audit",
        "content-audit",
        "site-index",
        "content-cluster",
        "product-gap",
        "internal-links",
        "knowledge-export",
        "project-tasks",
        "service-status",
    }
)

# Background job_type → tool page slug (for /tasks/{id} back-links).
JOB_TYPE_TO_TOOL: Dict[str, str] = {
    "index_diff": "index-diff",
    "content_cluster": "content-cluster",
    "content_audit": "content-audit",
    "site_index": "site-index",
    "product_gap": "product-gap",
    "knowledge_export": "knowledge-export",
    "technical_audit": "technical-audit",
    "internal_links": "internal-links",
}


def tool_requires_login(tool_id: str) -> bool:
    """True when the tool HTML page must be behind login."""
    return tool_id in LOGIN_REQUIRED_TOOLS
