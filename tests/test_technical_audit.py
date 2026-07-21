"""Unit tests for technical SEO audit engine and PDF report."""

from pathlib import Path

from src.seo_pdf_report import (
    ReportBranding,
    _fix_zwnj,
    _to_persian_digits,
    generate_seo_audit_pdf,
)
from src.technical_seo_audit import (
    ABSOLUTE_PAGE_CAP,
    ISSUE_CATALOG,
    PageAudit,
    STACK_LABELS_FA,
    STACK_SOLUTIONS,
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


class TestFullCrawlAndStack:
    """Full-crawl page cap and stack-specific solutions."""

    def test_max_pages_zero_means_full_crawl(self):
        a = TechnicalSeoAuditor("https://example.com", [], max_pages=0)
        assert a.max_pages == ABSOLUTE_PAGE_CAP

    def test_max_pages_capped(self):
        a = TechnicalSeoAuditor("https://example.com", [], max_pages=99999)
        assert a.max_pages == ABSOLUTE_PAGE_CAP

    def test_keeps_blog_path_as_site_base(self):
        a = TechnicalSeoAuditor(
            "https://zitro.ir/blog",
            [],
            max_pages=10,
            configured_sitemap_url="https://zitro.ir/blog/sitemap_index.xml",
        )
        assert a.site_url == "https://zitro.ir/blog"
        assert a.base_path == "/blog"
        assert a.homepage == "https://zitro.ir/blog/"
        assert a.configured_sitemap_url.endswith("sitemap_index.xml")

    def test_stack_solution_picked_for_detected_stack(self):
        a = _auditor()
        a.detected_stacks = ["wordpress"]
        label, solution = a._stack_solution_for("title_missing")
        assert label == STACK_LABELS_FA["wordpress"]
        assert "Rank Math" in solution or "Yoast" in solution

    def test_stack_solution_empty_when_unknown(self):
        a = _auditor()
        a.detected_stacks = []
        assert a._stack_solution_for("title_missing") == ("", "")

    def test_stack_solutions_reference_known_issues(self):
        for issue_id in STACK_SOLUTIONS:
            assert issue_id in ISSUE_CATALOG, f"unknown issue in solutions: {issue_id}"


class TestSitemapScope:
    """Project sitemap path scope (e.g. /blog/sitemap_index.xml)."""

    def test_site_base_from_blog_sitemap(self):
        from web.app.services.technical_audit_service import site_base_from_sitemap

        assert site_base_from_sitemap("https://zitro.ir/blog/sitemap_index.xml") == (
            "https://zitro.ir/blog"
        )
        assert site_base_from_sitemap("https://example.com/sitemap.xml") == (
            "https://example.com"
        )

    def test_url_in_site_scope_filters_path(self):
        from web.app.services.technical_audit_service import url_in_site_scope

        base = "https://zitro.ir/blog"
        assert url_in_site_scope("https://zitro.ir/blog/post-1", base)
        assert not url_in_site_scope("https://zitro.ir/products/x", base)
        assert not url_in_site_scope("https://other.com/blog/x", base)

    def test_resolve_uses_project_sitemap_not_root(self):
        from types import SimpleNamespace

        from web.app.services.technical_audit_service import resolve_audit_targets

        project = SimpleNamespace(
            domain="https://zitro.ir/blog/",
            sitemap_url="https://zitro.ir/blog/sitemap_index.xml",
        )
        site, sm = resolve_audit_targets(project)
        assert sm == "https://zitro.ir/blog/sitemap_index.xml"
        assert site == "https://zitro.ir/blog"


class TestPdf:
    """PDF generation output."""

    def test_persian_digits(self):
        assert _to_persian_digits(1402) == "۱۴۰۲"

    def test_fix_zwnj_replaces_half_space(self):
        assert _fix_zwnj("نمی\u200cشود") == "نمی\u202fشود"
        assert "\u200c" not in _fix_zwnj("شبکه\u200cهای اجتماعی")

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

    def test_branding_resolved_defaults(self):
        brand = ReportBranding(report_title="", client_name="").resolved(
            project_name="فروشگاه الف", site_url="https://a.example"
        )
        assert brand.report_title == "گزارش بررسی مشکلات فنی"
        assert brand.client_name == "فروشگاه الف"
        assert brand.header_subtitle == "https://a.example"
        assert brand.section_summary == "خلاصه مدیریتی"

    def test_generate_pdf_with_custom_branding(self, tmp_path: Path):
        issues = [_make_issue("og_missing", 2, ["https://example.com/x"])]
        result = {
            "site_url": "https://example.com",
            "generated_at": "2026-07-21T12:00:00+00:00",
            "pages_checked": 5,
            "pages_ok": 5,
            "avg_response_time": 0.8,
            "score": 90,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 1},
            "issues": [i.to_dict() for i in issues],
            "tasks": TechnicalSeoAuditor.build_task_plan(issues),
            "broken_links": 0,
        }
        brand = ReportBranding(
            report_title="گزارش تخصصی سئو",
            client_name="کارفرمای نمونه",
            prepared_by="تیم سئو آلفا",
            company_name="آژانس آلفا",
            header_title="بررسی مشکلات فنی — آلفا",
            section_summary="خلاصه برای کارفرما",
            section_issues="فهرست ایرادات",
            section_tasks="چک‌لیست اقدام",
        )
        out = generate_seo_audit_pdf(
            result, tmp_path / "branded.pdf", branding=brand
        )
        assert out.is_file() and out.stat().st_size > 8_000
