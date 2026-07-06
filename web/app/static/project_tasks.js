/**
 * Per-project reminder tasks Kanban — priority, tags, Jalali due dates,
 * subtasks, and user assignment.
 */

const TASK_COLUMNS = [
  { key: "pending", labelKey: "pending" },
  { key: "in_progress", labelKey: "in_progress" },
  { key: "done", labelKey: "done" },
];

const PRIORITY_OPTIONS = [
  { key: "high", labelKey: "priority_high", cls: "task-priority-high" },
  { key: "medium", labelKey: "priority_medium", cls: "task-priority-medium" },
  { key: "low", labelKey: "priority_low", cls: "task-priority-low" },
];

let __tasksCache = null;
let __membersCache = [];

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getLang() {
  return document.getElementById("project-tasks-page")?.dataset.lang || document.body.dataset.lang || "fa";
}

function getProjectSlug() {
  const fromUrl = new URLSearchParams(window.location.search).get("project");
  const fromBody = document.body.dataset.activeProject;
  const fromSelect = document.getElementById("global-project-select")?.value;
  return (fromUrl || fromSelect || fromBody || "").trim();
}

function priorityLabel(labels, key) {
  const map = {
    high: labels.priority_high,
    medium: labels.priority_medium,
    low: labels.priority_low,
  };
  return map[key] || key;
}

function formatDueDate(isoDate, lang) {
  if (!isoDate) return "";
  if (typeof formatJalaliDate === "function") {
    return formatJalaliDate(isoDate, lang);
  }
  return isoDate;
}

