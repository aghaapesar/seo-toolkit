/**
 * Task progress page — polls background jobs and runs browser sitemap expansion.
 */

async function reportJobProgress(jobId, progress, message, step) {
  await fetch(`/api/v1/jobs/${jobId}/progress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ progress, message, step }),
  });
}

function setTaskUi(labels, job) {
  const fill = document.getElementById("task-progress-fill");
  const track = document.getElementById("task-progress-track");
  const percentEl = document.getElementById("task-progress-percent");
  const messageEl = document.getElementById("task-progress-message");
  const badge = document.getElementById("task-status-badge");
  const stepsEl = document.getElementById("task-steps");

  const pct = job.progress || 0;
  if (fill) fill.style.width = `${pct}%`;
  if (track) track.setAttribute("aria-valuenow", String(pct));
  if (percentEl) percentEl.textContent = `${pct}%`;
  if (messageEl) messageEl.textContent = job.message || labels.pending;

  if (badge) {
    badge.dataset.status = job.status;
    const statusLabels = {
      waiting_client: labels.waiting,
      queued: labels.pending,
      running: labels.running,
      paused: labels.paused || "Paused",
      completed: labels.completed,
      failed: labels.failed,
    };
    badge.textContent = statusLabels[job.status] || job.status;
  }

  if (job.credit_exhausted && typeof toast === "function") {
    window.__creditNotifiedJobs = window.__creditNotifiedJobs || new Set();
    if (!window.__creditNotifiedJobs.has(job.id)) {
      window.__creditNotifiedJobs.add(job.id);
      toast(job.credit_message || labels.creditExhausted || "Recharge AI credits", "error");
    }
  }

  updateSiteIndexControls(labels, job);

  if (stepsEl && job.steps?.length) {
    stepsEl.innerHTML = job.steps
      .map((s) => `<li>${s.label}${s.progress != null ? ` <span class="muted">(${s.progress}%)</span>` : ""}</li>`)
      .join("");
    stepsEl.scrollTop = stepsEl.scrollHeight;
  }
}

function renderLiveSitemapSources(sources, labels, rootUrl) {
  const box = document.getElementById("task-sitemap-view");
  if (!box) return;

  const sourceUrls = sources?.length ? sources : rootUrl ? [rootUrl] : [];
  if (!sourceUrls.length) return;

  const items = sourceUrls
    .map(
      (u, i) =>
        `<li><a href="${u}" target="_blank" rel="noopener">${i === 0 ? labels.sitemapRoot || "Root" : labels.sitemapSub || "Sub"} ${i + 1}</a><span class="muted sitemap-src">${u}</span></li>`
    )
    .join("");

  box.innerHTML = `
    <h3>${labels.sitemapSourcesList || "Fetched sitemap XML files"}</h3>
    <p class="muted">${labels.sitemapFetchingLive || "Fetching…"} (${sourceUrls.length})</p>
    <ol class="sitemap-sources-list">${items}</ol>`;
  box.classList.remove("hidden");
}

async function loadTaskSitemapView(job, labels) {
  const box = document.getElementById("task-sitemap-view");
  if (!box || !job.params?.domain) return;

  const lg = document.body.dataset.lang || "fa";
  const projectSlug = job.params.project_slug || "";
  const qs = projectSlug ? `?project_slug=${encodeURIComponent(projectSlug)}` : "";
  try {
    const res = await fetch(`/api/v1/index-diff/sitemap-view/${encodeURIComponent(job.params.domain)}${qs}`);
    const view = await res.json().catch(() => ({}));
    if (res.ok && typeof renderSitemapViewPanel === "function") {
      box.innerHTML = `<h3>${labels.sitemapFetchedTitle || "Sitemap fetched"}</h3>${renderSitemapViewPanel(view, labels, lg)}`;
      box.classList.remove("hidden");
    }
  } catch (err) {
    console.warn("loadTaskSitemapView failed:", err);
  }
}

const TASK_TOOL_BACK_LABELS = {
  index_diff: "backToToolIndexDiff",
  content_cluster: "backToToolContentCluster",
  content_audit: "backToToolContentAudit",
  site_index: "backToToolSiteIndex",
  knowledge_export: "backToToolKnowledgeExport",
  technical_audit: "backToToolTechnicalAudit",
};

function updateSiteIndexControls(labels, job) {
  if (job.job_type !== "site_index") return;
  let box = document.getElementById("task-index-controls");
  const panel = document.querySelector(".task-panel");
  if (!box && panel) {
    box = document.createElement("div");
    box.id = "task-index-controls";
    box.className = "task-actions";
    const anchor = document.getElementById("task-result");
    if (anchor) panel.insertBefore(box, anchor);
    else panel.appendChild(box);
  }
  if (!box) return;

  if (job.status === "running") {
    box.innerHTML = `<button type="button" class="btn btn-ghost" id="btn-pause-index">${labels.pauseIndex || "Pause"}</button>`;
    document.getElementById("btn-pause-index")?.addEventListener("click", async () => {
      await fetch(`/api/v1/site-index/pause/${job.id}`, { method: "POST" });
      toast(labels.pauseRequested || "Pause requested…", "success");
    }, { once: true });
  } else if (job.status === "paused") {
    const slug = job.params?.project_slug || "";
    const runId = job.result?.run_id || job.params?.run_id || "";
    box.innerHTML = `<button type="button" class="btn btn-primary" id="btn-resume-index">${labels.resumeIndex || "Resume"}</button>`;
    document.getElementById("btn-resume-index")?.addEventListener("click", async () => {
      const fd = new FormData();
      fd.set("project_slug", slug);
      if (runId) fd.set("run_id", runId);
      const res = await fetch("/api/v1/site-index/resume", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(`${labels.error}: ${data.detail || res.statusText}`, "error");
        return;
      }
      window.location.href = `/tasks/${data.job_id}?lang=${document.body.dataset.lang || "fa"}&project=${encodeURIComponent(slug)}`;
    }, { once: true });
  } else {
    box.innerHTML = "";
  }
}

function escapeTaskHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderAuditDiffs(diffs, lang) {
  if (!diffs?.length) return `<p class="muted">${lang === "fa" ? "هم‌خوان با برنامه" : "Matches plan"}</p>`;
  return `<ul class="audit-diff-list">${diffs
    .map(
      (d) =>
        `<li><strong>${escapeTaskHtml(d.field)}</strong><br/>
        <span class="muted">${lang === "fa" ? "برنامه" : "Plan"}:</span> ${escapeTaskHtml(d.planned || "—")}<br/>
        <span class="muted">${lang === "fa" ? "زنده" : "Live"}:</span> ${escapeTaskHtml(d.live || "—")}</li>`
    )
    .join("")}</ul>`;
}

function renderAuditSuggestions(r, labels, lang) {
  const suggestions = r.suggestions || [];
  if (!suggestions.length) {
    return `<p class="muted">${labels.auditNoMatch || labels.audit_no_match || ""}</p>`;
  }
  return suggestions
    .map((s, idx) => {
      const msg = lang === "fa" ? s.message_fa : s.message_en;
      return `
      <article class="audit-suggestion-card" data-audit-idx="${idx}">
        <h4>${escapeTaskHtml(s.item_title || "—")}</h4>
        <p class="muted"><a href="${escapeTaskHtml(s.page_url)}" target="_blank" rel="noopener">${escapeTaskHtml(s.page_url)}</a></p>
        <p>${escapeTaskHtml(msg || "")}</p>
        ${renderAuditDiffs(s.diffs, lang)}
        <div class="audit-suggestion-actions">
          <button type="button" class="btn btn-primary btn-sm btn-audit-apply" data-idx="${idx}">${labels.auditApply || "Apply"}</button>
          <button type="button" class="btn btn-ghost btn-sm btn-audit-apply-live" data-idx="${idx}">${labels.auditApplyLive || "Adopt live"}</button>
        </div>
      </article>`;
    })
    .join("");
}

async function applyAuditSuggestion(suggestion, adoptLive, labels) {
  const res = await fetch("/api/v1/content-audit/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_id: suggestion.item_id,
      page_url: suggestion.page_url,
      scrape_snapshot: suggestion.scrape_snapshot || {},
      adopt_live_fields: adoptLive,
      set_status_review: true,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  toast(labels.doneTitle || "Done", "success");
  return data.item;
}

function bindAuditSuggestionButtons(r, labels, lang) {
  const suggestions = r.suggestions || [];
  document.querySelectorAll(".btn-audit-apply").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const s = suggestions[Number(btn.dataset.idx)];
      if (!s) return;
      btn.disabled = true;
      try {
        await applyAuditSuggestion(s, false, labels);
        btn.closest(".audit-suggestion-card")?.classList.add("applied");
      } catch (err) {
        toast(`${labels.error}: ${err.message}`, "error");
        btn.disabled = false;
      }
    });
  });
  document.querySelectorAll(".btn-audit-apply-live").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const s = suggestions[Number(btn.dataset.idx)];
      if (!s) return;
      btn.disabled = true;
      try {
        await applyAuditSuggestion(s, true, labels);
        btn.closest(".audit-suggestion-card")?.classList.add("applied");
      } catch (err) {
        toast(`${labels.error}: ${err.message}`, "error");
        btn.disabled = false;
      }
    });
  });
  document.getElementById("btn-audit-apply-all")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-audit-apply-all");
    btn.disabled = true;
    try {
      const res = await fetch("/api/v1/content-audit/apply-bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          suggestions: suggestions.map((s) => ({
            item_id: s.item_id,
            page_url: s.page_url,
            scrape_snapshot: s.scrape_snapshot || {},
          })),
          adopt_live_fields: false,
          set_status_review: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      document.querySelectorAll(".audit-suggestion-card").forEach((c) => c.classList.add("applied"));
      toast(labels.doneTitle || "Done", "success");
    } catch (err) {
      toast(`${labels.error}: ${err.message}`, "error");
      btn.disabled = false;
    }
  });
}

function applyTaskBackLink(job, labels) {
  const link = document.getElementById("task-back-link");
  const routes = window.TASK_TOOL_ROUTES || {};
  if (!link || !job?.job_type || !routes[job.job_type]) return;
  const lg = document.body.dataset.lang || "fa";
  const project = job.params?.project_slug || "";
  const qs = new URLSearchParams({ lang: lg });
  if (project) qs.set("project", project);
  link.href = `${routes[job.job_type]}?${qs}`;
  const labelKey = TASK_TOOL_BACK_LABELS[job.job_type];
  if (labelKey && labels[labelKey]) link.textContent = labels[labelKey];
}

function showTaskResult(labels, job) {
  const box = document.getElementById("task-result");
  const title = document.getElementById("task-title");
  const exportsBox = document.getElementById("task-export-files");
  if (!box || !job.result) return;

  const r = job.result;
  const lg = document.body.dataset.lang || "fa";
  const downloadLabel = typeof t === "function" ? t(lg, "download") : "Download";
  const isCluster = job.job_type === "content_cluster";
  const isAudit = job.job_type === "content_audit";
  const isIndex = job.job_type === "site_index";
  const isKnowledge = job.job_type === "knowledge_export";
  const isTechAudit = job.job_type === "technical_audit";
  const doneMsg = isCluster
    ? labels.doneMessageCluster || labels.doneMessage
    : isAudit
      ? labels.doneMessageAudit || labels.doneMessage
      : isIndex
        ? labels.doneMessageSiteIndex || labels.doneMessage
        : isKnowledge
          ? labels.doneMessageKnowledgeExport || labels.doneMessage
          : isTechAudit
            ? labels.doneMessageTechnicalAudit || labels.doneMessage
            : labels.doneMessageIndexDiff || labels.doneMessage;

  if (title) title.textContent = labels.doneTitle;
  box.innerHTML = `
    <div class="result-success task-done-card">
      <h4>${labels.doneTitle}</h4>
      <p class="task-done-msg">${doneMsg}</p>
      ${isAudit ? `
      <div class="result-row"><span>${labels.auditScraped || "Scraped"}</span><strong>${r.scraped_ok || 0} / ${r.url_count || 0}</strong></div>
      <div class="result-row"><span>${labels.auditMatches || "Matches"}</span><strong>${r.match_count || 0}</strong></div>
      <div class="result-row"><span>${labels.auditUpdates || "Updates"}</span><strong>${r.update_count || 0}</strong></div>
      ` : isIndex ? `
      <div class="result-row"><span>${labels.indexProcessed || "Indexed"}</span><strong>${r.processed_count || 0} / ${r.total_urls || 0}</strong></div>
      <div class="result-row"><span>${labels.indexSuccess || "OK"}</span><strong>${r.success_count || 0}</strong></div>
      ${r.paused ? `<p class="muted">${labels.indexPausedHint || ""}</p>` : ""}
      ` : isKnowledge ? `
      <div class="result-row"><span>${labels.keTotal || "Total"}</span><strong>${r.total_urls || 0}</strong></div>
      <div class="result-row"><span>${labels.keSuccess || "OK"}</span><strong>${r.success || 0}</strong></div>
      <div class="result-row"><span>${labels.keFailed || "Failed"}</span><strong>${r.failed || 0}</strong></div>
      <div class="result-row"><span>${labels.keDuplicate || "Duplicate"}</span><strong>${r.duplicate || 0}</strong></div>
      <div class="result-row"><span>${labels.keParts || "Parts"}</span><strong>${r.parts || 0}</strong></div>
      ` : isCluster ? `
      <div class="result-row"><span>${labels.clusterCount || "Clusters"}</span><strong>${r.cluster_count || 0}</strong></div>
      <div class="result-row"><span>${labels.calendarPosts || "Calendar posts"}</span><strong>${r.calendar_summary?.total_posts || 0}</strong></div>
      <div class="result-row"><span>${labels.calendarStart || "Start"}</span><strong>${r.calendar_summary?.start_date || "—"}</strong></div>
      ` : isTechAudit ? `
      <div class="result-row"><span>${labels.technicalAuditScore || "Score"}</span><strong>${r.score ?? "—"} / 100</strong></div>
      <div class="result-row"><span>Pages</span><strong>${r.pages_ok || 0} / ${r.pages_checked || 0}</strong></div>
      <div class="result-row"><span>Issues</span><strong>${(r.issues || []).length}</strong></div>
      ` : `
      <div class="result-row"><span>${labels.total}</span><strong>${r.total}</strong></div>
      <div class="result-row"><span>${labels.newUrls}</span><strong>${r.new_count}</strong></div>
      <div class="result-row"><span>${labels.already}</span><strong>${r.already_count}</strong></div>
      `}
    </div>`;
  box.classList.remove("hidden");

  const viewBox = document.getElementById("task-sitemap-view");
  if (viewBox) {
    if (isCluster || isAudit || isIndex || isKnowledge || isTechAudit) {
      viewBox.classList.add("hidden");
    } else if (r.sitemap_view && typeof renderSitemapViewPanel === "function") {
      viewBox.innerHTML = `<h3>${labels.sitemapFetchedTitle || "Sitemap fetched"}</h3>${renderSitemapViewPanel(r.sitemap_view, labels, lg)}`;
      viewBox.classList.remove("hidden");
    } else {
      loadTaskSitemapView(job, labels);
    }
  }

  if (exportsBox && r.files?.length && typeof renderDownloadFiles === "function") {
    exportsBox.innerHTML = `
      <h3>${labels.filesTitle || "Download files"}</h3>
      <p class="muted">${labels.filesHint || ""}</p>
      ${renderDownloadFiles(r.files, downloadLabel)}`;
    exportsBox.classList.remove("hidden");
  } else if (exportsBox && isAudit && r.suggestions) {
    const calQs = new URLSearchParams({ lang: lg });
    if (r.project_slug) calQs.set("project", r.project_slug);
    if (r.campaign_id) calQs.set("campaign_id", r.campaign_id);
    exportsBox.innerHTML = `
      <h3>${labels.auditMatches || "Matches"}</h3>
      <p class="task-actions" style="margin-bottom:1rem;">
        <button type="button" class="btn btn-ghost btn-sm" id="btn-audit-apply-all">${labels.auditApplyAll || "Apply all"}</button>
        <a class="btn btn-ghost btn-sm" href="/tools/content-cluster/calendar?${calQs}">${labels.openCalendarBoard || "Calendar"}</a>
      </p>
      <div class="audit-suggestions-list">${renderAuditSuggestions(r, labels, lg)}</div>
      ${(r.unmatched_items || []).length ? `<h4 class="muted">${labels.auditUnmatchedItems || ""}</h4><ul class="audit-mini-list">${r.unmatched_items.slice(0, 15).map((i) => `<li>${escapeTaskHtml(i.title)}</li>`).join("")}</ul>` : ""}
      ${(r.unmatched_pages || []).length ? `<h4 class="muted">${labels.auditUnmatchedPages || ""}</h4><ul class="audit-mini-list">${r.unmatched_pages.slice(0, 10).map((p) => `<li><a href="${escapeTaskHtml(p.url)}" target="_blank" rel="noopener">${escapeTaskHtml(p.title || p.url)}</a></li>`).join("")}</ul>` : ""}`;
    exportsBox.classList.remove("hidden");
    bindAuditSuggestionButtons(r, labels, lg);
  } else if (exportsBox && r.output_file) {
    const dlUrl = `/api/v1/content-cluster/download?path=${encodeURIComponent(r.output_file)}`;
    const boardUrl = r.calendar_board_url || (r.board_id ? `/tools/content-cluster/calendar?board_id=${r.board_id}` : "");
    const openBoard = labels.openCalendarBoard || "Open calendar board";
    const boardHref = boardUrl ? `${boardUrl}${boardUrl.includes("?") ? "&" : "?"}lang=${lg}` : "";
    exportsBox.innerHTML = `
      <h3>${labels.filesTitle || "Download files"}</h3>
      <p class="muted">${labels.filesHint || ""}</p>
      <p><a class="btn btn-primary" href="${dlUrl}">${downloadLabel}: content_calendar.xlsx</a></p>
      ${boardHref ? `<p><a class="btn btn-ghost" href="${boardHref}">${openBoard}</a></p>` : ""}
      <p class="muted">${labels.clusterCount || "Clusters"}: ${r.cluster_count || 0} · ${labels.calendarPosts || "Posts"}: ${r.calendar_summary?.total_posts || 0}</p>`;
    exportsBox.classList.remove("hidden");
  }

  toast(labels.doneTitle, "success");
}

function showTaskError(labels, message) {
  const box = document.getElementById("task-error");
  if (!box) return;
  box.innerHTML = `<div class="result-error"><h4>${labels.error}</h4><p>${message}</p></div>`;
  box.classList.remove("hidden");
  toast(`${labels.error}: ${message}`, "error");
}

async function runClientSitemapPhase(jobId, sitemapUrl, labels) {
  const liveSources = [];

  const expanded = await expandSitemapInBrowser(sitemapUrl, (kind, a, b, subUrl, depth) => {
    if (kind === "main") {
      liveSources.push(sitemapUrl);
      renderLiveSitemapSources(liveSources, labels, sitemapUrl);
      reportJobProgress(jobId, 10, labels.fetchingMain, "fetch_root");
      return;
    }
    const subIndex = a;
    const subTotal = b;
    if (subUrl && !liveSources.includes(subUrl)) {
      liveSources.push(subUrl);
      renderLiveSitemapSources(liveSources, labels, sitemapUrl);
    }
    const depthLabel = depth > 1 ? ` (level ${depth})` : "";
    const shortUrl = subUrl ? subUrl.split("/").pop() : "";
    const msg = `${labels.fetchingSub} ${subIndex}/${subTotal}${depthLabel}: ${shortUrl}`;
    const pct = 10 + Math.floor((subIndex / Math.max(subTotal, 1)) * 35);
    reportJobProgress(jobId, pct, msg, `fetch_sub_${subIndex}`);
  });

  if (!expanded.urls.length) {
    throw new Error(labels.noUrls);
  }

  renderLiveSitemapSources(expanded.sources || liveSources, labels, sitemapUrl);

  await reportJobProgress(
    jobId,
    48,
    `${labels.fetchingSub} — ${expanded.urls.length} URLs`,
    "urls_collected"
  );

  const fd = new FormData();
  fd.append("urls_file", urlsToTxtBlob(expanded.urls), "sitemap_urls.txt");
  fd.append("sitemap_sources", JSON.stringify(expanded.sources || []));
  const res = await fetch(`/api/v1/jobs/${jobId}/supply-urls`, { method: "POST", body: fd });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(data, res.statusText));
  return data;
}

async function pollJob(jobId, labels) {
  const res = await fetch(`/api/v1/jobs/${jobId}`);
  const job = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(job, "Job not found"));
  return job;
}

async function initTaskPage() {
  const page = document.getElementById("task-page");
  if (!page) return;

  const jobId = page.dataset.jobId;
  const labels = window.TASK_LABELS || {};
  let clientPhaseDone = false;

  const tick = async () => {
    try {
      let job = await pollJob(jobId, labels);
      applyTaskBackLink(job, labels);
      setTaskUi(labels, job);

      if (job.status === "waiting_client" && !clientPhaseDone && job.params?.sitemap_url) {
        clientPhaseDone = true;
        try {
          job = await runClientSitemapPhase(jobId, job.params.sitemap_url, labels);
          setTaskUi(labels, job);
        } catch (err) {
          showTaskError(labels, err.message);
          return;
        }
      }

      if (job.status === "completed" || job.status === "paused") {
        showTaskResult(labels, job);
        if (job.status === "paused") {
          setTimeout(tick, 2000);
        }
        return;
      }
      if (job.status === "failed") {
        showTaskError(labels, job.error || labels.error);
        return;
      }

      setTimeout(tick, 600);
    } catch (err) {
      showTaskError(labels, err.message);
    }
  };

  tick();
}

document.addEventListener("DOMContentLoaded", initTaskPage);
