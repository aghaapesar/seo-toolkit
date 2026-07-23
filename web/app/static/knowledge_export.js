/**
 * Knowledge Base export — phase 1: sitemap analyze + segment pick, phase 2: export.
 */

function initKnowledgeExportForm(lang) {
  if (typeof initProjectSelect === "function") initProjectSelect();

  const statsBox = document.getElementById("knowledge-export-stats");
  const filesBox = document.getElementById("knowledge-export-files");
  const sitemapInput = document.getElementById("knowledge-export-sitemap");
  const analyzeForm = document.getElementById("form-knowledge-analyze");
  const exportForm = document.getElementById("form-knowledge-export");
  const exportPhase = document.getElementById("ke-phase-export");
  const segmentPanel = document.getElementById("knowledge-segment-panel");
  const segmentSummary = document.getElementById("knowledge-segment-summary");
  const segmentGroups = document.getElementById("knowledge-segment-groups");
  const selectedCountEl = document.getElementById("knowledge-segment-selected-count");
  const exportBtn = document.getElementById("btn-knowledge-export-start");
  const analysisIdInput = document.getElementById("ke-analysis-id");
  const selectedSegmentsInput = document.getElementById("ke-selected-segments");
  const exportProjectInput = document.getElementById("ke-export-project-slug");
  const exportSitemapInput = document.getElementById("ke-export-sitemap-url");
  const modelSelect = document.getElementById("ke-model-select");
  const testModelBtn = document.getElementById("btn-ke-test-model");

  const projectSelectAnalyze = analyzeForm?.querySelector("[name=project_slug]");
  let currentAnalysis = null;
  let selectedSegmentIds = new Set();

  const tMsg = (fa, en) => (lang === "fa" ? fa : en);

  const loadModels = async () => {
    if (!modelSelect) return;
    try {
      const res = await fetch("/api/v1/settings/models", { credentials: "same-origin" });
      const data = await res.json().catch(() => ({}));
      const models = data.models || [];
      modelSelect.innerHTML = '<option value="">—</option>';
      models.forEach((m) => {
        const opt = document.createElement("option");
        opt.value = m.name || m.slug || "";
        opt.textContent = m.name || m.slug || "";
        if (m.is_default) opt.selected = true;
        modelSelect.appendChild(opt);
      });
    } catch (_) {
      /* ignore */
    }
  };
  loadModels();

  testModelBtn?.addEventListener("click", async () => {
    const name = modelSelect?.value?.trim();
    if (!name) {
      if (typeof toast === "function") toast(tMsg("مدل را انتخاب کنید", "Select a model"), "error");
      return;
    }
    const fd = new FormData();
    fd.set("model_name", name);
    try {
      const res = await fetch("/api/v1/knowledge-export/test-model", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || res.statusText);
      }
      if (typeof toast === "function") toast(tMsg("اتصال موفق", "Connection OK"), "success");
    } catch (err) {
      if (typeof toast === "function") toast(err.message, "error");
    }
  });

  const getProjectSlug = () =>
    projectSelectAnalyze?.value?.trim() ||
    exportProjectInput?.value?.trim() ||
    "";

  const syncHiddenExportFields = () => {
    if (exportProjectInput) exportProjectInput.value = getProjectSlug();
    if (exportSitemapInput && sitemapInput) exportSitemapInput.value = sitemapInput.value.trim();
    if (analysisIdInput && currentAnalysis) analysisIdInput.value = currentAnalysis.analysis_id || "";
    if (selectedSegmentsInput) {
      selectedSegmentsInput.value = JSON.stringify(Array.from(selectedSegmentIds));
    }
  };

  const updateSelectedCount = () => {
    if (!selectedCountEl || !currentAnalysis) return;
    let urlEstimate = 0;
    const segs = currentAnalysis.segments || [];
    segs.forEach((s) => {
      if (selectedSegmentIds.has(s.id)) urlEstimate += s.count || 0;
    });
    selectedCountEl.textContent = tMsg(
      `${selectedSegmentIds.size} پترن انتخاب‌شده (~${urlEstimate} URL)`,
      `${selectedSegmentIds.size} patterns selected (~${urlEstimate} URLs)`
    );
    syncHiddenExportFields();
    const ready = selectedSegmentIds.size > 0 && currentAnalysis?.analysis_id;
    if (exportBtn) exportBtn.disabled = !ready;
    if (exportPhase) {
      exportPhase.classList.toggle("ke-phase-disabled", !ready);
    }
  };

  const renderSegmentGroups = (data) => {
    if (!segmentGroups) return;
    const segments = (data.segments || []).slice().sort((a, b) => (b.count || 0) - (a.count || 0));

    segmentGroups.innerHTML = segments
      .map((seg) => {
        const checked = selectedSegmentIds.has(seg.id) ? "checked" : "";
        const patternLabel = seg.label_fa || seg.label || seg.url_pattern || "";
        const typeLabel =
          lang === "fa"
            ? seg.content_type_label_fa || seg.content_type
            : seg.content_type_label_en || seg.content_type;
        const confidence = seg.sample_confidence ? ` (${seg.sample_confidence})` : "";
        const samples = (seg.sample_pages || seg.sample_urls || [])
          .slice(0, 3)
          .map((s) => {
            if (typeof s === "string") return `<div class="muted">${s}</div>`;
            const title = s.title ? ` — ${s.title}` : "";
            return `<div class="muted">${s.url || ""}${title}</div>`;
          })
          .join("");
        return `
          <label class="ke-segment-row">
            <input type="checkbox" class="ke-segment-cb" data-segment-id="${seg.id}" ${checked} />
            <div class="ke-segment-meta">
              <div><strong>${patternLabel}</strong> <span class="ke-type-badge">${typeLabel}${confidence}</span></div>
              ${samples}
            </div>
            <span class="ke-segment-count">${seg.count || 0}</span>
          </label>`;
      })
      .join("");

    segmentGroups.querySelectorAll(".ke-segment-cb").forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = cb.dataset.segmentId;
        if (cb.checked) selectedSegmentIds.add(id);
        else selectedSegmentIds.delete(id);
        updateSelectedCount();
      });
    });
  };

  const resetAnalysis = () => {
    currentAnalysis = null;
    selectedSegmentIds = new Set();
    segmentPanel?.classList.add("hidden");
    segmentSummary?.classList.add("hidden");
    if (segmentGroups) segmentGroups.innerHTML = "";
    if (exportBtn) exportBtn.disabled = true;
    exportPhase?.classList.add("ke-phase-disabled");
    syncHiddenExportFields();
  };

  const renderDashboard = async (slug) => {
    if (!slug || !statsBox) return;
    try {
      const res = await fetch(
        `/api/v1/knowledge-export/dashboard?project_slug=${encodeURIComponent(slug)}`,
        { credentials: "same-origin" }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 401) {
          statsBox.innerHTML = tMsg("برای مشاهده خروجی وارد شوید.", "Sign in to view export status.");
        }
        return;
      }
      const latest = data.latest;
      const total = latest?.total_pages ?? 0;
      const ragFiles = latest?.exported_files ?? latest?.rag_files ?? 0;
      const parts = (latest?.parts || []).length;
      const generated = latest?.generated_at
        ? new Date(latest.generated_at).toLocaleString(lang === "fa" ? "fa-IR" : "en")
        : "—";
      statsBox.innerHTML = tMsg(
        `<strong>${total}</strong> صفحه · <strong>${parts}</strong> پارت چندمحصولی · <strong>${ragFiles}</strong> فایل نوشته‌شده<br/><span class="muted">آخرین خروجی: ${generated}</span>`,
        `<strong>${total}</strong> pages · <strong>${parts}</strong> multi-product parts · <strong>${ragFiles}</strong> files written<br/><span class="muted">Last export: ${generated}</span>`
      );

      if (filesBox && data.files?.length) {
        const packageFiles = data.files.filter(
          (f) => f.kind === "package" || f.kind === "package_changed" || f.status === "package" || (f.path || "").includes("/packages/")
        );
        const partFiles = data.files.filter(
          (f) => f.kind === "part" || ((f.name || "").startsWith("knowledge_part_") && (f.name || "").endsWith(".md"))
        );
        const indexFiles = data.files.filter((f) => f.kind === "index" || f.name === "index.json");
        const pageFiles = data.files.filter((f) => f.kind === "page" || (f.path || "").includes("/pages/"));
        const reindexCount =
          data.needs_reindex_count ||
          partFiles.filter((f) => f.needs_reindex).length ||
          pageFiles.filter((f) => f.needs_reindex).length;

        let html = `<h3>${tMsg("دانلود پایگاه دانش", "Knowledge base download")}</h3>`;
        html += `<p class="muted" style="margin:0.25rem 0 0.75rem">
          ${tMsg(
            "خروجی اصلی: چند محصول در هر knowledge_part_XX.md (هر محصول کامل در همان فایل).",
            "Primary output: many products per knowledge_part_XX.md (each product finishes in that file)."
          )}
        </p>`;

        if (reindexCount) {
          html += `<p class="ke-reindex-banner" style="margin:0.5rem 0;padding:0.6rem 0.8rem;border-radius:10px;background:rgba(251,191,36,.12);color:#fcd34d;">
            ${tMsg(
              `${reindexCount} موضوع تغییر کرده — پکیج تغییرکرده‌ها یا پارت‌های فلگ‌شده را برای ایندکس مجدد بفرستید.`,
              `${reindexCount} topic(s) changed — upload the changed package / flagged parts to RAG.`
            )}
          </p>`;
        }

        if (packageFiles.length) {
          html += `<div class="ke-packages" style="margin-bottom:1rem;display:flex;flex-direction:column;gap:0.5rem">`;
          packageFiles.forEach((f) => {
            const isChanged = f.kind === "package_changed" || (f.name || "").includes("_changed");
            const btnClass = isChanged ? "btn btn-secondary" : "btn btn-primary";
            const hint = isChanged
              ? tMsg("فقط پارت‌های تغییرکرده برای ایندکس مجدد", "Changed parts only — for re-index")
              : tMsg("کل دانش (پارت‌ها + index)", "Full knowledge (parts + index)");
            html += `<a class="${btnClass}" href="${f.download_url}" style="justify-content:flex-start;text-align:start">
              <span style="font-weight:600">${f.label || f.name}</span>
              <span class="muted" style="margin-inline-start:0.5rem;font-size:0.85em">${hint}</span>
            </a>`;
          });
          html += `</div>`;
        }

        const selectable = [...partFiles, ...indexFiles];
        if (selectable.length) {
          html += `<h4 style="margin:0.75rem 0 0.35rem">${tMsg("فایل‌های پارت (چندمحصولی)", "Part files (multi-product)")}</h4>`;
          html += `<div class="ke-file-toolbar" style="margin-bottom:0.5rem;display:flex;gap:0.5rem;flex-wrap:wrap">
            <button type="button" class="btn btn-ghost btn-sm" id="ke-select-changed">${tMsg("فقط تغییرکرده‌ها", "Changed only")}</button>
            <button type="button" class="btn btn-ghost btn-sm" id="ke-select-all-files">${tMsg("انتخاب همه", "Select all")}</button>
            <button type="button" class="btn btn-ghost btn-sm" id="ke-zip-selected">${tMsg("ZIP انتخاب‌شده", "ZIP selected")}</button>
            <button type="button" class="btn btn-ghost btn-sm" id="ke-mark-reindexed">${tMsg("علامت ایندکس‌شده", "Mark re-indexed")}</button>
          </div>`;
          html += `<div class="ke-part-files" style="max-height:320px;overflow:auto">`;
          selectable.forEach((f) => {
            const topics = f.topic_count ? ` · ${f.topic_count} ${tMsg("محصول", "topics")}` : "";
            const flag = f.needs_reindex
              ? ` <span class="ke-flag-changed" title="${f.change_reason || ""}">${tMsg("تغییرکرده", "CHANGED")}</span>`
              : "";
            const dl = `${f.download_url}&project_slug=${encodeURIComponent(slug)}`;
            html += `<label class="ke-file-row" style="display:flex;gap:0.5rem;align-items:center;padding:0.35rem 0;border-bottom:1px solid rgba(127,127,127,.15)" data-changed="${f.needs_reindex ? "1" : "0"}">
              <input type="checkbox" class="ke-file-cb" data-path="${f.path}" data-changed="${f.needs_reindex ? "1" : "0"}" ${f.needs_reindex ? "checked" : ""} />
              <a href="${dl}">${f.label || f.name}</a>${topics}${flag}
            </label>`;
          });
          html += `</div>`;
        }

        if (pageFiles.length) {
          html += `<details class="ke-optional-pages" style="margin-top:1rem">
            <summary style="cursor:pointer">${tMsg(`فایل‌های اختیاری per-URL (${pageFiles.length})`, `Optional per-URL files (${pageFiles.length})`)}</summary>
            <div class="ke-page-files" style="max-height:200px;overflow:auto;margin-top:0.5rem">`;
          pageFiles.slice(0, 200).forEach((f) => {
            const dl = `${f.download_url}&project_slug=${encodeURIComponent(slug)}`;
            html += `<div style="padding:0.2rem 0"><a href="${dl}">${f.label || f.name}</a></div>`;
          });
          if (pageFiles.length > 200) {
            html += `<p class="muted">${tMsg("… و موارد بیشتر در پکیج ZIP", "… more inside the ZIP package")}</p>`;
          }
          html += `</div></details>`;
        }

        filesBox.innerHTML = html;
        filesBox.classList.remove("hidden");

        document.getElementById("ke-select-changed")?.addEventListener("click", () => {
          filesBox.querySelectorAll(".ke-file-cb").forEach((cb) => {
            cb.checked = cb.dataset.changed === "1";
          });
        });
        document.getElementById("ke-select-all-files")?.addEventListener("click", () => {
          filesBox.querySelectorAll(".ke-file-cb").forEach((cb) => {
            cb.checked = true;
          });
        });
        document.getElementById("ke-zip-selected")?.addEventListener("click", async () => {
          const paths = Array.from(filesBox.querySelectorAll(".ke-file-cb:checked")).map((cb) => cb.dataset.path);
          if (!paths.length) {
            if (typeof toast === "function") toast(tMsg("فایلی انتخاب نشده", "No files selected"), "error");
            return;
          }
          try {
            const res = await fetch("/api/v1/knowledge-export/download-zip", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ project_slug: slug, paths }),
            });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              throw new Error(err.detail || res.statusText);
            }
            const blob = await res.blob();
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "knowledge_export_selected.zip";
            a.click();
          } catch (err) {
            if (typeof toast === "function") toast(err.message, "error");
          }
        });
        document.getElementById("ke-mark-reindexed")?.addEventListener("click", async () => {
          const paths = Array.from(filesBox.querySelectorAll(".ke-file-cb:checked")).map((cb) => cb.dataset.path);
          if (!paths.length) {
            if (typeof toast === "function") toast(tMsg("فایلی انتخاب نشده", "No files selected"), "error");
            return;
          }
          try {
            const res = await fetch("/api/v1/knowledge-export/mark-reindexed", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ project_slug: slug, paths }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.detail || res.statusText);
            if (typeof toast === "function") {
              toast(
                tMsg(`${data.cleared} فایل از فلگ ایندکس خارج شد`, `Cleared re-index flag on ${data.cleared} file(s)`),
                "success"
              );
            }
            await renderDashboard(slug);
          } catch (err) {
            if (typeof toast === "function") toast(err.message, "error");
          }
        });
      } else if (filesBox) {
        filesBox.classList.add("hidden");
        filesBox.innerHTML = "";
      }
    } catch (_) {
      /* ignore */
    }
  };

  const loadProject = async (slug) => {
    if (!slug) return;
    resetAnalysis();
    try {
      const res = await fetch(`/api/v1/projects/${encodeURIComponent(slug)}`);
      if (res.ok) {
        const data = await res.json();
        if (sitemapInput && data.sitemap_url && !sitemapInput.value) {
          sitemapInput.value = data.sitemap_url;
        }
      }
    } catch (_) {
      /* ignore */
    }
    await renderDashboard(slug);
  };

  if (projectSelectAnalyze?.value) loadProject(projectSelectAnalyze.value);
  projectSelectAnalyze?.addEventListener("change", () => loadProject(projectSelectAnalyze.value));

  const runAnalyze = async (form) => {
    const fd = new FormData(form);
    if (!fd.get("project_slug")?.toString().trim()) {
      throw new Error(tMsg("پروژه را انتخاب کنید", "Select a project"));
    }
    if (!fd.get("sitemap_url")?.toString().trim()) {
      throw new Error(tMsg("آدرس sitemap را وارد کنید", "Enter sitemap URL"));
    }
    if (typeof toast === "function") toast(tMsg("در حال آنالیز sitemap…", "Analyzing sitemap…"));
    const btn = document.getElementById("btn-knowledge-analyze");
    if (btn) btn.disabled = true;

    try {
      const res = await fetch("/api/v1/knowledge-export/analyze", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof formatApiError === "function" ? formatApiError(data, res.statusText) : data.detail || res.statusText
        );
      }

      currentAnalysis = data;
      selectedSegmentIds = new Set((data.segments || []).map((s) => s.id));

      if (segmentSummary) {
        const patternCount = data.pattern_count ?? (data.segments?.length || 0);
        let staleHtml = "";
        if (data.staleness) {
          const st = data.staleness;
          staleHtml = tMsg(
            `<br/><span class="muted">جدید: ${st.new_count} · قدیمی/آپدیت‌شده: ${st.stale_count} · بدون تغییر: ${st.unchanged_count}` +
              (st.needs_reindex_count != null ? ` · فلگ ایندکس: ${st.needs_reindex_count}` : "") +
              `</span>` +
              (st.stale_count > 0
                ? `<br/><strong style="color:#fcd34d">محتوای ${st.stale_count} URL در سایت‌مپ آپدیت شده — همان فایل md قبلی را دوباره بسازید و فقط تغییرکرده‌ها را به RAG بفرستید.</strong>`
                : ""),
            `<br/><span class="muted">New: ${st.new_count} · Stale: ${st.stale_count} · Unchanged: ${st.unchanged_count}` +
              (st.needs_reindex_count != null ? ` · Re-index flags: ${st.needs_reindex_count}` : "") +
              `</span>` +
              (st.stale_count > 0
                ? `<br/><strong style="color:#fcd34d">${st.stale_count} URL(s) updated in sitemap — re-export and send only changed MD to RAG.</strong>`
                : "")
          );
        }
        segmentSummary.innerHTML = tMsg(
          `<strong>${data.total_urls}</strong> URL در <strong>${patternCount}</strong> پترن · <span class="muted">نوع محتوا از نمونه صفحات</span>${staleHtml}`,
          `<strong>${data.total_urls}</strong> URLs in <strong>${patternCount}</strong> patterns · <span class="muted">content type from sampled pages</span>${staleHtml}`
        );
        segmentSummary.classList.remove("hidden");
      }
      segmentPanel?.classList.remove("hidden");
      renderSegmentGroups(data);
      updateSelectedCount();
      if (typeof toast === "function") toast(tMsg("آنالیز تمام شد", "Analysis complete"), "success");
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  if (typeof bindForm === "function") {
    bindForm("form-knowledge-analyze", async (form) => runAnalyze(form));
  } else {
    analyzeForm?.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await runAnalyze(e.target);
      } catch (err) {
        if (typeof toast === "function") toast(err.message, "error");
      }
    });
  }

  document.getElementById("btn-segment-all")?.addEventListener("click", () => {
    (currentAnalysis?.segments || []).forEach((s) => selectedSegmentIds.add(s.id));
    segmentGroups?.querySelectorAll(".ke-segment-cb").forEach((cb) => {
      cb.checked = true;
    });
    updateSelectedCount();
  });

  document.getElementById("btn-segment-none")?.addEventListener("click", () => {
    selectedSegmentIds.clear();
    segmentGroups?.querySelectorAll(".ke-segment-cb").forEach((cb) => {
      cb.checked = false;
    });
    updateSelectedCount();
  });

  const startExport = async (form) => {
    syncHiddenExportFields();
    if (!analysisIdInput?.value) {
      throw new Error(tMsg("ابتدا sitemap را آنالیز کنید", "Analyze sitemap first"));
    }
    if (!selectedSegmentIds.size) {
      throw new Error(tMsg("حداقل یک سگمنت انتخاب کنید", "Select at least one segment"));
    }
    const fd = new FormData(form);
    // Unchecked checkboxes are omitted — set explicit false for toggles
    ["include_blog", "include_noindex", "write_parts", "write_per_url", "skip_unchanged"].forEach((name) => {
      const el = form.querySelector(`[name="${name}"]`);
      if (el && el.type === "checkbox" && !el.checked) {
        fd.set(name, "false");
      }
    });
    if (typeof toast === "function") toast(typeof t === "function" ? t(lang, "processing") : "Processing…");
    const res = await fetch("/api/v1/knowledge-export/start", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(
        typeof formatApiError === "function" ? formatApiError(data, res.statusText) : data.detail || res.statusText
      );
    }
    const qs = new URLSearchParams({ lang });
    const slug = getProjectSlug();
    if (slug) qs.set("project", slug);
    window.location.href = `/tasks/${data.job_id}?${qs}`;
  };

  if (typeof bindForm === "function") {
    bindForm("form-knowledge-export", async (form) => startExport(form));
  } else {
    exportForm?.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await startExport(e.target);
      } catch (err) {
        if (typeof toast === "function") toast(err.message, "error");
      }
    });
  }
}
