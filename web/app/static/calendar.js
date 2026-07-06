/**
 * Content calendar Kanban board — campaigns, load, render, drag-drop.
 */

let __kanbanBoardCache = null;
let __kanbanCampaigns = [];
let __activeCampaignId = null;
let __kanbanProjectSlug = null;
let __kanbanMembersCache = [];

function findKanbanItem(itemId) {
  return (__kanbanBoardCache?.items || []).find((i) => i.id === itemId);
}

const KANBAN_COLUMNS = [
  { key: "pending", labelKey: "kanban_pending" },
  { key: "in_progress", labelKey: "kanban_in_progress" },
  { key: "done", labelKey: "kanban_done" },
];

function kanbanLabel(labels, key) {
  const map = {
    pending: labels.pending,
    in_progress: labels.in_progress,
    done: labels.done,
    planned: labels.pending,
    writing: labels.in_progress,
    review: labels.in_progress,
    scheduled: labels.in_progress,
    published: labels.done,
  };
  return map[key] || key;
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function memberOptions(members, selectedId, labels) {
  const sel = selectedId ? Number(selectedId) : null;
  let html = `<option value="">${escapeHtml(labels.unassigned || "—")}</option>`;
  for (const m of members || []) {
    const id = Number(m.id);
    const name = m.display_name || m.username || `#${id}`;
    html += `<option value="${id}" ${id === sel ? "selected" : ""}>${escapeHtml(name)}</option>`;
  }
  return html;
}

function assigneeName(assignee, labels) {
  if (!assignee) return labels.unassigned || "—";
  return assignee.display_name || assignee.username || "—";
}

async function loadKanbanMembers(projectSlug) {
  if (!projectSlug) {
    __kanbanMembersCache = [];
    return [];
  }
  const res = await fetch(`/api/v1/calendar/members?project_slug=${encodeURIComponent(projectSlug)}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  __kanbanMembersCache = data.members || [];
  return __kanbanMembersCache;
}

function renderChecklist(item, labels, lang) {
  const list = item.checklist || [];
  return list
    .map((row, idx) => {
      const label = lang === "fa" ? row.label_fa || row.label_en : row.label_en || row.label_fa;
      const checked = row.done ? "checked" : "";
      return `<label class="checklist-row">
        <input type="checkbox" data-check-idx="${idx}" ${checked} />
        <span>${escapeHtml(label)}</span>
      </label>`;
    })
    .join("");
}

function parseH2Headings(raw) {
  if (Array.isArray(raw)) return raw.map((x) => String(x).trim()).filter(Boolean);
  return String(raw || "")
    .split(" | ")
    .map((s) => s.trim())
    .filter(Boolean);
}

function serializeH2Headings(list) {
  return list.map((h) => h.trim()).filter(Boolean).join(" | ");
}

function renderH2Block(item, labels, lang) {
  const headings = parseH2Headings(item.h2_headings);
  const sectionLabel = labels.h2Section || (lang === "fa" ? "هدینگ‌های H2" : "H2 headings");
  const actionsLabel = labels.h2Actions || (lang === "fa" ? "عملیات هدینگ" : "Heading actions");
  const rows = headings
    .map((heading, idx) => {
      const textId = `h2-text-${item.id}-${idx}`;
      const deleteLabel = `${labels.h2Delete || "Delete"}: ${heading}`;
      const rewriteLabel = `${labels.h2Rewrite || "Rewrite"}: ${heading}`;
      return `<li class="card-h2-row" data-h2-idx="${idx}">
        <span class="card-h2-text" id="${textId}">${escapeHtml(heading)}</span>
        <div class="card-h2-actions" role="group" aria-label="${escapeHtml(actionsLabel)}">
          <button type="button" class="btn-icon h2-btn-delete" data-item-id="${item.id}" data-h2-idx="${idx}"
            aria-label="${escapeHtml(deleteLabel)}" title="${escapeHtml(labels.h2Delete || "Delete")}">×</button>
          <button type="button" class="btn-icon h2-btn-rewrite" data-item-id="${item.id}" data-h2-idx="${idx}"
            aria-label="${escapeHtml(rewriteLabel)}" title="${escapeHtml(labels.h2Rewrite || "Rewrite")}">↻</button>
        </div>
      </li>`;
    })
    .join("");

  return `<div class="card-h2-block" data-item-id="${item.id}">
    <h5 class="card-h2-title" id="h2-heading-${item.id}">${escapeHtml(sectionLabel)}</h5>
    <ul class="card-h2-list" aria-labelledby="h2-heading-${item.id}">
      ${rows || `<li class="muted card-h2-empty">${escapeHtml(labels.h2Empty || "")}</li>`}
    </ul>
    <button type="button" class="btn btn-ghost btn-sm h2-btn-add" data-item-id="${item.id}"
      aria-label="${escapeHtml(labels.h2Add || "Add H2")}">
      + ${escapeHtml(labels.h2Add || "Add H2")}
    </button>
  </div>`;
}

function refreshH2Block(itemId, labels, lang) {
  const item = findKanbanItem(itemId);
  const card = document.querySelector(`.kanban-card[data-item-id="${itemId}"]`);
  if (!item || !card) return;
  const old = card.querySelector(".card-h2-block");
  const html = renderH2Block(item, labels, lang);
  if (old) {
    old.outerHTML = html;
  } else {
    const anchor = card.querySelector(".kanban-kw") || card.querySelector(".kanban-card-title");
    anchor?.insertAdjacentHTML("afterend", html);
  }
  bindH2Events(labels, lang);
}

async function saveH2List(itemId, headings, labels, lang) {
  const updated = await patchItem(itemId, { h2_headings: serializeH2Headings(headings) });
  const item = findKanbanItem(itemId);
  if (item) item.h2_headings = updated.h2_headings;
  refreshH2Block(itemId, labels, lang);
  return updated;
}

function bindH2Events(labels, lang) {
  document.querySelectorAll(".h2-btn-delete").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const itemId = btn.dataset.itemId;
      const idx = Number(btn.dataset.h2Idx);
      const item = findKanbanItem(itemId);
      if (!item) return;
      const headings = parseH2Headings(item.h2_headings);
      const removed = headings[idx];
      const confirmMsg = (labels.h2DeleteConfirm || "Delete this heading?").replace("{heading}", removed || "");
      if (!window.confirm(confirmMsg)) return;
      headings.splice(idx, 1);
      btn.disabled = true;
      try {
        await saveH2List(itemId, headings, labels, lang);
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  });

  document.querySelectorAll(".h2-btn-rewrite").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const itemId = btn.dataset.itemId;
      const idx = Number(btn.dataset.h2Idx);
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      try {
        const fd = new FormData();
        fd.set("heading_index", String(idx));
        fd.set("use_ai", "true");
        const res = await fetch(`/api/v1/calendar/items/${encodeURIComponent(itemId)}/h2-rewrite`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        if (data.credit_exhausted) {
          toast(data.credit_message || labels.creditExhausted || "Recharge AI", "error");
        }
        const item = findKanbanItem(itemId);
        if (item && data.item) {
          item.h2_headings = data.item.h2_headings;
        }
        refreshH2Block(itemId, labels, lang);
        toast(labels.h2Rewritten || labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
        btn.removeAttribute("aria-busy");
      }
    });
  });

  document.querySelectorAll(".h2-btn-add").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const itemId = btn.dataset.itemId;
      const item = findKanbanItem(itemId);
      if (!item) return;
      const promptLabel = labels.h2AddPrompt || "New H2 heading:";
      const value = window.prompt(promptLabel, "");
      if (!value?.trim()) return;
      const headings = parseH2Headings(item.h2_headings);
      headings.push(value.trim());
      btn.disabled = true;
      try {
        await saveH2List(itemId, headings, labels, lang);
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function renderCard(item, labels, lang) {
  const h2html = renderH2Block(item, labels, lang);
  const jalali = typeof formatJalaliDate === "function" ? formatJalaliDate(item.publish_date, lang) : item.publish_date;
  const assignee = assigneeName(item.assignee, labels);
  const showAssignee = Boolean(__kanbanProjectSlug);

  return `
    <article class="kanban-card" data-item-id="${item.id}" draggable="true"
      aria-label="${escapeHtml(item.title || item.h1_title || labels.card || "Card")}">
      <div class="kanban-card-head">
        <span class="kanban-date" title="${escapeHtml(item.publish_date || "")}">${escapeHtml(jalali)}</span>
        <div class="kanban-card-head-actions">
          ${showAssignee ? `<span class="task-assignee-chip kanban-assignee-chip ${item.assignee ? "" : "unassigned"}" title="${escapeHtml(labels.assignee || "Assignee")}">👤 ${escapeHtml(assignee)}</span>` : ""}
          ${item.difficulty_label ? `<span class="kanban-tag">${escapeHtml(item.difficulty_label)}</span>` : ""}
          <button type="button" class="btn-icon-delete kanban-delete-item" data-item-id="${item.id}"
            title="${escapeHtml(labels.item_delete || "Delete")}" aria-label="${escapeHtml(labels.item_delete || "Delete")}">×</button>
        </div>
      </div>
      <h4 class="kanban-card-title">${escapeHtml(item.title || item.h1_title || "—")}</h4>
      ${item.url ? `<p class="muted kanban-item-url"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.url)}</a></p>` : ""}
      ${item.keywords ? `<p class="muted kanban-kw">${escapeHtml(item.keywords)}</p>` : ""}
      ${h2html}
      ${showAssignee ? `<label class="kanban-assignee-label">
        <span class="muted">${labels.assignee || "Assignee"}</span>
        <select class="kanban-assignee-select" data-item-id="${item.id}" aria-label="${escapeHtml(labels.assignee || "Assignee")}">
          ${memberOptions(__kanbanMembersCache, item.assignee?.id, labels)}
        </select>
      </label>` : ""}
      <details class="kanban-details">
        <summary>${labels.checklist || "Checklist"}</summary>
        <div class="checklist-box" data-item-id="${item.id}">${renderChecklist(item, labels, lang)}</div>
      </details>
      <label class="kanban-notes-label">
        <span class="muted">${labels.notes || "Notes"}</span>
        <textarea class="kanban-notes" rows="2" data-item-id="${item.id}">${escapeHtml(item.notes || "")}</textarea>
      </label>
      <select class="kanban-move-select" data-item-id="${item.id}" aria-label="${labels.move || "Move"}">
        ${KANBAN_COLUMNS.map(
          (col) =>
            `<option value="${col.key}" ${col.key === item.status ? "selected" : ""}>${escapeHtml(
              kanbanLabel(labels, col.key)
            )}</option>`
        ).join("")}
      </select>
      <button type="button" class="btn btn-ghost btn-sm kanban-link-suggest" data-item-id="${item.id}">
        ${escapeHtml(labels.linkSuggest || "Suggest links")}
      </button>
      <div class="kanban-suggested-links hidden" data-item-id="${item.id}"></div>
    </article>`;
}

function normalizeKanbanStatus(status) {
  const legacy = {
    planned: "pending",
    writing: "in_progress",
    review: "in_progress",
    scheduled: "in_progress",
    published: "done",
  };
  const norm = legacy[status] || status;
  return KANBAN_COLUMNS.some((c) => c.key === norm) ? norm : "pending";
}

function renderBoard(board, labels, lang) {
  const root = document.getElementById("kanban-root");
  if (!root) return;
  __kanbanBoardCache = board;
  const byStatus = Object.fromEntries(KANBAN_COLUMNS.map((c) => [c.key, []]));
  for (const item of board.items || []) {
    const st = normalizeKanbanStatus(item.status);
    byStatus[st].push(item);
  }

  root.innerHTML = KANBAN_COLUMNS.map((col) => {
    const cards = (byStatus[col.key] || []).map((item) => renderCard(item, labels, lang)).join("");
    return `
      <section class="kanban-column" data-status="${col.key}" aria-labelledby="kanban-col-${col.key}">
        <header class="kanban-column-head">
          <h3 id="kanban-col-${col.key}">${escapeHtml(kanbanLabel(labels, col.key))}</h3>
          <span class="kanban-count" aria-label="${escapeHtml(labels.count || "Count")}">${(byStatus[col.key] || []).length}</span>
        </header>
        <div class="kanban-column-body" data-drop-status="${col.key}">${cards || `<p class="muted kanban-empty">${labels.empty || ""}</p>`}</div>
      </section>`;
  }).join("");

  bindKanbanEvents(labels, lang);
  bindH2Events(labels, lang);
}

function renderCampaignTabs(labels, lang) {
  const root = document.getElementById("campaign-tabs");
  if (!root) return;
  const addLabel = labels.campaign_add || "+";
  root.innerHTML =
    __kanbanCampaigns
      .map(
        (c) => `
      <div class="campaign-tab ${c.id === __activeCampaignId ? "active" : ""}" role="button" tabindex="0"
        data-campaign-id="${c.id}" draggable="true">
        <span class="campaign-tab-name">${escapeHtml(c.name)}</span>
        <span class="campaign-count">${c.item_count || 0}</span>
        <button type="button" class="btn-icon-delete campaign-tab-delete" data-campaign-id="${c.id}"
          title="${escapeHtml(labels.campaign_delete || "Delete campaign")}"
          aria-label="${escapeHtml(labels.campaign_delete || "Delete campaign")}">×</button>
      </div>`
      )
      .join("") +
    `<button type="button" class="campaign-tab campaign-tab-add" id="btn-add-campaign" title="${escapeHtml(addLabel)}">${escapeHtml(addLabel)}</button>`;
  bindCampaignTabEvents(labels, lang);
}

async function patchItem(itemId, payload) {
  const res = await fetch(`/api/v1/calendar/items/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data.item;
}

async function deleteItem(itemId, labels, lang) {
  const msg = labels.item_delete_confirm || "Delete this item?";
  if (!window.confirm(msg)) return false;
  const res = await fetch(`/api/v1/calendar/items/${encodeURIComponent(itemId)}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  if (__kanbanBoardCache?.items) {
    __kanbanBoardCache.items = __kanbanBoardCache.items.filter((i) => i.id !== itemId);
  }
  document.querySelector(`.kanban-card[data-item-id="${itemId}"]`)?.remove();
  await refreshCampaignCounts(labels, lang);
  toast(labels.deleted || labels.saved || "Deleted", "success");
  return true;
}

async function deleteCampaign(campaignId, labels, lang) {
  const camp = __kanbanCampaigns.find((c) => c.id === campaignId);
  const name = camp?.name || "";
  const msg = (labels.campaign_delete_confirm || "Delete campaign «{name}» and all items?").replace("{name}", name);
  if (!window.confirm(msg)) return false;
  const res = await fetch(`/api/v1/calendar/campaigns/${encodeURIComponent(campaignId)}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  __kanbanCampaigns = __kanbanCampaigns.filter((c) => c.id !== campaignId);
  if (__activeCampaignId === campaignId) {
    __activeCampaignId = __kanbanCampaigns[0]?.id || null;
    const root = document.getElementById("kanban-root");
    if (__activeCampaignId) {
      await loadCampaignKanban(__activeCampaignId, labels, lang);
      const url = new URL(window.location.href);
      url.searchParams.set("campaign_id", __activeCampaignId);
      window.history.replaceState({}, "", url);
    } else if (root) {
      root.innerHTML = `<p class="muted">${labels.campaign_empty || labels.empty || ""}</p>`;
    }
  }
  renderCampaignTabs(labels, lang);
  toast(labels.deleted || labels.saved || "Deleted", "success");
  return true;
}

function bindCampaignTabEvents(labels, lang) {
  let dragCampaignId = null;

  document.querySelectorAll(".campaign-tab:not(.campaign-tab-add)").forEach((tab) => {
    tab.addEventListener("click", async (e) => {
      if (e.target.closest(".campaign-tab-delete")) return;
      const cid = tab.dataset.campaignId;
      if (!cid || cid === __activeCampaignId) return;
      __activeCampaignId = cid;
      renderCampaignTabs(labels, lang);
      await loadCampaignKanban(cid, labels, lang);
      const url = new URL(window.location.href);
      url.searchParams.set("campaign_id", cid);
      window.history.replaceState({}, "", url);
    });

    tab.addEventListener("dragstart", (e) => {
      dragCampaignId = tab.dataset.campaignId;
      tab.classList.add("dragging");
      e.dataTransfer?.setData("text/plain", dragCampaignId);
    });
    tab.addEventListener("dragend", () => {
      tab.classList.remove("dragging");
      dragCampaignId = null;
    });
    tab.addEventListener("dragover", (e) => {
      e.preventDefault();
      tab.classList.add("drag-over");
    });
    tab.addEventListener("dragleave", () => tab.classList.remove("drag-over"));
    tab.addEventListener("drop", async (e) => {
      e.preventDefault();
      tab.classList.remove("drag-over");
      const itemId = e.dataTransfer?.getData("application/x-kanban-item");
      if (itemId) {
        const targetId = tab.dataset.campaignId;
        if (targetId && targetId !== __activeCampaignId) {
          try {
            await patchItem(itemId, { campaign_id: targetId });
            document.querySelector(`.kanban-card[data-item-id="${itemId}"]`)?.remove();
            toast(labels.saved || "Saved", "success");
            await refreshCampaignCounts(labels, lang);
          } catch (err) {
            toast(`${labels.error || "Error"}: ${err.message}`, "error");
          }
        }
        return;
      }
      const fromId = dragCampaignId;
      const toId = tab.dataset.campaignId;
      if (!fromId || !toId || fromId === toId) return;
      const ids = __kanbanCampaigns.map((c) => c.id);
      const fromIdx = ids.indexOf(fromId);
      const toIdx = ids.indexOf(toId);
      if (fromIdx < 0 || toIdx < 0) return;
      ids.splice(fromIdx, 1);
      ids.splice(toIdx, 0, fromId);
      try {
        const res = await fetch("/api/v1/calendar/campaigns/reorder", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_slug: __kanbanProjectSlug, ordered_ids: ids }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        __kanbanCampaigns = data.campaigns || __kanbanCampaigns;
        renderCampaignTabs(labels, lang);
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".campaign-tab-delete").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await deleteCampaign(btn.dataset.campaignId, labels, lang);
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.getElementById("btn-add-campaign")?.addEventListener("click", async () => {
    if (!__kanbanProjectSlug) return;
    const defaultName = labels.campaign_default_name || "کمپین جدید";
    const name = window.prompt(labels.campaign_prompt || "Campaign name:", defaultName);
    if (!name?.trim()) return;
    try {
      const res = await fetch("/api/v1/calendar/campaigns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_slug: __kanbanProjectSlug, name: name.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      __kanbanCampaigns.push({ ...data.campaign, item_count: 0 });
      __activeCampaignId = data.campaign.id;
      renderCampaignTabs(labels, lang);
      await loadCampaignKanban(__activeCampaignId, labels, lang);
    } catch (err) {
      toast(`${labels.error || "Error"}: ${err.message}`, "error");
    }
  });
}

async function refreshCampaignCounts(labels, lang) {
  if (!__kanbanProjectSlug) return;
  const res = await fetch(`/api/v1/calendar/campaigns?project_slug=${encodeURIComponent(__kanbanProjectSlug)}`);
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    __kanbanCampaigns = data.campaigns || [];
    renderCampaignTabs(labels, lang);
  }
}

function bindKanbanEvents(labels, lang) {
  document.querySelectorAll(".kanban-link-suggest").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const itemId = btn.dataset.itemId;
      if (!__kanbanProjectSlug) {
        toast(labels.indexRequired || "Run Site Index first", "error");
        return;
      }
      btn.disabled = true;
      try {
        const fd = new FormData();
        fd.set("project_slug", __kanbanProjectSlug);
        fd.set("use_ai", "true");
        const res = await fetch(`/api/v1/calendar/items/${encodeURIComponent(itemId)}/link-suggestions`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        if (data.credit_exhausted) {
          toast(data.credit_message || labels.creditExhausted || "Recharge AI", "error");
        }
        const box = document.querySelector(`.kanban-suggested-links[data-item-id="${itemId}"]`);
        const links = data.suggestions || [];
        if (box && links.length) {
          box.classList.remove("hidden");
          box.innerHTML = `<ul class="card-h2">${links
            .map(
              (l) =>
                `<li><a href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.anchor_text || l.url)}</a> <span class="muted">(${escapeHtml(l.page_type || "")})</span></li>`
            )
            .join("")}</ul>`;
        } else if (box) {
          box.classList.remove("hidden");
          box.innerHTML = `<p class="muted">${labels.linkSuggestEmpty || "No suggestions"}</p>`;
        }
        const item = findKanbanItem(itemId);
        if (item) item.suggested_links = links;
        toast(labels.saved || "Done", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  });

  document.querySelectorAll(".kanban-delete-item").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await deleteItem(btn.dataset.itemId, labels, lang);
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".kanban-move-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const id = sel.dataset.itemId;
      const card = sel.closest(".kanban-card");
      const targetCol = document.querySelector(`.kanban-column-body[data-drop-status="${sel.value}"]`);
      try {
        await patchItem(id, { status: sel.value });
        if (card && targetCol) targetCol.appendChild(card);
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".kanban-assignee-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const val = sel.value ? Number(sel.value) : null;
      try {
        const updated = await patchItem(sel.dataset.itemId, { assigned_user_id: val });
        const item = findKanbanItem(sel.dataset.itemId);
        if (item) item.assignee = updated.assignee;
        const card = sel.closest(".kanban-card");
        const chip = card?.querySelector(".kanban-assignee-chip");
        if (chip) {
          chip.textContent = `👤 ${assigneeName(updated.assignee, labels)}`;
          chip.classList.toggle("unassigned", !updated.assignee);
        }
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".kanban-notes").forEach((ta) => {
    let timer;
    ta.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          await patchItem(ta.dataset.itemId, { notes: ta.value });
        } catch (err) {
          toast(`${labels.error || "Error"}: ${err.message}`, "error");
        }
      }, 700);
    });
  });

  document.querySelectorAll(".checklist-box input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", async () => {
      const box = cb.closest(".checklist-box");
      const itemId = box.dataset.itemId;
      const item = findKanbanItem(itemId);
      const checklist = item?.checklist ? [...item.checklist] : [];
      const idx = Number(cb.dataset.checkIdx);
      if (checklist[idx]) checklist[idx].done = cb.checked;
      try {
        const updated = await patchItem(itemId, { checklist });
        if (item) item.checklist = updated.checklist;
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
        cb.checked = !cb.checked;
      }
    });
  });

  let dragId = null;
  document.querySelectorAll(".kanban-card").forEach((card) => {
    card.addEventListener("dragstart", (e) => {
      if (e.target.closest(".kanban-delete-item")) {
        e.preventDefault();
        return;
      }
      dragId = card.dataset.itemId;
      card.classList.add("dragging");
      e.dataTransfer?.setData("application/x-kanban-item", dragId);
      e.dataTransfer?.setData("text/plain", dragId);
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      dragId = null;
    });
  });
  document.querySelectorAll(".kanban-column-body").forEach((zone) => {
    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", async (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      if (!dragId) return;
      const status = zone.dataset.dropStatus;
      const card = document.querySelector(`.kanban-card[data-item-id="${dragId}"]`);
      const sel = card?.querySelector(".kanban-move-select");
      try {
        await patchItem(dragId, { status });
        if (sel) sel.value = status;
        if (card) zone.appendChild(card);
        toast(labels.saved || "Saved", "success");
      } catch (err) {
        toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });
}

async function loadCampaignKanban(campaignId, labels, lang) {
  const res = await fetch(`/api/v1/calendar/campaigns/${encodeURIComponent(campaignId)}/board`);
  if (res.status === 401) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login?lang=${lang}&next=${next}`;
    return;
  }
  const board = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(board.detail || res.statusText);
  const titleEl = document.getElementById("kanban-board-title");
  if (titleEl) titleEl.textContent = board.title || labels.title || "Calendar";
  renderBoard(board, labels, lang);
}

async function loadKanbanBoard(boardId, jobId, labels, lang) {
  let url = boardId
    ? `/api/v1/calendar/boards/${encodeURIComponent(boardId)}`
    : `/api/v1/calendar/by-job/${encodeURIComponent(jobId)}`;
  const res = await fetch(url);
  if (res.status === 401) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login?lang=${lang}&next=${next}`;
    return;
  }
  const board = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(board.detail || res.statusText);
  const titleEl = document.getElementById("kanban-board-title");
  if (titleEl) titleEl.textContent = board.title || labels.title || "Calendar";
  renderBoard(board, labels, lang);
  return board;
}

