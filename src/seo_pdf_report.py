"""
Persian RTL PDF report for technical SEO audits (fpdf2 + Vazirmatn).

Input:
    Audit result dict from TechnicalSeoAuditor.run().

Output:
    Styled A4 PDF: cover, score, issue tables by severity,
    prioritized task plan for client + dev team.
"""

from __future__ import annotations

import logging
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

    def __init__(self, site_url: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.site_url = site_url
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
        self.cell(0, 6, "گزارش ممیزی سئو تکنیکال", align="R")
        self.set_x(15)
        self.set_font("Vazir", "", 8)
        self.cell(60, 6, self.site_url, align="L")
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


def _cover_page(pdf: SeoAuditPdf, result: Dict[str, Any], project_name: str) -> None:
    """Full-bleed cover with title, site, date, and score badge."""
    pdf._in_cover = True
    pdf.add_page()
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.set_fill_color(*C_ACCENT)
    pdf.rect(0, 190, 210, 4, style="F")

    pdf.set_y(70)
    pdf.set_font("Vazir", "B", 26)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 14, "گزارش ممیزی سئو تکنیکال", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Vazir", "", 14)
    if project_name:
        pdf.cell(0, 10, project_name, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Vazir", "", 12)
    pdf.cell(0, 9, result.get("site_url", ""), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Score circle
    score = int(result.get("score", 0))
    pdf.set_y(120)
    cx, cy, r = 105, 145, 24
    ring = SEVERITY_COLORS["low"] if score >= 80 else (
        SEVERITY_COLORS["medium"] if score >= 60 else SEVERITY_COLORS["critical"]
    )
    pdf.set_draw_color(*ring)
    pdf.set_line_width(2.2)
    pdf.ellipse(cx - r, cy - r, r * 2, r * 2)
    pdf.set_line_width(0.2)
    pdf.set_xy(cx - r, cy - 9)
    pdf.set_font("Vazir", "B", 24)
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
    pdf.cell(0, 7, "تهیه‌شده با Seo Toolkit", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf._in_cover = False


def _summary_page(pdf: SeoAuditPdf, result: Dict[str, Any]) -> None:
    """Executive summary: severity KPI boxes + interpretation text."""
    pdf.add_page()
    pdf.section_title("خلاصه مدیریتی")

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
        f"در این ممیزی {_to_persian_digits(result.get('pages_checked', 0))} صفحه از سایت "
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


def _issues_pages(pdf: SeoAuditPdf, issues: List[Dict[str, Any]]) -> None:
    """Detailed issue cards grouped by severity."""
    pdf.add_page()
    pdf.section_title("جزئیات مشکلات")

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


def _task_plan_page(pdf: SeoAuditPdf, tasks: List[Dict[str, Any]]) -> None:
    """Prioritized action table for the dev/content team."""
    pdf.add_page()
    pdf.section_title("برنامه اقدام اولویت‌بندی‌شده")
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
        "پیشنهاد می‌شود پس از رفع موارد بحرانی و زیاد، ممیزی مجدد انجام شود تا روند بهبود امتیاز ثبت گردد.",
        size=9,
        color=C_MUTED,
    )


def generate_seo_audit_pdf(
    result: Dict[str, Any],
    output_path: Path,
    *,
    project_name: str = "",
) -> Path:
    """
    Render full Persian PDF report from audit result.

    Input:
        result: TechnicalSeoAuditor.run() output.
        output_path: Target .pdf path (parent dirs created).
        project_name: Optional client/project display name for cover.

    Output:
        Written PDF path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = SeoAuditPdf(result.get("site_url", ""))
    _cover_page(pdf, result, project_name)
    _summary_page(pdf, result)
    _issues_pages(pdf, result.get("issues", []))
    _task_plan_page(pdf, result.get("tasks", []))

    pdf.output(str(output_path))
    logger.info("SEO audit PDF written: %s", output_path)
    return output_path
