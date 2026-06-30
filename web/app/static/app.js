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

function toast(msg, type = "info") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = `toast toast-${type}`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 4000);
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
  if (!res.ok) throw new Error(data.detail || res.statusText);
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
  document.querySelectorAll(".project-select").forEach((sel) => {
    sel.addEventListener("change", () => fillProjectFields(sel.value));
    if (sel.value) fillProjectFields(sel.value);
  });
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

function initIndexDiffForm(lang) {
  initProjectSelect();
  bindForm("form-index-diff", async (form, lg) => {
    const body = {
      domain: form.domain.value,
      sitemap_url: form.sitemap_url.value,
      mark_submitted: form.mark_submitted.checked,
      project_slug: form.project_slug?.value || null,
    };
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/index-diff/diff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
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
    toast(t(lg, "success"), "success");
  });

  bindForm("form-index-import", async (form, lg) => {
    const main = document.getElementById("form-index-diff");
    const domainInput = document.getElementById("import_domain");
    if (main?.domain?.value && domainInput) {
      domainInput.value = main.domain.value;
    }
    if (!domainInput?.value) {
      throw new Error(lg === "fa" ? "ابتدا دامنه را وارد کنید" : "Enter domain first");
    }
    const fd = new FormData(form);
    if (main?.project_slug?.value) {
      fd.set("project_slug", main.project_slug.value);
    }
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/index-diff/import", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    toast(`${t(lg, "success")}: +${data.added}`, "success");
  });
}

function initContentForm(lang) {
  initProjectSelect();
  bindForm("form-content", async (form, lg) => {
    const fd = new FormData(form);
    toast(t(lg, "processing"));
    const res = await fetch("/api/v1/content/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
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
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showResult(
      "result-generation",
      `<div class="result-success"><pre class="cli-box">${data.cli}</pre><p>${data.message}</p></div>`
    );
  });
}

// Persist language preference
document.querySelectorAll(".lang-switch a").forEach((a) => {
  a.addEventListener("click", () => {
    const lang = a.getAttribute("href").replace("?lang=", "");
    document.cookie = `lang=${lang};path=/;max-age=31536000`;
  });
});
