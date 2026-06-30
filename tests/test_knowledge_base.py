"""Unit tests for KnowledgeBase duplicate detection."""

from src.knowledge_base import KnowledgeBase


def test_is_duplicate_content_detects_similar_title(tmp_path, monkeypatch):
    """Similar titles above threshold should be treated as duplicates."""
    monkeypatch.chdir(tmp_path)
    kb = KnowledgeBase("example.com", base_dir="knowledge_base")
    kb.add_generated_content(
        title="راهنمای خرید گوشی",
        keywords=["گوشی"],
        content_type="article",
        predicted_impressions=100,
    )

    assert kb.is_duplicate_content("راهنمای خرید گوشی موبایل", ["گوشی"], threshold=0.8)