function isOverdue(dueDate) {
  if (!dueDate) return false;
  const today = new Date().toISOString().slice(0, 10);
  return dueDate < today;
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

async function patchTask(taskId, payload) {
  const res = await fetch(`/api/v1/project-tasks/tasks/${encodeURIComponent(taskId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  const task = data.task;
  const idx = (__tasksCache?.items || []).findIndex((t) => t.id === taskId);
  if (idx >= 0 && __tasksCache?.items) __tasksCache.items[idx] = task;
  return task;
}

function renderTags(tagsList) {
  if (!tagsList?.length) return "";
  return tagsList.map((t) => `<span class="task-tag">${escapeHtml(t)}</span>`).join("");
}

function renderSubtasks(task, members, labels) {
  const items = (task.subtasks || [])
    .map(
      (st) => `
      <li class="task-subtask-item ${st.done ? "done" : ""}" data-subtask-id="${st.id}">
        <input type="checkbox" class="task-subtask-check" data-subtask-id="${st.id}" ${st.done ? "checked" : ""} />
        <span class="task-subtask-title">${escapeHtml(st.title)}</span>
        <select class="task-subtask-assign" data-subtask-id="${st.id}" title="${escapeHtml(labels.assignee || "Assignee")}">
          ${memberOptions(members, st.assignee?.id, labels)}
        </select>
        <button type="button" class="btn-icon-delete task-subtask-delete" data-subtask-id="${st.id}" title="×">×</button>
      </li>`
    )
    .join("");

  const progress =
    task.subtask_total > 0
      ? `${task.subtask_done}/${task.subtask_total}`
      : "";

  return `
    <details class="task-subtasks-panel">
      <summary>${escapeHtml(labels.subtasks || "Subtasks")}${progress ? ` (${progress})` : ""}</summary>
      <ul class="task-subtask-list">${items || `<li class="muted" style="font-size:0.8rem;">—</li>`}</ul>
      <div class="task-subtask-add">
        <input type="text" class="task-subtask-input" data-task-id="${task.id}" placeholder="${escapeHtml(labels.subtask_placeholder || "New subtask…")}" />
        <select class="task-subtask-new-assign" data-task-id="${task.id}">
          ${memberOptions(members, null, labels)}
        </select>
        <button type="button" class="btn btn-ghost btn-sm task-subtask-add-btn" data-task-id="${task.id}">${escapeHtml(labels.subtask_add || "+")}</button>
      </div>
    </details>`;
}

function renderTaskCard(task, members, labels, lang) {
  const pri = PRIORITY_OPTIONS.find((p) => p.key === task.priority) || PRIORITY_OPTIONS[1];
  const dueFmt = formatDueDate(task.due_date, lang);
  const overdue = isOverdue(task.due_date) && task.status !== "done";
  const pickerId = `task-due-${task.id}`;
  const hasMeta = (task.tags_list?.length > 0) || dueFmt || (task.subtask_total > 0);

  return `
    <article class="kanban-card project-task-card task-card-v2" data-task-id="${task.id}" draggable="true">
      <div class="task-card-top">
        <span class="task-priority-badge ${pri.cls}">${escapeHtml(priorityLabel(labels, pri.key))}</span>
        <button type="button" class="btn-icon-delete task-delete-btn" data-task-id="${task.id}" title="${escapeHtml(labels.task_delete || "Delete")}">×</button>
      </div>
      <h4 class="task-card-title">${escapeHtml(task.title)}</h4>
      ${hasMeta ? `<div class="task-card-meta">
        ${renderTags(task.tags_list)}
        ${dueFmt ? `<span class="task-due-chip ${overdue ? "overdue" : ""}">📅 ${escapeHtml(dueFmt)}${overdue ? " ⚠" : ""}</span>` : ""}
        ${task.subtask_total > 0 ? `<span class="task-subtask-progress">✓ ${task.subtask_done}/${task.subtask_total}</span>` : ""}
      </div>` : ""}
      <details class="task-card-details">
        <summary>${escapeHtml(labels.details || "Details")}</summary>
        <div class="task-card-body">
          <label>
            <span class="task-field-label muted">${labels.notes || "Notes"}</span>
            <textarea class="kanban-notes task-notes" rows="2" data-task-id="${task.id}">${escapeHtml(task.notes || "")}</textarea>
          </label>
          <div class="task-inline-grid">
            <label>
              <span class="task-field-label muted">${labels.priority || "Priority"}</span>
              <select class="task-priority-select" data-task-id="${task.id}">
                ${PRIORITY_OPTIONS.map(
                  (p) =>
                    `<option value="${p.key}" ${p.key === task.priority ? "selected" : ""}>${escapeHtml(priorityLabel(labels, p.key))}</option>`
                ).join("")}
              </select>
            </label>
            <label>
              <span class="task-field-label muted">${labels.assignee || "Assignee"}</span>
              <select class="task-assignee-select" data-task-id="${task.id}">
                ${memberOptions(members, task.assignee?.id, labels)}
              </select>
            </label>
          </div>
          <label>
            <span class="task-field-label muted">${labels.due_date || "Due date"}</span>
            <div class="task-due-jalali" data-task-id="${task.id}" data-iso="${escapeHtml(task.due_date || "")}">
              ${typeof jalaliPickerHtml === "function" ? jalaliPickerHtml(pickerId, null, `${pickerId}-iso`) : ""}
            </div>
          </label>
          <label>
            <span class="task-field-label muted">${labels.tags || "Tags"}</span>
            <input type="text" class="task-tags-input" data-task-id="${task.id}" value="${escapeHtml(task.tags || "")}" placeholder="seo, blog" />
          </label>
          <select class="kanban-move-select task-move-select" data-task-id="${task.id}" aria-label="${labels.move || "Move"}">
            ${TASK_COLUMNS.map(
              (col) =>
                `<option value="${col.key}" ${col.key === task.status ? "selected" : ""}>${escapeHtml(labels[col.labelKey] || col.key)}</option>`
            ).join("")}
          </select>
        </div>
      </details>
      ${renderSubtasks(task, members, labels)}
    </article>`;
}

function initCardJalaliPickers(lang) {
  document.querySelectorAll(".task-due-jalali").forEach((wrap) => {
    const taskId = wrap.dataset.taskId;
    const iso = wrap.dataset.iso || "";
    const pickerId = `task-due-${taskId}`;
    if (!document.getElementById(pickerId)) return;
    initJalaliDatePicker(pickerId, {
      lang,
      allowEmpty: true,
      defaultIso: iso,
      onChange: async (val) => {
        try {
          await patchTask(taskId, { due_date: val });
        } catch (_) {
          /* autosave */
        }
      },
    });
  });
}

function fillMemberSelects(members, labels) {
  const html = memberOptions(members, null, labels);
  document.querySelectorAll(".task-subtask-new-assign").forEach((sel) => {
    sel.innerHTML = html;
  });
}

function renderBoard(board, labels, lang) {
  const root = document.getElementById("project-tasks-root");
  if (!root) return;
  __tasksCache = board;
  __membersCache = board.members || [];

  fillMemberSelects(__membersCache, labels);

  const byStatus = Object.fromEntries(TASK_COLUMNS.map((c) => [c.key, []]));
  for (const item of board.items || []) {
    const st = TASK_COLUMNS.some((c) => c.key === item.status) ? item.status : "pending";
    byStatus[st].push(item);
  }

  root.innerHTML = TASK_COLUMNS.map((col) => {
    const cards = (byStatus[col.key] || [])
      .map((t) => renderTaskCard(t, __membersCache, labels, lang))
      .join("");
    return `
      <section class="kanban-column" data-status="${col.key}">
        <header class="kanban-column-head">
          <h3>${escapeHtml(labels[col.labelKey] || col.key)}</h3>
          <span class="kanban-count">${(byStatus[col.key] || []).length}</span>
        </header>
        <div class="kanban-column-body" data-drop-status="${col.key}">
          ${cards || `<p class="muted kanban-empty">${labels.empty || ""}</p>`}
        </div>
      </section>`;
  }).join("");

  initCardJalaliPickers(lang);
  bindTaskEvents(labels, lang);
}

function bindDebouncedPatch(selector, field, delay = 600) {
  document.querySelectorAll(selector).forEach((el) => {
    let timer;
    const handler = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          await patchTask(el.dataset.taskId, { [field]: el.value });
        } catch (_) {
          /* autosave */
        }
      }, delay);
    };
    el.addEventListener("input", handler);
    el.addEventListener("change", handler);
  });
}

async function patchSubtask(subtaskId, payload) {
  const res = await fetch(`/api/v1/project-tasks/subtasks/${encodeURIComponent(subtaskId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data.subtask;
}

async function addSubtask(taskId, title, assignedUserId, labels, lang) {
  const payload = { title };
  if (assignedUserId) payload.assigned_user_id = Number(assignedUserId);
  const res = await fetch(`/api/v1/project-tasks/tasks/${encodeURIComponent(taskId)}/subtasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  await loadBoard(getProjectSlug(), labels, lang);
  if (typeof toast === "function") toast(labels.saved || "Saved", "success");
}

function bindTaskEvents(labels, lang) {
  document.querySelectorAll(".task-move-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const id = sel.dataset.taskId;
      const card = sel.closest(".project-task-card");
      const targetCol = document.querySelector(`.kanban-column-body[data-drop-status="${sel.value}"]`);
      try {
        await patchTask(id, { status: sel.value });
        if (card && targetCol) targetCol.appendChild(card);
        if (typeof toast === "function") toast(labels.saved || "Saved", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-priority-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      try {
        await patchTask(sel.dataset.taskId, { priority: sel.value });
        await loadBoard(getProjectSlug(), labels, lang);
        if (typeof toast === "function") toast(labels.saved || "Saved", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-assignee-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const val = sel.value ? Number(sel.value) : null;
      try {
        await patchTask(sel.dataset.taskId, { assigned_user_id: val });
        await loadBoard(getProjectSlug(), labels, lang);
        if (typeof toast === "function") toast(labels.saved || "Saved", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  bindDebouncedPatch(".task-notes", "notes");
  bindDebouncedPatch(".task-tags-input", "tags");

  document.querySelectorAll(".task-subtask-check").forEach((cb) => {
    cb.addEventListener("change", async () => {
      try {
        await patchSubtask(cb.dataset.subtaskId, { done: cb.checked });
        cb.closest(".task-subtask-item")?.classList.toggle("done", cb.checked);
        await loadBoard(getProjectSlug(), labels, lang);
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-subtask-assign").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const val = sel.value ? Number(sel.value) : null;
      try {
        await patchSubtask(sel.dataset.subtaskId, { assigned_user_id: val });
        if (typeof toast === "function") toast(labels.saved || "Saved", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-subtask-add-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const taskId = btn.dataset.taskId;
      const input = document.querySelector(`.task-subtask-input[data-task-id="${taskId}"]`);
      const assignSel = document.querySelector(`.task-subtask-new-assign[data-task-id="${taskId}"]`);
      const title = input?.value?.trim();
      if (!title) return;
      try {
        await addSubtask(taskId, title, assignSel?.value, labels, lang);
        if (input) input.value = "";
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-subtask-input").forEach((input) => {
    input.addEventListener("keydown", async (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const taskId = input.dataset.taskId;
      const assignSel = document.querySelector(`.task-subtask-new-assign[data-task-id="${taskId}"]`);
      const title = input.value?.trim();
      if (!title) return;
      try {
        await addSubtask(taskId, title, assignSel?.value, labels, lang);
        input.value = "";
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-subtask-delete").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!window.confirm(labels.subtask_delete_confirm || "Delete subtask?")) return;
      try {
        const res = await fetch(`/api/v1/project-tasks/subtasks/${encodeURIComponent(btn.dataset.subtaskId)}`, {
          method: "DELETE",
          credentials: "same-origin",
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        await loadBoard(getProjectSlug(), labels, lang);
        if (typeof toast === "function") toast(labels.deleted || "Deleted", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".task-delete-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!window.confirm(labels.task_delete_confirm || "Delete this task?")) return;
      try {
        const res = await fetch(`/api/v1/project-tasks/tasks/${encodeURIComponent(btn.dataset.taskId)}`, {
          method: "DELETE",
          credentials: "same-origin",
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        __tasksCache.items = (__tasksCache.items || []).filter((t) => t.id !== btn.dataset.taskId);
        document.querySelector(`.project-task-card[data-task-id="${btn.dataset.taskId}"]`)?.remove();
        if (typeof toast === "function") toast(labels.deleted || "Deleted", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });

  document.querySelectorAll(".project-task-card").forEach((card) => {
    card.addEventListener("dragstart", (e) => {
      card.classList.add("dragging");
      e.dataTransfer?.setData("text/plain", card.dataset.taskId || "");
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });

  document.querySelectorAll(".kanban-column-body").forEach((col) => {
    col.addEventListener("dragover", (e) => {
      e.preventDefault();
      col.classList.add("drag-over");
    });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async (e) => {
      e.preventDefault();
      col.classList.remove("drag-over");
      const taskId = e.dataTransfer?.getData("text/plain");
      const status = col.dataset.dropStatus;
      if (!taskId || !status) return;
      const card = document.querySelector(`.project-task-card[data-task-id="${taskId}"]`);
      try {
        await patchTask(taskId, { status });
        if (card) col.appendChild(card);
        const sel = card?.querySelector(".task-move-select");
        if (sel) sel.value = status;
        if (typeof toast === "function") toast(labels.saved || "Saved", "success");
      } catch (err) {
        if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
      }
    });
  });
}

async function loadBoard(slug, labels, lang) {
  const root = document.getElementById("project-tasks-root");
  if (!slug) {
    if (root) root.innerHTML = `<p class="muted">${labels.select_project || ""}</p>`;
    return;
  }
  if (root) root.textContent = "…";
  const res = await fetch(`/api/v1/project-tasks/board?project_slug=${encodeURIComponent(slug)}`, {
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  renderBoard(data, labels, lang);
}

document.addEventListener("DOMContentLoaded", () => {
  const labels = window.PROJECT_TASKS_LABELS || {};
  const lang = getLang();
  const form = document.getElementById("form-add-task");
  const hint = document.getElementById("project-tasks-hint");

  const refresh = async () => {
    const slug = getProjectSlug();
    if (hint) hint.classList.toggle("hidden", !!slug);
    if (form) form.classList.toggle("hidden", !slug);
    try {
      await loadBoard(slug, labels, lang);
    } catch (err) {
      const root = document.getElementById("project-tasks-root");
      if (root) root.innerHTML = `<p class="result-error">${escapeHtml(err.message)}</p>`;
    }
  };

  refresh();
  document.getElementById("global-project-select")?.addEventListener("change", refresh);

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const slug = getProjectSlug();
    if (!slug) {
      if (typeof toast === "function") toast(labels.select_project || "Select project", "error");
      return;
    }
    const title = document.getElementById("task-new-title")?.value?.trim();
    if (!title) {
      if (typeof toast === "function") toast(labels.add_title_required || "Title required", "error");
      return;
    }
    const payload = {
      project_slug: slug,
      title,
    };

    try {
      const res = await fetch("/api/v1/project-tasks/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      form.reset();
      document.getElementById("task-new-title")?.focus();
      await loadBoard(slug, labels, lang);
      if (typeof toast === "function") toast(labels.saved || "Saved", "success");
    } catch (err) {
      if (typeof toast === "function") toast(`${labels.error || "Error"}: ${err.message}`, "error");
    }
  });
});
