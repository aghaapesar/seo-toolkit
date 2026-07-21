/**
 * Technical Issues Check page.
 *
 * Input:  form (project, site URL, sample size).
 * Output: background job start + previous PDF/JSON report list.
 */

/** Escape text for safe HTML insertion. */
function taEscape(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

/** Resolve selected project slug from form or global selector. */
function taProjectSlug(form) {
  const fromForm = form?.project_slug?.value || "";
  if (fromForm) return fromForm;
  return typeof getActiveProjectSlug === "function" ? getActiveProjectSlug() || "" : "";
}

/** Render one saved report card. */
function taReportCard(report, labels) {
  const score = Number(report.score ?? -1);
  const cls = score >= 80 ? "good" : score >= 60 ? "mid" : "bad";
  const date = (report.generated_at || "").slice(0, 16).replace("T", " ");
  const sev = report.severity_counts || {};
  const sevLine = `C:${sev.critical || 0} H:${sev.high || 0} M:${sev.medium || 0} L:${sev.low || 0}`;

  const buttons = [];
  if (report.pdf) {
    buttons.push(
      `<a class="btn btn-primary btn-sm" href="${taEscape(report.pdf.download_url)}">${taEscape(labels.pdf)}</a>`
    );
  }
  if (report.json) {
    buttons.push(
      `<a class="btn btn-ghost btn-sm" href="${taEscape(report.json.download_url)}">${taEscape(labels.json)}</a>`
    );
  }

  return `
    <div class="ta-report-card">
      <div class="ta-report-meta">
        <span class="ta-report-site">${taEscape(report.site_url || report.json?.name || "")}</span>
        <span class="ta-report-sub">${taEscape(date)} — ${taEscape(String(report.pages_checked ?? "?"))} pages
          — <span class="ta-sev">${taEscape(sevLine)}</span></span>
      </div>
      ${score >= 0 ? `<span class="ta-score ${cls}" title="${taEscape(labels.score)}">${score}</span>` : ""}
      <div class="ta-report-actions">${buttons.join("")}</div>
    </div>`;
}

/** Load previous reports for the selected project. */
async function taLoadReports(form) {
  const container = document.getElementById("ta-reports");
  if (!container) return;
  const labels = window.TECH_AUDIT_LABELS || {};
  const slug = taProjectSlug(form);
  if (!slug) {
    container.innerHTML = `<p class="muted">${taEscape(labels.noReports || "")}</p>`;
    return;
  }
  try {
    const res = await fetch(
      `/api/v1/technical-audit/reports?project_slug=${encodeURIComponent(slug)}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const reports = data.reports || [];
    container.innerHTML = reports.length
      ? reports.map((r) => taReportCard(r, labels)).join("")
      : `<p class="muted">${taEscape(labels.noReports || "")}</p>`;
  } catch (err) {
    container.innerHTML = `<p class="muted">${taEscape(String(err))}</p>`;
  }
}

/** Bind form submit + report list refresh. */
function initTechnicalAuditPage(lang) {
  const form = document.getElementById("form-technical-audit");
  const errorBox = document.getElementById("ta-error");
  if (!form) return;

  taLoadReports(form);
  form.project_slug?.addEventListener("change", () => taLoadReports(form));

  // Restore last branding edits from localStorage
  try {
    const raw = localStorage.getItem("ta_report_branding");
    if (raw) {
      const saved = JSON.parse(raw);
      Object.keys(saved || {}).forEach((name) => {
        const el = form.elements.namedItem(name);
        if (el && "value" in el && saved[name]) el.value = saved[name];
      });
    }
  } catch (_e) {
    /* ignore */
  }

  // Full-crawl toggle disables the sample size input
  const fullCrawlBox = document.getElementById("ta-full-crawl");
  fullCrawlBox?.addEventListener("change", () => {
    const input = form.max_pages;
    if (input) input.disabled = fullCrawlBox.checked;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox?.classList.add("hidden");

    const slug = taProjectSlug(form);
    if (!slug) {
      if (errorBox) {
        errorBox.textContent =
          lang === "fa" ? "ابتدا یک پروژه انتخاب کنید." : "Select a project first.";
        errorBox.classList.remove("hidden");
      }
      return;
    }

    const fullCrawl = document.getElementById("ta-full-crawl")?.checked;
    const body = new FormData();
    body.append("project_slug", slug);
    body.append("site_url", form.site_url?.value || "");
    body.append("sitemap_url", form.sitemap_url?.value || "");
    // 0 = crawl every sitemap URL (server caps at 5000)
    body.append("max_pages", fullCrawl ? "0" : form.max_pages?.value || "100");

    // PDF branding / cover / section headers
    const brandingFields = [
      "report_title",
      "client_name",
      "prepared_by",
      "company_name",
      "cover_footer",
      "header_title",
      "header_subtitle",
      "section_summary",
      "section_issues",
      "section_tasks",
    ];
    brandingFields.forEach((name) => {
      const el = form.elements.namedItem(name);
      if (el && "value" in el) body.append(name, el.value || "");
    });

    // Remember last branding choices for this browser
    try {
      const saved = {};
      brandingFields.forEach((name) => {
        const el = form.elements.namedItem(name);
        if (el && "value" in el) saved[name] = el.value || "";
      });
      localStorage.setItem("ta_report_branding", JSON.stringify(saved));
    } catch (_e) {
      /* ignore quota / private mode */
    }

    const submitBtn = document.getElementById("ta-submit");
    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await fetch("/api/v1/technical-audit/start", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      // Follow job on the shared progress page
      window.location.href = `${data.progress_url}?lang=${encodeURIComponent(lang)}`;
    } catch (err) {
      if (errorBox) {
        errorBox.textContent = String(err.message || err);
        errorBox.classList.remove("hidden");
      }
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}
