"""
Persian RTL PDF report for technical SEO audits (fpdf2 + Vazirmatn).

Input:
    Audit result dict from TechnicalSeoAuditor.run()
    + optional ReportBranding (cover / headers / section titles).

Output:
    Styled A4 PDF: cover, score, issue tables by severity,
    prioritized task plan for client + dev team.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Brand palette (RGB)
C_PRIMARY = (16, 82, 130)       # deep blue
C_ACCENT = (14, 165, 133)       # teal
C_DARK = (33, 37, 41)
C_MUTED = (108, 117, 125)
C_LIGHT_BG = (243, 246, 249)
C_WHITE = (255, 255, 255)

SEVERITY_COLORS = {
    "critical": (220, 53, 69),
    "high": (253, 126, 20),
    "medium": (255, 193, 7),
    "low": (108, 175, 80),
}

SEVERITY_LABELS = {
    "critical": "بحرانی",
    "high": "زیاد",
    "medium": "متوسط",
    "low": "کم",
}


@dataclass
class ReportBranding:
    """
    Editable cover + header labels for the PDF report.

    Empty strings fall back to Persian defaults so callers can override
    only the fields they care about.
    """

    report_title: str = "گزارش بررسی مشکلات فنی"
    client_name: str = ""
    prepared_by: str = ""
    company_name: str = ""
    cover_footer: str = "تهیه‌شده با Seo Toolkit"
    header_title: str = "گزارش بررسی مشکلات فنی"
    header_subtitle: str = ""  # empty → site URL
    section_summary: str = "خلاصه مدیریتی"
    section_issues: str = "جزئیات مشکلات"
    section_tasks: str = "برنامه اقدام اولویت‌بندی‌شده"

    def resolved(self, *, project_name: str = "", site_url: str = "") -> "ReportBranding":
        """
        Fill blanks with sensible defaults.

        Input:
            project_name: Fallback for client_name when empty.
            site_url: Fallback for header_subtitle when empty.
        """
        return ReportBranding(
            report_title=(self.report_title or "").strip() or "گزارش بررسی مشکلات فنی",
            client_name=(self.client_name or "").strip() or (project_name or "").strip(),
            prepared_by=(self.prepared_by or "").strip(),
            company_name=(self.company_name or "").strip(),
            cover_footer=(self.cover_footer or "").strip() or "تهیه‌شده با Seo Toolkit",
            header_title=(self.header_title or "").strip() or "گزارش بررسی مشکلات فنی",
            header_subtitle=(self.header_subtitle or "").strip() or (site_url or "").strip(),
            section_summary=(self.section_summary or "").strip() or "خلاصه مدیریتی",
            section_issues=(self.section_issues or "").strip() or "جزئیات مشکلات",
            section_tasks=(self.section_tasks or "").strip() or "برنامه اقدام اولویت‌بندی‌شده",
        )

    def to_dict(self) -> Dict[str, str]:
        """Serialize for JSON storage / job result."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "ReportBranding":
        """
        Build branding from form/API dict; unknown keys ignored.

        Input:
            raw: Optional mapping of field → string.
        """
        if not raw:
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {
            k: str(v).strip() if v is not None else ""
            for k, v in raw.items()
            if k in known
        }
        return cls(**kwargs)


def branding_defaults() -> Dict[str, str]:
    """Default branding labels for the web form (pre-fill values)."""
    return ReportBranding().to_dict()


def _to_persian_digits(value: Any) -> str:
    """Convert ASCII digits to Persian digits."""
    text = str(value)
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return text.translate(table)


def _fix_zwnj(text: str) -> str:
    """
    Replace ZWNJ with narrow no-break space (U+202F).

    fpdf2's bidi pass drops Boundary-Neutral chars (incl. ZWNJ U+200C)
    before shaping, gluing Persian half-spaced words together
    (نمی‌شود → نمیشود). U+202F survives bidi, breaks Arabic joining,
    and renders as a hair-thin non-breaking gap.
    """
    return text.replace("\u200c", "\u202f") if text else text


