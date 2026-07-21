"""Unit tests for technical SEO audit engine and PDF report."""

from pathlib import Path

from src.seo_pdf_report import _to_persian_digits, generate_seo_audit_pdf
from src.technical_seo_audit import (
    ISSUE_CATALOG,
    PageAudit,
    TechnicalSeoAuditor,
    _make_issue,
)


def _auditor() -> TechnicalSeoAuditor:
    """Auditor instance without network usage."""
    return TechnicalSeoAuditor("https://example.com", [], max_pages=10)


def _ok_page(url: str, **overrides) -> PageAudit:
    """Healthy page baseline; override fields to trigger issues."""
    defaults = dict(
        url=url,
        status_code=200,
        response_time=0.5,
        size_bytes=50_000,
        title="عنوان تستی مناسب برای صفحه نمونه ما",
        meta_description="توضیحات متا برای صفحه تست",
        canonical=url,
        h1_count=1,
        has_viewport=True,
        has_lang=True,
        has_json_ld=True,
        has_og=True,
    )
    defaults.update(overrides)
    return PageAudit(**defaults)


class TestAggregation:
    """Page-level issue aggregation."""

    def test_healthy_pages_yield_no_issues(self):
        pages = [
            _ok_page(
                f"https://example.com/p{i}",
                title=f"عنوان یکتای صفحه شماره {i} برای تست سلامت",
                meta_description=f"توضیحات یکتای صفحه {i}",
            )
            for i in range(3)
        ]
        issues = _auditor()._aggregate_page_issues(pages)
        assert issues == []

    def test_broken_page_detected(self):
        pages = [_ok_page("https://example.com/a", status_code=404)]
        ids = [i.issue_id for i in _auditor()._aggregate_page_issues(pages)]
        assert "page_broken" in ids

    def test_duplicate_titles_detected(self):
        pages = [
            _ok_page("https://example.com/a", title="عنوان تکراری در هر دو صفحه سایت"),
            _ok_page("https://example.com/b", title="عنوان تکراری در هر دو صفحه سایت"),
        ]
        issues = _auditor()._aggregate_page_issues(pages)
        dup = next(i for i in issues if i.issue_id == "title_duplicate")
        assert dup.count == 2

    def test_missing_meta_and_h1(self):
        pages = [_ok_page("https://example.com/a", meta_description="", h1_count=0)]
        ids = {i.issue_id for i in _auditor()._aggregate_page_issues(pages)}
        assert {"meta_desc_missing", "h1_missing"} <= ids

    def test_slow_and_noindex(self):
        pages = [
            _ok_page("https://example.com/a", response_time=5.0, is_noindex=True)
        ]
        ids = {i.issue_id for i in _auditor()._aggregate_page_issues(pages)}
        assert {"slow_pages", "noindex_pages"} <= ids


class TestScoringAndTasks:
    """Score computation and prioritized task plan."""

    def test_score_perfect_when_no_issues(self):
        assert TechnicalSeoAuditor.compute_score([], 50) == 100

    def test_score_drops_with_critical_issues(self):
        issues = [_make_issue("page_broken", 10, ["https://example.com/x"])]
        score = TechnicalSeoAuditor.compute_score(issues, 10)
        assert score < 90

    def test_score_never_negative(self):
        issues = [_make_issue(i, 100, ["u"]) for i in ISSUE_CATALOG]
        assert TechnicalSeoAuditor.compute_score(issues, 10) >= 0

    def test_task_plan_ordered_by_severity(self):
        issues = [
            _make_issue("og_missing", 5, ["u"]),          # low
            _make_issue("page_broken", 2, ["u"]),          # critical
            _make_issue("meta_desc_missing", 9, ["u"]),    # high
        ]
        tasks = TechnicalSeoAuditor.build_task_plan(issues)
        assert [t["severity"] for t in tasks] == ["critical", "high", "low"]
        assert [t["priority"] for t in tasks] == [1, 2, 3]
        assert all(t["owner"] and t["action"] for t in tasks)


class TestCatalog:
    """Issue catalog completeness for the Persian report."""

    def test_all_entries_have_persian_fields(self):
        for issue_id, meta in ISSUE_CATALOG.items():
            for key in ("severity", "category", "title", "description", "recommendation", "owner", "effort"):
                assert meta.get(key), f"{issue_id} missing {key}"
            assert meta["severity"] in ("critical", "high", "medium", "low")


class TestPdf:
    """PDF generation output."""

    def test_persian_digits(self):
        assert _to_persian_digits(1402) == "۱۴۰۲"

    def test_generate_pdf(self, tmp_path: Path):
        issues = [
            _make_issue("page_broken", 3, ["https://example.com/a"]),
            _make_issue("title_duplicate", 8, ["https://example.com/b"]),
        ]
        result = {
            "site_url": "https://example.com",
            "generated_at": "2026-07-21T12:00:00+00:00",
            "pages_checked": 20,
            "pages_ok": 17,
            "avg_response_time": 1.1,
            "score": TechnicalSeoAuditor.compute_score(issues, 20),
            "severity_counts": {"critical": 1, "high": 1, "medium": 0, "low": 0},
            "issues": [i.to_dict() for i in issues],
            "tasks": TechnicalSeoAuditor.build_task_plan(issues),
            "broken_links": 1,
        }
        out = generate_seo_audit_pdf(result, tmp_path / "report.pdf", project_name="پروژه تست")
        assert out.is_file()
        data = out.read_bytes()
        assert data[:5] == b"%PDF-"
        assert len(data) > 10_000
