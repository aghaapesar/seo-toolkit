/**
 * Seo Toolkit web UI — form handlers and API client.
 */

const I18N = {
  en: { processing: "Processing…", success: "Done", error: "Error", download: "Download" },
  fa: { processing: "در حال پردازش…", success: "انجام شد", error: "خطا", download: "دانلود" },
};

function t(lang, key) {
  return (I18N[lang] || I18N.en)[key] || key;
}

let toastHideTimer = null;

function toast(msg, type = "info", persist = false) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = `toast toast-${type}`;
  el.classList.remove("hidden");
  if (toastHideTimer) clearTimeout(toastHideTimer);
  if (!persist) {
    toastHideTimer = setTimeout(() => el.classList.add("hidden"), type === "error" ? 8000 : 5000);
  }
}

function setIndexDiffProgress(lg, labels, message, active) {
  const panel = document.getElementById("index-diff-progress");
  const text = document.getElementById("index-diff-progress-text");
  const status = document.getElementById("index-status");
  const btn = document.getElementById("index-diff-submit");
  if (panel) panel.classList.toggle("hidden", !active);
  if (text && message) text.textContent = message;
  if (status && message) {
    status.textContent = message;
    status.classList.toggle("muted", !active);
    status.classList.toggle("status-active", active);
  }
  if (btn) {
    btn.disabled = active;
    btn.classList.toggle("is-loading", active);
  }
  if (active && message) {
    toast(message, "info", true);
  }
}

function parseSitemapXmlText(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror")) {
    throw new Error("Invalid sitemap XML");
  }
  const locsIn = (parentLocal) =>
    [...doc.getElementsByTagName("*")]
      .filter((el) => el.localName === parentLocal)
      .map((el) => [...el.children].find((c) => c.localName === "loc")?.textContent?.trim())
      .filter(Boolean);
  return { subSitemaps: locsIn("sitemap"), urls: locsIn("url") };
}

async function fetchTextWithTimeout(url, timeoutMs = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      credentials: "omit",
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } finally {
    clearTimeout(timer);
  }
}

async function expandSitemapInBrowser(entryUrl, onProgress) {
  const visited = new Set();
  const collected = [];

  async function walk(url, depth = 0) {
    const absolute = resolveSitemapUrl(entryUrl, url);
    if (!absolute || visited.has(absolute)) return;
    visited.add(absolute);

    const text = await fetchSitemapText(absolute);
    const parsed = parseSitemapXmlText(text);

    if (parsed.subSitemaps.length) {
      const total = parsed.subSitemaps.length;
      for (let i = 0; i < total; i++) {
        const subUrl = resolveSitemapUrl(absolute, parsed.subSitemaps[i]);
        onProgress?.("sub", i + 1, total, subUrl, depth + 1);
        await walk(subUrl, depth + 1);
      }
    }
    if (parsed.urls.length) {
      collected.push(...parsed.urls);
    }
  }

  onProgress?.("main", entryUrl);
  await walk(entryUrl);
  return [...new Set(collected)];
}

function resolveSitemapUrl(baseUrl, loc) {
  const trimmed = (loc || "").trim();
  if (!trimmed) return "";
  try {
    return new URL(trimmed, baseUrl).href;
  } catch (_) {
    return trimmed;
  }
}

async function fetchSitemapText(url) {
  try {
    return await fetchTextWithTimeout(url, 90000);
  } catch (browserErr) {
    const proxy = `/api/v1/sitemap/proxy?url=${encodeURIComponent(url)}`;
    const res = await fetch(proxy);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data, browserErr.message));
    }
    return data.content || "";
  }
}

function urlsToTxtBlob(urls) {
  return new Blob([urls.join("\n") + "\n"], { type: "text/plain" });
}

/** Turn FastAPI / fetch error payloads into a readable string. */
function formatApiError(data, fallback = "Request failed") {
  const detail = data?.detail ?? data?.message ?? data;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item?.msg) return item.msg;
        return JSON.stringify(item);
      })
      .join(" · ");
  }
  if (typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

function showResult(containerId, html) {
  const box = document.getElementById(containerId);
  if (!box) return;
  box.innerHTML = html;
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function resultCard(lang, data) {
  const rows = Object.entries(data)
    .map(([k, v]) => `<div class="result-row"><span>${k}</span><strong>${v}</strong></div>`)
    .join("");
  return `<div class="result-success"><h4>${t(lang, "success")}</h4>${rows}</div>`;
}

async function postForm(url, form, lang) {
  toast(t(lang, "processing"));
  const res = await fetch(url, { method: "POST", body: new FormData(form) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(data, res.statusText));
  return data;
}

function bindForm(formId, handler) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const lang = document.body.dataset.lang || "fa";
    try {
      await handler(form, lang);
    } catch (err) {
      toast(`${t(lang, "error")}: ${err.message}`, "error");
    }
  });
}