class SeoAuditPdf(FPDF):
    """A4 RTL PDF with Vazirmatn font, header band, and footer page numbers."""

    def __init__(self, site_url: str, branding: Optional[ReportBranding] = None) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.site_url = site_url
        self.branding = branding or ReportBranding()
        self._in_cover = False
        self.add_font("Vazir", "", str(FONT_DIR / "Vazirmatn-Regular.ttf"))
        self.add_font("Vazir", "B", str(FONT_DIR / "Vazirmatn-Bold.ttf"))
        self.set_text_shaping(True)
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(15, 18, 15)

    def cell(self, w=None, h=None, text="", **kwargs):  # noqa: D102 — ZWNJ-safe override
        return super().cell(w, h, _fix_zwnj(text), **kwargs)

    def multi_cell(self, w, h=None, text="", **kwargs):  # noqa: D102 — ZWNJ-safe override
        return super().multi_cell(w, h, _fix_zwnj(text), **kwargs)

    def header(self) -> None:  # noqa: D102 — fpdf hook
        if self._in_cover:
            return
        self.set_fill_color(*C_PRIMARY)
        self.rect(0, 0, 210, 12, style="F")
        self.set_y(3)
        self.set_font("Vazir", "B", 9)
        self.set_text_color(*C_WHITE)
        self.cell(0, 6, self.branding.header_title, align="R")
        self.set_x(15)
        self.set_font("Vazir", "", 8)
        left = self.branding.header_subtitle or self.site_url
        self.cell(60, 6, left, align="L")
        self.set_y(18)
        self.set_text_color(*C_DARK)

    def footer(self) -> None:  # noqa: D102 — fpdf hook
        if self._in_cover or self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_draw_color(*C_MUTED)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_font("Vazir", "", 8)
        self.set_text_color(*C_MUTED)
        self.cell(
            0,
            8,
            _to_persian_digits(f"صفحه {self.page_no()}"),
            align="C",
        )

    # ---------- building blocks ----------

    def rtl_cell(self, w: float, h: float, text: str, **kwargs) -> None:
        """Right-aligned cell shortcut."""
        kwargs.setdefault("align", "R")
        self.cell(w, h, text, **kwargs)

    def section_title(self, text: str) -> None:
        """Colored section heading with accent bar."""
        if self.get_y() > 250:
            self.add_page()
        y = self.get_y() + 2
        self.set_fill_color(*C_ACCENT)
        self.rect(191, y, 4, 9, style="F")
        self.set_xy(15, y)
        self.set_font("Vazir", "B", 14)
        self.set_text_color(*C_PRIMARY)
        self.cell(174, 9, text, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*C_DARK)
        self.ln(3)

    def paragraph(self, text: str, *, size: int = 10, color=C_DARK) -> None:
        """RTL multi-line paragraph."""
        self.set_x(self.l_margin)
        self.set_font("Vazir", "", size)
        self.set_text_color(*color)
        self.multi_cell(
            0, 6.5, text, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.set_text_color(*C_DARK)


def _cover_page(pdf: SeoAuditPdf, result: Dict[str, Any], branding: ReportBranding) -> None:
    """Full-bleed cover with title, client, preparer, date, and score badge."""
    pdf._in_cover = True
    pdf.add_page()
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.set_fill_color(*C_ACCENT)
    pdf.rect(0, 190, 210, 4, style="F")

    pdf.set_y(55)
    pdf.set_font("Vazir", "B", 26)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(
        0, 14, branding.report_title,
        align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(3)

    if branding.client_name:
        pdf.set_font("Vazir", "", 14)
        pdf.cell(
            0, 9, branding.client_name,
            align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
    pdf.set_font("Vazir", "", 12)
    pdf.cell(
        0, 8, result.get("site_url", ""),
        align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )

    # Preparer / company block on cover
    if branding.prepared_by or branding.company_name:
        pdf.ln(4)
        pdf.set_font("Vazir", "", 11)
        pdf.set_text_color(200, 215, 228)
        if branding.prepared_by:
            pdf.cell(
                0, 7, f"تهیه‌کننده: {branding.prepared_by}",
                align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
        if branding.company_name:
            pdf.cell(
                0, 7, branding.company_name,
                align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
        pdf.set_text_color(*C_WHITE)

    # Score circle
    score = int(result.get("score", 0))
    pdf.set_y(125)
    cx, cy, r = 105, 150, 24
    ring = SEVERITY_COLORS["low"] if score >= 80 else (
        SEVERITY_COLORS["medium"] if score >= 60 else SEVERITY_COLORS["critical"]
    )
    pdf.set_draw_color(*ring)
    pdf.set_line_width(2.2)
    pdf.ellipse(cx - r, cy - r, r * 2, r * 2)
    pdf.set_line_width(0.2)
    pdf.set_xy(cx - r, cy - 9)
    pdf.set_font("Vazir", "B", 24)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(r * 2, 12, _to_persian_digits(score), align="C", new_y=YPos.NEXT)
    pdf.set_xy(cx - r, cy + 3)
    pdf.set_font("Vazir", "", 9)
    pdf.cell(r * 2, 6, "از ۱۰۰", align="C")

    # Date + stats
    try:
        gen = datetime.fromisoformat(result.get("generated_at", "").replace("Z", "+00:00"))
        date_str = gen.strftime("%Y/%m/%d")
    except ValueError:
        date_str = ""
    pdf.set_y(205)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Vazir", "", 11)
    pdf.set_text_color(*C_WHITE)
    stats = (
        f"تاریخ گزارش: {_to_persian_digits(date_str)}   |   "
        f"صفحات بررسی‌شده: {_to_persian_digits(result.get('pages_checked', 0))}   |   "
        f"مشکلات یافت‌شده: {_to_persian_digits(len(result.get('issues', [])))}"
    )
    pdf.cell(0, 8, stats, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Vazir", "", 9)
    pdf.set_text_color(200, 215, 228)
    pdf.cell(
        0, 7, branding.cover_footer,
        align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf._in_cover = False


def _summary_page(pdf: SeoAuditPdf, result: Dict[str, Any], branding: ReportBranding) -> None:
    """Executive summary: severity KPI boxes + interpretation text."""
    pdf.add_page()
    pdf.section_title(branding.section_summary)

    counts = result.get("severity_counts", {})
    total_issues = len(result.get("issues", []))
    score = int(result.get("score", 0))

    verdict = (
        "وضعیت فنی سایت خوب است و مشکلات محدودی دارد."
        if score >= 80
        else "وضعیت فنی سایت متوسط است و نیاز به بهبود دارد."
        if score >= 60
        else "وضعیت فنی سایت ضعیف است و رفع مشکلات بحرانی فوریت دارد."
    )
    pdf.paragraph(
        f"در این بررسی {_to_persian_digits(result.get('pages_checked', 0))} صفحه از سایت "
        f"{result.get('site_url', '')} بررسی شد و در مجموع {_to_persian_digits(total_issues)} "
        f"دسته مشکل شناسایی گردید. امتیاز سلامت فنی سایت {_to_persian_digits(score)} از ۱۰۰ است. "
        + verdict
    )
    pdf.ln(4)

    # KPI boxes
    box_w, box_h, gap = 41, 24, 4
    x = 195 - box_w
    y = pdf.get_y()
    for sev in ("critical", "high", "medium", "low"):
        color = SEVERITY_COLORS[sev]
        pdf.set_fill_color(*color)
        pdf.rect(x, y, box_w, box_h, style="F")
        pdf.set_xy(x, y + 3)
        pdf.set_font("Vazir", "B", 16)
        pdf.set_text_color(*C_WHITE)
        pdf.cell(box_w, 9, _to_persian_digits(counts.get(sev, 0)), align="C", new_y=YPos.NEXT)
        pdf.set_x(x)
        pdf.set_font("Vazir", "", 10)
        pdf.cell(box_w, 7, SEVERITY_LABELS[sev], align="C")
        x -= box_w + gap
    pdf.set_text_color(*C_DARK)
    pdf.set_y(y + box_h + 8)

    avg = result.get("avg_response_time", 0)
    broken = result.get("broken_links", 0)
    pdf.paragraph(
        f"میانگین زمان پاسخ صفحات: {_to_persian_digits(avg)} ثانیه — "
        f"لینک‌های داخلی شکسته یافت‌شده: {_to_persian_digits(broken)} مورد.",
        size=10,
        color=C_MUTED,
    )

    stacks_fa = result.get("detected_stacks_fa") or []
    if stacks_fa:
        pdf.ln(1)
        pdf.paragraph(
            f"پلتفرم شناسایی‌شده: {'، '.join(stacks_fa)} — "
            "راهکارهای اختصاصی این پلتفرم در بخش جزئیات مشکلات آمده است.",
            size=10,
            color=C_PRIMARY,
        )


def _issues_pages(
    pdf: SeoAuditPdf,
    issues: List[Dict[str, Any]],
    branding: ReportBranding,
) -> None:
    """Detailed issue cards grouped by severity."""
    pdf.add_page()
    pdf.section_title(branding.section_issues)

    for sev in ("critical", "high", "medium", "low"):
        group = [i for i in issues if i.get("severity") == sev]
        if not group:
            continue
        if pdf.get_y() > 240:
            pdf.add_page()
        # Severity band
        color = SEVERITY_COLORS[sev]
        pdf.set_fill_color(*color)
        pdf.set_text_color(*C_WHITE)
        pdf.set_font("Vazir", "B", 11)
        pdf.cell(
            0, 9,
            f"اولویت {SEVERITY_LABELS[sev]} ({_to_persian_digits(len(group))} مورد)",
            align="R", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.set_text_color(*C_DARK)
        pdf.ln(2)

        for issue in group:
            needed = 40
            if pdf.get_y() > 297 - 22 - needed:
                pdf.add_page()
            y0 = pdf.get_y()
            pdf.set_fill_color(*C_LIGHT_BG)
            pdf.set_draw_color(*color)

            pdf.set_x(pdf.l_margin)
            pdf.set_font("Vazir", "B", 10.5)
            title = issue.get("title", "")
            count = issue.get("count", 0)
            suffix = f"  ({_to_persian_digits(count)} صفحه)" if count > 1 else ""
            pdf.cell(0, 8, f"{title}{suffix}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_x(pdf.l_margin)
            pdf.set_font("Vazir", "", 9)
            pdf.set_text_color(*C_MUTED)
            pdf.multi_cell(
                0, 5.5, issue.get("description", ""), align="R",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
            pdf.set_x(pdf.l_margin)
            pdf.set_text_color(*C_DARK)
            pdf.set_font("Vazir", "B", 9)
            pdf.multi_cell(
                0, 5.5, f"راهکار: {issue.get('recommendation', '')}", align="R",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )

            stack_solution = issue.get("stack_solution") or ""
            if stack_solution:
                stack_label = issue.get("stack_label") or "پلتفرم شما"
                pdf.set_x(pdf.l_margin)
                pdf.set_text_color(*C_ACCENT)
                pdf.set_font("Vazir", "B", 9)
                pdf.multi_cell(
                    0, 5.5, f"راهکار در {stack_label}: {stack_solution}", align="R",
                    new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                )
                pdf.set_text_color(*C_DARK)

            meta = (
                f"مسئول: {issue.get('owner', '')}   |   حجم کار: {issue.get('effort', '')}"
                f"   |   دسته: {issue.get('category', '')}"
            )
            pdf.set_font("Vazir", "", 8.5)
            pdf.set_text_color(*C_MUTED)
            pdf.cell(0, 5.5, meta, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            samples = issue.get("sample_urls") or []
            if samples:
                pdf.set_font("Vazir", "", 7.5)
                for u in samples[:3]:
                    pdf.cell(0, 4.5, u[:110], align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*C_DARK)

            # Left accent line for the card
            pdf.set_line_width(1.0)
            pdf.line(195, y0 + 1, 195, pdf.get_y() - 1)
            pdf.set_line_width(0.2)
            pdf.ln(4)


def _task_plan_page(
    pdf: SeoAuditPdf,
    tasks: List[Dict[str, Any]],
    branding: ReportBranding,
) -> None:
    """Prioritized action table for the dev/content team."""
    pdf.add_page()
    pdf.section_title(branding.section_tasks)
    pdf.paragraph(
        "جدول زیر ترتیب پیشنهادی رفع مشکلات را نشان می‌دهد. موارد بحرانی باید در اسپرینت جاری برطرف شوند.",
        size=9.5,
        color=C_MUTED,
    )
    pdf.ln(2)

    # Column widths (RTL order: rightmost = priority)
    w_pr, w_task, w_owner, w_effort, w_sev = 12, 108, 26, 18, 16
    header_h, row_h = 9, 7

    def table_header() -> None:
        pdf.set_fill_color(*C_PRIMARY)
        pdf.set_text_color(*C_WHITE)
        pdf.set_font("Vazir", "B", 9)
        x = 195
        for w, label in (
            (w_pr, "ردیف"),
            (w_sev, "اولویت"),
            (w_task, "اقدام"),
            (w_owner, "مسئول"),
            (w_effort, "حجم"),
        ):
            x -= w
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(w, header_h, label, align="C", fill=True)
        pdf.ln(header_h)
        pdf.set_text_color(*C_DARK)

    table_header()
    fill = False
    for task in tasks:
        # Estimate needed height from action text length
        action = f"{task.get('title', '')} — {task.get('action', '')}"
        if task.get("stack_solution"):
            label = task.get("stack_label") or "پلتفرم"
            action += f" [{label}: {task['stack_solution']}]"
        pdf.set_font("Vazir", "", 8.5)
        lines = max(1, len(action) // 62 + 1)
        h = max(row_h, lines * 4.5 + 2)
        if pdf.get_y() + h > 275:
            pdf.add_page()
            table_header()
            fill = False

        y = pdf.get_y()
        if fill:
            pdf.set_fill_color(*C_LIGHT_BG)
            pdf.rect(15, y, 180, h, style="F")

        sev_color = SEVERITY_COLORS.get(task.get("severity", "low"), C_MUTED)
        x = 195
        # priority
        x -= w_pr
        pdf.set_xy(x, y)
        pdf.set_font("Vazir", "B", 9)
        pdf.cell(w_pr, h, _to_persian_digits(task.get("priority", "")), align="C")
        # severity chip
        x -= w_sev
        pdf.set_xy(x + 1.5, y + (h - 5.5) / 2)
        pdf.set_fill_color(*sev_color)
        pdf.set_text_color(*C_WHITE)
        pdf.set_font("Vazir", "B", 7.5)
        pdf.cell(w_sev - 3, 5.5, task.get("severity_fa", ""), align="C", fill=True)
        pdf.set_text_color(*C_DARK)
        # action (multi-line)
        x -= w_task
        pdf.set_xy(x, y + 1)
        pdf.set_font("Vazir", "", 8.5)
        pdf.multi_cell(
            w_task, 4.5, action, align="R", new_x=XPos.RIGHT, new_y=YPos.TOP
        )
        # owner
        x -= w_owner
        pdf.set_xy(x, y)
        pdf.cell(w_owner, h, task.get("owner", ""), align="C")
        # effort
        x -= w_effort
        pdf.set_xy(x, y)
        pdf.cell(w_effort, h, task.get("effort", ""), align="C")

        pdf.set_y(y + h)
        fill = not fill

    pdf.ln(6)
    pdf.paragraph(
        "پیشنهاد می‌شود پس از رفع موارد بحرانی و زیاد، بررسی مجدد انجام شود تا روند بهبود امتیاز ثبت گردد.",
        size=9,
        color=C_MUTED,
    )


def generate_seo_audit_pdf(
    result: Dict[str, Any],
    output_path: Path,
    *,
    project_name: str = "",
    branding: Optional[ReportBranding] = None,
) -> Path:
    """
    Render full Persian PDF report from audit result.

    Input:
        result: TechnicalSeoAuditor.run() output.
        output_path: Target .pdf path (parent dirs created).
        project_name: Fallback client name when branding.client_name empty.
        branding: Optional cover/header/section overrides.

    Output:
        Written PDF path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    brand = (branding or ReportBranding()).resolved(
        project_name=project_name,
        site_url=result.get("site_url", ""),
    )
    pdf = SeoAuditPdf(result.get("site_url", ""), brand)
    _cover_page(pdf, result, brand)
    _summary_page(pdf, result, brand)
    _issues_pages(pdf, result.get("issues", []), brand)
    _task_plan_page(pdf, result.get("tasks", []), brand)

    pdf.output(str(output_path))
    logger.info("SEO audit PDF written: %s", output_path)
    return output_path
