/**
 * Dashboard home page — loads read-only KPIs and renders CSS charts.
 * Does not mutate backend state.
 */

function dashEscape(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getDashProjectSlug() {
  const fromUrl = new URLSearchParams(window.location.search).get("project");
  const fromBody = document.body.dataset.activeProject;
  const fromSelect = document.getElementById("global-project-select")?.value;
  return (fromUrl || fromSelect || fromBody || "").trim();
}

function getDashLang() {
  return document.getElementById("dashboard-page")?.dataset.lang || document.body.dataset.lang || "fa";
}

function statusLabel(labels, key) {
  const map = {
    pending: labels.pending,
    in_progress: labels.inProgress,
    done: labels.done,
    planned: labels.pending,
    writing: labels.inProgress,
    published: labels.done,
  };
  return map[key] || key;
}

function jobStatusLabel(labels, status) {
  const map = {
    running: labels.statusRunning,
    completed: labels.statusCompleted,
    failed: labels.statusFailed,
    queued: labels.statusPending,
    waiting_client: labels.statusPending,
    paused: labels.statusRunning,
  };
  return map[status] || status;
}

function renderBarChart(container, series, labels, lang) {
  if (!container) return;
  const entries = Object.entries(series || {}).filter(([, v]) => Number(v) >= 0);
  const max = Math.max(1, ...entries.map(([, v]) => Number(v)));
  if (!entries.length || entries.every(([, v]) => !v)) {
    container.innerHTML = `<p class="muted dash-empty">—</p>`;
    return;
  }
  container.innerHTML = entries
    .map(([key, val]) => {
      const n = Number(val) || 0;
      const pct = Math.round((n / max) * 100);
      const label = statusLabel(labels, key);
      return `<div class="dash-bar-row">
        <span class="dash-bar-label">${dashEscape(label)}</span>
        <div class="dash-bar-track" role="presentation">
          <div class="dash-bar-fill status-${dashEscape(key)}" style="width:${pct}%"></div>
        </div>
        <span class="dash-bar-value">${n}</span>
      </div>`;
    })
    .join("");
  container.classList.remove("muted");
}

function pageTypeLabel(key, lang) {
  const fa = { product: "محصول", category: "دسته", blog: "بلاگ", other: "سایر", page: "صفحه" };
  const en = { product: "Product", category: "Category", blog: "Blog", other: "Other", page: "Page" };
  const map = lang === "fa" ? fa : en;
  return map[key] || key;
}

function renderTypeChart(container, byType, lang) {
  if (!container) return;
  const entries = Object.entries(byType || {}).filter(([, v]) => Number(v) > 0);
  const total = entries.reduce((s, [, v]) => s + Number(v), 0);
  if (!total) {
    container.innerHTML = `<p class="muted dash-empty">—</p>`;
    return;
  }

  const colors = ["#34d399", "#38bdf8", "#a78bfa", "#fbbf24", "#fb7185", "#94a3b8"];
  let angle = 0;
  const segments = entries.map(([key, val], idx) => {
    const n = Number(val);
    const pct = (n / total) * 100;
    const start = angle;
    angle += pct;
    return { key, n, pct, start, color: colors[idx % colors.length] };
  });
  const gradient = segments.map((s) => `${s.color} ${s.start}% ${s.start + s.pct}%`).join(", ");

  const legend = segments
    .map(
      (s) => `<li><span class="dash-legend-dot" style="background:${s.color}"></span>
        <span>${dashEscape(pageTypeLabel(s.key, lang))}</span>
        <strong>${s.n}</strong></li>`
    )
    .join("");

  container.innerHTML = `
    <div class="dash-donut-wrap">
      <div class="dash-donut" style="background:conic-gradient(${gradient})" role="img"
        aria-label="${dashEscape(String(total))} pages"></div>
      <div class="dash-donut-center"><strong>${total}</strong><span>${lang === "fa" ? "صفحه" : "pages"}</span></div>
    </div>
    <ul class="dash-legend">${legend}</ul>`;
  container.classList.remove("muted");
}

function renderKpis(root, data, labels) {
  if (!root) return;
  const openTasks = (data.tasks?.by_status?.pending || 0) + (data.tasks?.by_status?.in_progress || 0);
  const cards = [
    { key: "projects", value: data.projects_count || 0, label: labels.kpiProjects, always: true },
    { key: "pages", value: data.site_index?.total_pages || 0, label: labels.kpiPages, needsProject: true },
    { key: "gap", value: data.product_gap?.missing_count || 0, label: labels.kpiGap, needsProject: true },
    { key: "calendar", value: data.calendar?.items_total || 0, label: labels.kpiCalendar, needsProject: true },
    { key: "campaigns", value: data.calendar?.campaigns || 0, label: labels.kpiCampaigns, needsProject: true },
    { key: "tasks", value: openTasks, label: labels.kpiTasks, needsProject: true },
  ];

  root.innerHTML = cards
    .filter((c) => c.always || data.has_project)
    .map(
      (c) => `<article class="dash-kpi-card">
        <span class="dash-kpi-value" id="kpi-${c.key}">${c.value}</span>
        <span class="dash-kpi-label">${dashEscape(c.label)}</span>
      </article>`
    )
    .join("");
  root.setAttribute("aria-busy", "false");
}

function renderJobs(container, jobs, labels, lang) {
  if (!container) return;
  const list = jobs || [];
  if (!list.length) {
    container.innerHTML = `<p class="muted dash-empty">${dashEscape(labels.noJobs)}</p>`;
    return;
  }
  container.innerHTML = `<ul class="dash-jobs-ul">${list
    .map((job) => {
      const st = job.status || "queued";
      const pct = Number(job.progress) || 0;
      const type = (job.job_type || "").replace(/_/g, " ");
      return `<li class="dash-job-item status-${dashEscape(st)}">
        <div class="dash-job-head">
          <a href="${dashEscape(job.progress_url || "#")}" class="dash-job-link">${dashEscape(type)}</a>
          <span class="dash-job-status">${dashEscape(jobStatusLabel(labels, st))}</span>
        </div>
        <div class="dash-job-meta muted">
          <span>${pct}%</span>
          <span>${dashEscape((job.message || "").slice(0, 80))}</span>
        </div>
        <div class="dash-job-bar" role="presentation"><div style="width:${pct}%"></div></div>
      </li>`;
    })
    .join("")}</ul>`;
  container.classList.remove("muted");
}

async function loadDashboard() {
  const labels = window.DASHBOARD_LABELS || {};
  const lang = getDashLang();
  const slug = getDashProjectSlug();
  const qs = slug ? `?project_slug=${encodeURIComponent(slug)}` : "";

  const kpiRoot = document.getElementById("dash-kpi-grid");
  const tasksChart = document.getElementById("dash-chart-tasks");
  const calChart = document.getElementById("dash-chart-calendar");
  const pagesChart = document.getElementById("dash-chart-pages");
  const jobsRoot = document.getElementById("dash-recent-jobs");

  try {
    const res = await fetch(`/api/v1/dashboard/summary${qs}`, { credentials: "same-origin" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText);

    renderKpis(kpiRoot, data, labels);
    renderBarChart(tasksChart, data.tasks?.by_status, labels, lang);
    renderBarChart(calChart, data.calendar?.by_status, labels, lang);
    renderTypeChart(pagesChart, data.site_index?.by_type, lang);
    renderJobs(jobsRoot, data.recent_jobs, labels, lang);
  } catch (err) {
    if (kpiRoot) {
      kpiRoot.innerHTML = `<p class="result-error">${dashEscape(err.message)}</p>`;
      kpiRoot.setAttribute("aria-busy", "false");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
  document.getElementById("global-project-select")?.addEventListener("change", () => {
    setTimeout(loadDashboard, 300);
  });
});