function getActiveProjectSlug() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("project")) return params.get("project");
  const bodySlug = document.body.dataset.activeProject;
  if (bodySlug) return bodySlug;
  const match = document.cookie.match(/(?:^|;\s*)active_project=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function syncProjectSelects() {
  const slug = getActiveProjectSlug();
  if (!slug) return;
  document.querySelectorAll(".project-select, #global-project-select").forEach((sel) => {
    if (sel && sel.value !== slug) sel.value = slug;
  });
}

function setActiveProject(slug) {
  if (slug) {
    document.cookie = `active_project=${encodeURIComponent(slug)};path=/;max-age=31536000`;
  } else {
    document.cookie = "active_project=;path=/;max-age=0";
  }
  const url = new URL(window.location.href);
  if (slug) url.searchParams.set("project", slug);
  else url.searchParams.delete("project");
  window.location.href = url.toString();
}

async function fillProjectFields(slug) {
  if (!slug) return;
  try {
    const res = await fetch(`/api/v1/projects/${slug}`);
    const data = await res.json();
    const byId = {
      "domain-field": data.domain,
      "sitemap-field": data.sitemap_url,
      "project-name-field": data.domain,
      "sitemap-url-field": data.sitemap_url,
    };
    Object.entries(byId).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el && val) el.value = val;
    });
  } catch (_) {}
}

function initProjectSelect() {
  syncProjectSelects();
  document.querySelectorAll(".project-select").forEach((sel) => {
    sel.addEventListener("change", () => {
      if (sel.value) setActiveProject(sel.value);
      else fillProjectFields("");
    });
    if (sel.value) fillProjectFields(sel.value);
  });
}

