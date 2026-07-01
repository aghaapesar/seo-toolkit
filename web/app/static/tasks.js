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
      completed: labels.completed,
      failed: labels.failed,
    };
    badge.textContent = statusLabels[job.status] || job.status;
  }

  if (stepsEl && job.steps?.length) {
    stepsEl.innerHTML = job.steps
      .map((s) => `<li>${s.label}${s.progress != null ? ` <span class="muted">(${s.progress}%)</span>` : ""}</li>`)
      .join("");
    stepsEl.scrollTop = stepsEl.scrollHeight;
  }
}

function showTaskResult(labels, job) {
  const box = document.getElementById("task-result");
  const title = document.getElementById("task-title");
  const exportsBox = document.getElementById("task-export-files");
  if (!box || !job.result) return;

  const r = job.result;
  const lg = document.body.dataset.lang || "fa";
  const downloadLabel = typeof t === "function" ? t(lg, "download") : "Download";

  if (title) title.textContent = labels.doneTitle;
  box.innerHTML = `
    <div class="result-success task-done-card">
      <h4>${labels.doneTitle}</h4>
      <p class="task-done-msg">${labels.doneMessage}</p>
      <div class="result-row"><span>${labels.total}</span><strong>${r.total}</strong></div>
      <div class="result-row"><span>${labels.newUrls}</span><strong>${r.new_count}</strong></div>
      <div class="result-row"><span>${labels.already}</span><strong>${r.already_count}</strong></div>
    </div>`;
  box.classList.remove("hidden");

  if (exportsBox && r.files?.length && typeof renderDownloadFiles === "function") {
    exportsBox.innerHTML = `
      <h3>${labels.filesTitle || "Download files"}</h3>
      <p class="muted">${labels.filesHint || ""}</p>
      ${renderDownloadFiles(r.files, downloadLabel)}`;
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
  const expanded = await expandSitemapInBrowser(sitemapUrl, (kind, a, b, subUrl, depth) => {
    if (kind === "main") {
      reportJobProgress(jobId, 10, labels.fetchingMain, "fetch_root");
      return;
    }
    const subIndex = a;
    const subTotal = b;
    const depthLabel = depth > 1 ? ` (level ${depth})` : "";
    const shortUrl = subUrl ? subUrl.split("/").pop() : "";
    const msg = `${labels.fetchingSub} ${subIndex}/${subTotal}${depthLabel}: ${shortUrl}`;
    const pct = 10 + Math.floor((subIndex / Math.max(subTotal, 1)) * 35);
    reportJobProgress(jobId, pct, msg, `fetch_sub_${subIndex}`);
  });

  if (!expanded.urls.length) {
    throw new Error(labels.noUrls);
  }

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

      if (job.status === "completed") {
        showTaskResult(labels, job);
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