async function initProjectKanban(projectSlug, preferredCampaignId, boardId, jobId, labels, lang) {
  __kanbanProjectSlug = projectSlug;
  const tabsWrap = document.getElementById("campaign-tabs");
  if (tabsWrap) tabsWrap.classList.remove("hidden");

  try {
    await loadKanbanMembers(projectSlug);
  } catch (err) {
    toast(`${labels.error || "Error"}: ${err.message}`, "error");
  }

  let initialCampaign = preferredCampaignId;
  if (!initialCampaign && (boardId || jobId)) {
    const url = boardId
      ? `/api/v1/calendar/boards/${encodeURIComponent(boardId)}`
      : `/api/v1/calendar/by-job/${encodeURIComponent(jobId)}`;
    const res = await fetch(url);
    const board = await res.json().catch(() => ({}));
    if (res.ok) {
      initialCampaign = board.campaign_id || board.items?.[0]?.campaign_id;
    }
  }

  const res = await fetch(`/api/v1/calendar/campaigns?project_slug=${encodeURIComponent(projectSlug)}`);
  if (res.status === 401) {
    window.location.href = `/login?lang=${lang}`;
    return;
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  __kanbanCampaigns = data.campaigns || [];

  if (!__kanbanCampaigns.length) {
    document.getElementById("kanban-root").innerHTML = `<p class="muted">${labels.campaign_empty || labels.empty}</p>`;
    renderCampaignTabs(labels, lang);
    return;
  }

  __activeCampaignId = initialCampaign || __kanbanCampaigns[0]?.id;
  renderCampaignTabs(labels, lang);
  if (__activeCampaignId) {
    await loadCampaignKanban(__activeCampaignId, labels, lang);
  }
}

function initKanbanPage(lang) {
  const params = new URLSearchParams(window.location.search);
  const project = params.get("project") || document.body.dataset.activeProject || "";
  const campaignId = params.get("campaign_id") || "";
  const boardId = params.get("board_id") || "";
  const jobId = params.get("job_id") || "";
  const labels = window.KANBAN_LABELS || {};

  if (project) {
    initProjectKanban(project, campaignId, boardId, jobId, labels, lang).catch((err) => {
      toast(`${labels.error || "Error"}: ${err.message}`, "error");
    });
    return;
  }

  if (!boardId && !jobId) {
    document.getElementById("kanban-root").innerHTML = `<p class="muted">${labels.missing || ""}</p>`;
    return;
  }
  loadKanbanBoard(boardId, jobId, labels, lang).catch((err) => {
    toast(`${labels.error || "Error"}: ${err.message}`, "error");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.getElementById("kanban-page");
  if (page) initKanbanPage(page.dataset.lang || "fa");
});