async function refreshIndexDiffStatus(domain, projectSlug, labels, lg) {
  const statusEl = document.getElementById("index-status");
  const pendingBtn = document.getElementById("mark-pending-btn");
  if (!statusEl || !domain) return;

  const qs = projectSlug ? `?project_slug=${encodeURIComponent(projectSlug)}` : "";
  try {
    const res = await fetch(`/api/v1/index-diff/status/${encodeURIComponent(domain)}${qs}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return;

    const pendingText = data.has_pending_batch
      ? `${data.pending_batch_count} (${data.pending_batch_file || "new_urls"})`
      : labels.indexNoPending || "—";

    statusEl.innerHTML = `
      <div class="result-row"><span>${labels.indexSitemap || "Sitemap"}</span><strong>${data.sitemap_url_count || 0}</strong></div>
      <div class="result-row"><span>${labels.indexSubmitted || "Submitted"}</span><strong>${data.total_submitted || 0}</strong></div>
      <div class="result-row"><span>${labels.indexPending || "Pending"}</span><strong>${pendingText}</strong></div>
      <div class="result-row"><span>${labels.indexLastFetch || "Last fetch"}</span><strong>${data.last_sitemap_fetch ? data.last_sitemap_fetch.slice(0, 16).replace("T", " ") : "—"}</strong></div>`;
    statusEl.classList.remove("muted");

    if (pendingBtn) {
      pendingBtn.disabled = !data.has_pending_batch;
      pendingBtn.title = data.has_pending_batch ? "" : labels.indexNoPending || "";
    }
  } catch (_) {}
}

function indexDiffContext(form) {
  const domain = form?.domain?.value?.trim() || document.getElementById("domain-field")?.value?.trim() || "";
  const projectSlug = form?.project_slug?.value || getActiveProjectSlug() || "";
  return { domain, projectSlug };
}

function initScrapingForm(lang) {
  initProjectSelect();
  bindForm("form-scraping", async (form, lg) => {
    const data = await postForm("/api/v1/scraping", form, lg);
    showResult(
      "result-scraping",
      resultCard(lg, {
        URLs: data.url_count,
        File: data.output_file,
        Test: data.test_mode ? "yes" : "no",
      })
    );
    toast(t(lg, "success"), "success");
  });
}

function initLinkingForm(lang) {
  initProjectSelect();
  bindForm("form-linking", async (form, lg) => {
    const data = await postForm("/api/v1/linking", form, lg);
    showResult("result-linking", resultCard(lg, { File: data.output_file, Sitemap: data.sitemap_url_count }));
    toast(t(lg, "success"), "success");
  });
}

function initSynonymsForm(lang) {
  initProjectSelect();
  bindForm("form-synonyms", async (form, lg) => {
    const data = await postForm("/api/v1/synonyms", form, lg);
    showResult("result-synonyms", resultCard(lg, { File: data.output_file, Model: data.model }));
    toast(t(lg, "success"), "success");
  });
}

function initProjectsPage(lang) {
  bindForm("form-create-project", async (form, lg) => {
    const data = await postForm("/api/v1/projects/form", form, lg);
    showResult(
      "result-project",
      resultCard(lg, { slug: data.slug, name: data.name, domain: data.domain })
    );
    toast(t(lg, "success"), "success");
    setTimeout(() => setActiveProject(data.slug), 600);
  });
  document.querySelectorAll(".set-project").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      setActiveProject(btn.dataset.slug);
    });
  });
}

async function tryFetchSitemapInBrowser(url) {
  const urls = await expandSitemapInBrowser(url);
  if (!urls.length) throw new Error("No URLs in sitemap");
  return urlsToTxtBlob(urls);
}

async function runIndexDiffLegacy(form, lg, importLabels, sitemapUrl, hasFile, sitemapFile) {
  const fd = new FormData();
  fd.append("domain", form.domain.value);
  fd.append("mark_submitted", form.mark_submitted.checked ? "true" : "false");
  if (form.project_slug?.value) {
    fd.append("project_slug", form.project_slug.value);
  }

  if (hasFile) {
    fd.append("sitemap_file", sitemapFile.files[0]);
    fd.append("sitemap_url", sitemapUrl);
  } else if (sitemapUrl) {
    setIndexDiffProgress(
      lg,
      importLabels,
      importLabels.statusFetching || (lg === "fa" ? "دریافت sitemap…" : "Fetching sitemap…"),
      true
    );
    try {
      const urls = await expandSitemapInBrowser(sitemapUrl, (kind, idx, total, subUrl, depth) => {
        if (kind === "main") return;
        const base = importLabels.statusSub || (lg === "fa" ? "sub-sitemap" : "Sub-sitemap");
        const depthLabel = depth > 1 ? ` L${depth}` : "";
        const shortName = subUrl ? subUrl.split("/").pop() : "";
        setIndexDiffProgress(lg, importLabels, `${base} ${idx}/${total}${depthLabel}: ${shortName}…`, true);
      });
      fd.append("urls_file", urlsToTxtBlob(urls), "sitemap_urls.txt");
      fd.append("sitemap_url", "");
    } catch (browserErr) {
      console.warn("Browser sitemap fetch failed, trying server:", browserErr);
      fd.append("sitemap_url", sitemapUrl);
    }
  }

  setIndexDiffProgress(
    lg,
    importLabels,
    importLabels.statusServer || (lg === "fa" ? "مقایسه روی سرور…" : "Comparing on server…"),
    true
  );

  let res = await fetch("/api/v1/index-diff/diff-form", { method: "POST", body: fd });
  if (res.status === 404 && sitemapUrl && !hasFile) {
    res = await fetch("/api/v1/index-diff/diff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        domain: form.domain.value,
        sitemap_url: sitemapUrl,
        mark_submitted: form.mark_submitted.checked,
        project_slug: form.project_slug?.value || null,
      }),
    });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(data, res.statusText));

  const doneMsg =
    lg === "fa"
      ? `انجام شد — ${data.total} URL، ${data.new_count} جدید، ${data.already_count} قبلی`
      : `Done — ${data.total} URLs, ${data.new_count} new, ${data.already_count} submitted`;

  setIndexDiffProgress(lg, importLabels, doneMsg, false);
  showResult(
    "result-index-diff",
    resultCard(lg, {
      [lg === "fa" ? "مجموع" : "Total"]: data.total,
      [lg === "fa" ? "جدید" : "New"]: data.new_count,
      [lg === "fa" ? "قبلی" : "Submitted"]: data.already_count,
      "new.txt": data.new_file,
      "done.txt": data.already_file,
    })
  );
  toast(doneMsg, "success");
  const { domain, projectSlug } = indexDiffContext(form);
  await refreshIndexDiffStatus(domain, projectSlug, importLabels, lg);
}

function initIndexDiffForm(lang, importLabels = {}) {
  initProjectSelect();

  const mainForm = document.getElementById("form-index-diff");
  const refreshStatus = () => {
    const lg = document.body.dataset.lang || lang || "fa";
    const { domain, projectSlug } = indexDiffContext(mainForm);
    if (domain) refreshIndexDiffStatus(domain, projectSlug, importLabels, lg);
  };
  mainForm?.domain?.addEventListener("change", refreshStatus);
  mainForm?.domain?.addEventListener("blur", refreshStatus);
  document.querySelectorAll(".project-select").forEach((sel) => {
    sel.addEventListener("change", () => setTimeout(refreshStatus, 300));
  });
  refreshStatus();

  const fileInput = document.getElementById("import-txt-files");
  const fileHint = document.getElementById("import-file-hint");
  if (fileInput && fileHint) {
    fileInput.addEventListener("change", () => {
      const count = fileInput.files?.length || 0;
      if (count === 0) {
        fileHint.textContent = importLabels.importHint || "";
      } else {
        const label = importLabels.filesSelected || "file(s) selected";
        fileHint.textContent = `${count} ${label}`;
      }
    });
  }

  bindForm("form-index-diff", async (form, lg) => {
    const sitemapUrl = form.sitemap_url?.value?.trim() || "";
    const sitemapFile = document.getElementById("sitemap-file-field");
    const hasFile = sitemapFile?.files?.length > 0;
    if (!sitemapUrl && !hasFile) {
      throw new Error(
        importLabels.sitemapRequired ||
          (lg === "fa" ? "آدرس sitemap یا فایل sitemap.xml را وارد کنید" : "Enter sitemap URL or upload sitemap.xml")
      );
    }

    const fd = new FormData();
    fd.append("domain", form.domain.value);
    fd.append("mark_submitted", form.mark_submitted.checked ? "true" : "false");
    if (form.project_slug?.value) {
      fd.append("project_slug", form.project_slug.value);
    }
    if (hasFile) {
      fd.append("sitemap_file", sitemapFile.files[0]);
      fd.append("sitemap_url", sitemapUrl);
    } else {
      fd.append("sitemap_url", sitemapUrl);
    }

    setIndexDiffProgress(
      lg,
      importLabels,
      importLabels.statusStarting || (lg === "fa" ? "شروع پردازش…" : "Starting…"),
      true
    );

    const res = await fetch("/api/v1/jobs/index-diff/start", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));

    if (res.status === 404) {
      const restartHint =
        lg === "fa"
          ? "سرور قدیمی است — برای صفحه پیشرفت: ./scripts/run_web.sh"
          : "Stale server — run ./scripts/run_web.sh for the progress page";
      toast(restartHint, "info", true);
      await runIndexDiffLegacy(form, lg, importLabels, sitemapUrl, hasFile, sitemapFile);
      return;
    }

    if (!res.ok) throw new Error(formatApiError(data, res.statusText));

    const qs = new URLSearchParams({ lang: lg });
    if (form.project_slug?.value) qs.set("project", form.project_slug.value);
    window.location.href = `/tasks/${data.job_id}?${qs}`;
  });

  bindForm("form-index-import", async (form, lg) => {
    const main = document.getElementById("form-index-diff");
    const domainInput = document.getElementById("import_domain");
    const fileInputEl = document.getElementById("import-txt-files");
    if (main?.domain?.value && domainInput) {
      domainInput.value = main.domain.value;
    }
    if (!domainInput?.value) {
      throw new Error(lg === "fa" ? "ابتدا دامنه را وارد کنید" : "Enter domain first");
    }
    if (!fileInputEl?.files?.length) {
      throw new Error(importLabels.noFiles || (lg === "fa" ? "حداقل یک فایل txt انتخاب کنید" : "Select at least one .txt file"));
    }
    const markSubmitted = document.getElementById("import-mark-submitted")?.checked ?? true;
    const fd = new FormData();
    fd.append("domain", domainInput.value);
    fd.append("mark_submitted", markSubmitted ? "true" : "false");
    for (const file of fileInputEl.files) {
      fd.append("urls_files", file);
    }
    if (main?.project_slug?.value) {
      fd.append("project_slug", main.project_slug.value);
    }
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/index-diff/import", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(formatApiError(data, res.statusText));

    const countLabel = data.mark_submitted
      ? importLabels.totalAdded || "Total new URLs"
      : importLabels.importParsed || "URLs parsed";
    const countValue = data.mark_submitted ? data.added : data.parsed;

    const fileRows = (data.files || [])
      .map((f) => {
        const err = f.error ? ` — ${f.error}` : "";
        const n = data.mark_submitted ? f.added : f.parsed;
        return `<div class="result-row"><span>${f.name}</span><strong>${n}${err}</strong></div>`;
      })
      .join("");

    showResult(
      "result-index-import",
      `<div class="result-success">
        <h4>${t(lg, "success")}</h4>
        <div class="result-row"><span>${countLabel}</span><strong>${countValue}</strong></div>
        <div class="result-row"><span>${importLabels.filesProcessed || "Files processed"}</span><strong>${data.files_processed}</strong></div>
        ${fileRows}
      </div>`
    );
    toast(`${t(lg, "success")}: ${countValue}`, "success");
    await refreshIndexDiffStatus(domainInput.value, main?.project_slug?.value || getActiveProjectSlug(), importLabels, lg);
  });

  const markForm = document.getElementById("form-mark-batch");
  if (markForm) {
    markForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const lg = document.body.dataset.lang || lang || "fa";
      try {
        const main = document.getElementById("form-index-diff");
        const domainInput = document.getElementById("mark_batch_domain");
        if (main?.domain?.value && domainInput) {
          domainInput.value = main.domain.value;
        }
        if (!domainInput?.value) {
          throw new Error(lg === "fa" ? "ابتدا دامنه را وارد کنید" : "Enter domain first");
        }

        const action = e.submitter?.value || "pending";
        const batchFile = document.getElementById("mark-batch-file");
        const fd = new FormData();
        fd.append("domain", domainInput.value);
        if (main?.project_slug?.value) {
          fd.append("project_slug", main.project_slug.value);
        }

        if (action === "upload") {
          if (!batchFile?.files?.length) {
            throw new Error(lg === "fa" ? "فایل txt را انتخاب کنید" : "Select a txt file");
          }
          fd.append("use_pending", "false");
          fd.append("batch_file", batchFile.files[0]);
        } else {
          fd.append("use_pending", "true");
        }

        toast(t(lg, "processing"));
        const res = await fetch("/api/v1/index-diff/mark-batch", { method: "POST", body: fd });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(formatApiError(data, res.statusText));

        showResult(
          "result-mark-batch",
          resultCard(lg, {
            batch_id: data.batch_id,
            submitted: data.status?.total_submitted,
          })
        );
        toast(t(lg, "success"), "success");
        if (batchFile) batchFile.value = "";
        await refreshIndexDiffStatus(
          domainInput.value,
          main?.project_slug?.value || getActiveProjectSlug(),
          importLabels,
          lg
        );
      } catch (err) {
        toast(`${t(lg, "error")}: ${err.message}`, "error");
      }
    });
  }
}

function initContentForm(lang) {
  initProjectSelect();
  bindForm("form-content", async (form, lg) => {
    const fd = new FormData(form);
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/content/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(formatApiError(data, res.statusText));
    showResult(
      "result-content",
      `<div class="result-success">
        <h4>${t(lg, "success")}</h4>
        <p>${data.message}</p>
        <pre class="cli-box">${data.cli}</pre>
        <p><strong>File:</strong> ${data.saved_path}</p>
      </div>`
    );
    toast(t(lg, "success"), "success");
  });
}

function initGenerationForm(lang) {
  initProjectSelect();
  bindForm("form-generation", async (form, lg) => {
    const fd = new FormData(form);
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/generation/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(formatApiError(data, res.statusText));
    showResult(
      "result-generation",
      `<div class="result-success"><pre class="cli-box">${data.cli}</pre><p>${data.message}</p></div>`
    );
  });
}

// Sticky project + language links on load
document.addEventListener("DOMContentLoaded", () => {
  syncProjectSelects();
});

// Persist language preference
document.querySelectorAll(".lang-switch a").forEach((a) => {
  a.addEventListener("click", () => {
    const lang = a.getAttribute("href").replace("?lang=", "");
    document.cookie = `lang=${lang};path=/;max-age=31536000`;
  });
});
