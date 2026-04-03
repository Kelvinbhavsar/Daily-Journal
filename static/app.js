/* global window, document, fetch, setTimeout, clearTimeout, navigator */

const ACCENTS = window.__ACCENTS__ || {};
const FONTS = window.__FONTS__ || [];

const STATIC_SEGMENTS = [
  { key: "personal", label: "Personal", tone: "#8B5CF6", soft: "rgba(139, 92, 246, 0.18)", icon: "handshake" },
  { key: "professional", label: "Professional", tone: "#3B82F6", soft: "rgba(59, 130, 246, 0.18)", icon: "chart" },
  { key: "spiritual", label: "Spiritual", tone: "#FBBF24", soft: "rgba(251, 191, 36, 0.18)", icon: "lotus" },
  { key: "financial", label: "Financial", tone: "#22C55E", soft: "rgba(34, 197, 94, 0.18)", icon: "coins" },
  { key: "emotional", label: "Emotional", tone: "#EF4444", soft: "rgba(239, 68, 68, 0.18)", icon: "heart" },
];

const els = {
  appTitle: document.getElementById("appTitle"),
  subbar: document.getElementById("subbar"),
  themeToggle: document.getElementById("themeToggle"),
  modalLayer: document.getElementById("modalLayer"),
  modalBackdrop: document.getElementById("modalBackdrop"),
  modalTitle: document.getElementById("modalTitle"),
  modalMessage: document.getElementById("modalMessage"),
  modalInputWrap: document.getElementById("modalInputWrap"),
  modalInputLabel: document.getElementById("modalInputLabel"),
  modalInput: document.getElementById("modalInput"),
  modalCancel: document.getElementById("modalCancel"),
  modalConfirm: document.getElementById("modalConfirm"),
  homeToggle: document.getElementById("homeToggle"),
  breadcrumb: document.getElementById("breadcrumb"),
  homeView: document.getElementById("homeView"),
  detailView: document.getElementById("detailView"),
  segmentGrid: document.getElementById("segmentGrid"),
  statsSummary: document.getElementById("statsSummary"),
  statsDetail: document.getElementById("statsDetail"),
  openTrash: document.getElementById("openTrash"),
  closeTrash: document.getElementById("closeTrash"),
  emptyTrash: document.getElementById("emptyTrash"),
  trashPanel: document.getElementById("trashPanel"),
  trashList: document.getElementById("trashList"),
  detailSummary: document.getElementById("detailSummary"),
  backToHome: document.getElementById("backToHome"),
  categoryList: document.getElementById("categoryList"),
  topicList: document.getElementById("topicList"),
  topicTitle: document.getElementById("topicTitle"),
  topicContent: document.getElementById("topicContent"),
  saveStatus: document.getElementById("saveStatus"),
  undoBtn: document.getElementById("undoBtn"),
  redoBtn: document.getElementById("redoBtn"),
  saveNowBtn: document.getElementById("saveNowBtn"),
  accent: document.getElementById("accent"),
  font: document.getElementById("font"),
  newCategory: document.getElementById("newCategory"),
  newTopic: document.getElementById("newTopic"),
};

let state = null;
let viewMode = "home";
let trashOpen = false;
let saveTimer = null;
let dirty = false;
let lastSavedAt = null;
let historyDebounce = null;
let history = { topicId: null, undo: [], redo: [], last: null };
let modalState = null;

const AUTOSAVE_MS = 5 * 60 * 1000;
const HISTORY_DEBOUNCE_MS = 400;
const HISTORY_LIMIT = 120;

function setStatus(text) {
  els.saveStatus.textContent = text;
}

function closeModal(result = null) {
  if (!modalState) return;
  const current = modalState;
  modalState = null;
  els.modalLayer.classList.add("modalLayer--hidden");
  els.modalLayer.setAttribute("aria-hidden", "true");
  els.modalInputWrap.classList.add("modalShell__field--hidden");
  current.resolve(result);
}

function openModal({
  title,
  message = "",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  inputLabel = "",
  inputValue = "",
  inputPlaceholder = "",
  requireInput = false,
}) {
  return new Promise((resolve) => {
    modalState = { resolve, requireInput };
    els.modalTitle.textContent = title;
    els.modalMessage.textContent = message;
    els.modalConfirm.textContent = confirmLabel;
    els.modalCancel.textContent = cancelLabel;
    els.modalInputLabel.textContent = inputLabel;
    els.modalInput.value = inputValue;
    els.modalInput.placeholder = inputPlaceholder;
    els.modalInputWrap.classList.toggle("modalShell__field--hidden", !requireInput);
    els.modalLayer.classList.remove("modalLayer--hidden");
    els.modalLayer.setAttribute("aria-hidden", "false");
    if (requireInput) {
      setTimeout(() => {
        els.modalInput.focus();
        els.modalInput.select();
      }, 0);
    } else {
      setTimeout(() => {
        els.modalConfirm.focus();
      }, 0);
    }
  });
}

async function promptModal(options) {
  const result = await openModal({ ...options, requireInput: true });
  if (!result || !result.confirmed) return null;
  return result.value;
}

async function confirmModal(options) {
  const result = await openModal(options);
  return !!(result && result.confirmed);
}

function setAccent(accentKey) {
  const hex = ACCENTS[accentKey] || ACCENTS.orange || "#FF9800";
  document.documentElement.style.setProperty("--accent", hex);
  document.documentElement.style.setProperty("--accent-weak", hexToRgba(hex, 0.15));
}

function setFont(fontKey) {
  const font = FONTS.find((f) => f.key === fontKey) || FONTS[0];
  if (font) document.documentElement.style.setProperty("--font", font.css);
}

function themeIcon(mode) {
  if (mode === "dark") {
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path></svg>`;
  }
  return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"></path></svg>`;
}

function setTheme(mode) {
  const theme = mode === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
  els.themeToggle.innerHTML = themeIcon(theme);
  els.themeToggle.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
}

function hexToRgba(hex, alpha) {
  const clean = String(hex).replace("#", "");
  const bigint = parseInt(clean, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `Request failed: ${res.status}`);
  }
  return await res.json();
}

function selectedSegmentKey() {
  return state?.selected?.segment_key || "financial";
}

function selectedCategoryId() {
  return state?.selected?.category_id || null;
}

function selectedTopicId() {
  return state?.selected?.topic_id || null;
}

function categoriesForSegment(segmentKey) {
  return (state?.categories || []).filter((category) => category.segment_key === segmentKey);
}

function topicsForCategory(categoryId) {
  return (state?.topics || []).filter((topic) => topic.category_id === categoryId);
}

function getSegment(segmentKey) {
  return STATIC_SEGMENTS.find((segment) => segment.key === segmentKey) || STATIC_SEGMENTS[3];
}

function getCategoryById(categoryId) {
  return (state?.categories || []).find((category) => category.id === categoryId) || null;
}

function getTopicById(topicId) {
  return (state?.topics || []).find((topic) => topic.id === topicId) || null;
}

function visibleTrashTopics() {
  return (state?.trash?.topics || []).filter((topic) => !topic.deleted_with_category_id);
}

function trashCategories() {
  return state?.trash?.categories || [];
}

function initialsForLabel(label) {
  return String(label || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() || "")
    .join("") || "SG";
}

function iconMarkup(name, color) {
  const common = `stroke="${color}" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  if (name === "chart") return `<svg viewBox="0 0 64 64" aria-hidden="true"><path ${common} d="M12 50H52"/><path ${common} d="M18 44V34"/><path ${common} d="M30 44V26"/><path ${common} d="M42 44V18"/><path ${common} d="M18 24L29 15L38 21L49 10"/></svg>`;
  if (name === "lotus") return `<svg viewBox="0 0 64 64" aria-hidden="true"><path ${common} d="M32 50C22 45 18 36 21 28C27 30 31 35 32 43"/><path ${common} d="M32 50C42 45 46 36 43 28C37 30 33 35 32 43"/><path ${common} d="M32 49C36 43 37 36 32 18C27 36 28 43 32 49"/><path ${common} d="M16 48C22 47 27 44 30 38"/><path ${common} d="M48 48C42 47 37 44 34 38"/></svg>`;
  if (name === "coins") return `<svg viewBox="0 0 64 64" aria-hidden="true"><ellipse ${common} cx="23" cy="39" rx="11" ry="5"/><path ${common} d="M12 39V47C12 49.8 17 52 23 52S34 49.8 34 47V39"/><ellipse ${common} cx="41" cy="27" rx="11" ry="5"/><path ${common} d="M30 27V35C30 37.8 35 40 41 40S52 37.8 52 35V27"/><path ${common} d="M30 35C30 37.8 35 40 41 40S52 37.8 52 35"/></svg>`;
  if (name === "heart") return `<svg viewBox="0 0 64 64" aria-hidden="true"><path ${common} d="M32 51C18 42 12 34 12 25C12 18 17 13 24 13C28 13 31 15 32 19C33 15 36 13 40 13C47 13 52 18 52 25C52 34 46 42 32 51Z"/><path ${common} d="M24 36C27 32 30 31 33 33C36 35 39 34 42 30"/></svg>`;
  return `<svg viewBox="0 0 64 64" aria-hidden="true"><path ${common} d="M15 32H22L28 24L36 40L42 32H49"/><path ${common} d="M18 20V44"/><path ${common} d="M46 20V44"/></svg>`;
}

function renderStats() {
  const mainThreads = state?.categories || [];
  const topics = state?.topics || [];
  els.statsSummary.textContent = `${topics.length} total ${topics.length === 1 ? "entry" : "entries"}`;
  const trashCount = trashCategories().length + visibleTrashTopics().length;
  els.statsDetail.textContent = `${mainThreads.length} ${mainThreads.length === 1 ? "main thread" : "main threads"} • ${trashCount} in trash`;
}

function renderSegments() {
  const activeSegment = selectedSegmentKey();
  els.segmentGrid.innerHTML = STATIC_SEGMENTS.map((segment) => {
    const segmentCategories = categoriesForSegment(segment.key);
    const segmentTopics = segmentCategories.flatMap((category) => topicsForCategory(category.id));
    const active = segment.key === activeSegment ? " segmentCard--active" : "";
    return `
      <button
        class="segmentCard${active}"
        type="button"
        data-action="open-segment"
        data-id="${escapeHtml(segment.key)}"
        style="--segment-tone:${segment.tone};--segment-soft:${segment.soft};--segment-ring:${segment.tone};"
      >
        <div class="segmentCard__title">${escapeHtml(segment.label)}</div>
        <div class="segmentCard__ring">
          <div class="segmentCard__icon">${iconMarkup(segment.icon, segment.tone)}</div>
        </div>
        <div class="segmentCard__footer">
          <span class="segmentCard__count">${segmentCategories.length} main threads • ${segmentTopics.length} topics</span>
        </div>
      </button>
    `;
  }).join("");
}

function renderDetailSummary() {
  const segment = getSegment(selectedSegmentKey());
  const segmentCategories = categoriesForSegment(segment.key);
  const subcategoryCount = segmentCategories.reduce((sum, category) => sum + topicsForCategory(category.id).length, 0);
  // els.detailSummary.innerHTML = `
  //   <div class="segmentSummary__badge" style="--summary-tone:${segment.tone};--summary-soft:${segment.soft};">
  //     ${escapeHtml(initialsForLabel(segment.label))}
  //   </div>
  //   <div class="segmentSummary__content">
  //     <div class="segmentSummary__eyebrow">Static Category</div>
  //     <div class="segmentSummary__title">${escapeHtml(segment.label)}</div>
  //     <div class="segmentSummary__meta">${segmentCategories.length} user categories • ${subcategoryCount} subcategories</div>
  //   </div>
  // `;
}

function renderCategoryList() {
  const activeCategoryId = selectedCategoryId();
  const categories = categoriesForSegment(selectedSegmentKey());
  els.categoryList.innerHTML = categories.map((category) => {
    const topicCount = topicsForCategory(category.id).length;
    const active = category.id === activeCategoryId ? " browserCard--active" : "";
    return `
      <div class="browserCard${active}" data-action="select-category" data-id="${escapeHtml(category.id)}" role="button" tabindex="0">
        <div class="browserCard__title">${escapeHtml(category.name)}</div>
        <div class="browserCard__meta">${topicCount} ${topicCount === 1 ? "topic" : "topics"}</div>
        <span class="cardDeleteWrap">
          <button class="cardDelete" type="button" data-action="delete-category" data-id="${escapeHtml(category.id)}" aria-label="Delete ${escapeHtml(category.name)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </button>
        </span>
      </div>
    `;
  }).join("");
}

function renderTopicList() {
  const activeTopicId = selectedTopicId();
  const topics = selectedCategoryId() ? topicsForCategory(selectedCategoryId()) : [];
  els.topicList.innerHTML = topics.map((topic) => {
    const active = topic.id === activeTopicId ? " browserCard--active" : "";
    const preview = (topic.content || "").trim().split("\n")[0] || "No content yet";
    return `
      <div class="browserCard browserCard--topic${active}" data-action="select-topic" data-id="${escapeHtml(topic.id)}" role="button" tabindex="0">
        <div class="browserCard__title">${escapeHtml(topic.title || "Untitled")}</div>
        <div class="browserCard__meta">${escapeHtml(preview)}</div>
        <span class="cardDeleteWrap">
          <button class="cardDelete" type="button" data-action="delete-topic" data-id="${escapeHtml(topic.id)}" aria-label="Delete ${escapeHtml(topic.title || "Untitled")}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </button>
        </span>
      </div>
    `;
  }).join("");
}

function renderTrash() {
  const items = [
    ...trashCategories().map((category) => {
      const childCount = (state?.trash?.topics || []).filter((topic) => topic.deleted_with_category_id === category.id).length;
      return {
        kind: "category",
        id: category.id,
        title: category.name,
        meta: `${category.segment_key || "financial"} segment • restores ${childCount} topics`,
      };
    }),
    ...visibleTrashTopics().map((topic) => ({
      kind: "topic",
      id: topic.id,
      title: topic.title || "Untitled",
      meta: "Deleted topic",
    })),
  ];

  els.trashPanel.classList.toggle("trashPanel--hidden", !trashOpen);
  els.trashList.innerHTML = items.length
    ? items.map((item) => `
      <div class="trashCard">
        <div>
          <div class="trashCard__title">${escapeHtml(item.title)}</div>
          <div class="trashCard__meta">${escapeHtml(item.meta)}</div>
        </div>
        <button class="cardRestore" type="button" data-action="restore-trash" data-kind="${escapeHtml(item.kind)}" data-id="${escapeHtml(item.id)}" aria-label="Restore ${escapeHtml(item.title)}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>
        </button>
      </div>
    `).join("")
    : `<div class="trashEmpty">Trash is empty right now.</div>`;
}

function renderEditor() {
  const topic = getTopicById(selectedTopicId());
  els.topicTitle.value = topic?.title || "";
  els.topicContent.value = topic?.content || "";
  els.topicTitle.disabled = !topic;
  els.topicContent.disabled = !topic;
  resetHistoryForTopic(topic?.id || null);
}

function renderBreadcrumb() {
  const segment = getSegment(selectedSegmentKey());
  const category = getCategoryById(selectedCategoryId());
  const topic = getTopicById(selectedTopicId());
  if (viewMode !== "detail") {
    els.breadcrumb.textContent = "Static Category • Main Thread • Topic";
    return;
  }
  const parts = [segment.label];
  if (category?.name) parts.push(category.name);
  if (topic?.title) parts.push(topic.title);
  els.breadcrumb.textContent = parts.join(" • ");
}

function setViewMode(nextMode) {
  viewMode = nextMode;
  const home = nextMode === "home";
  els.subbar.classList.toggle("subbar--hidden", home);
  els.homeView.classList.toggle("homeView--hidden", !home);
  els.detailView.classList.toggle("detailView--hidden", home);
  renderBreadcrumb();
}

function renderAll() {
  applyAppearanceFromState();
  renderStats();
  renderSegments();
  renderCategoryList();
  renderTopicList();
  renderTrash();
  renderEditor();
  renderBreadcrumb();
}

function applyAppearanceFromState() {
  els.accent.value = state?.accent || "orange";
  els.font.value = state?.font || (FONTS[0]?.key ?? "fredoka");
  setAccent(els.accent.value);
  setFont(els.font.value);
  setTheme(state?.theme || "light");
  els.appTitle.value = state?.app_title || "Daily-Journal";
  document.title = els.appTitle.value;
}

function currentSnapshot() {
  return { topicId: selectedTopicId(), title: els.topicTitle.value, content: els.topicContent.value };
}

function sameSnapshot(a, b) {
  return !!(a && b && a.topicId === b.topicId && a.title === b.title && a.content === b.content);
}

function resetHistoryForTopic(topicId) {
  if (history.topicId === topicId) return;
  history = { topicId, undo: [], redo: [], last: null };
  if (topicId) {
    const snap = currentSnapshot();
    history.undo.push(snap);
    history.last = snap;
  }
  updateUndoRedoButtons();
}

function pushHistorySnapshot() {
  const snap = currentSnapshot();
  if (!snap.topicId) return;
  if (history.last && sameSnapshot(history.last, snap)) return;
  if (history.undo.length && sameSnapshot(history.undo[history.undo.length - 1], snap)) return;
  history.undo.push(snap);
  history.last = snap;
  history.redo = [];
  if (history.undo.length > HISTORY_LIMIT) history.undo.shift();
  updateUndoRedoButtons();
}

function scheduleHistorySnapshot() {
  if (historyDebounce) clearTimeout(historyDebounce);
  historyDebounce = setTimeout(pushHistorySnapshot, HISTORY_DEBOUNCE_MS);
}

function applySnapshot(snap) {
  if (!snap || snap.topicId !== selectedTopicId()) return;
  els.topicTitle.value = snap.title;
  els.topicContent.value = snap.content;
  history.last = snap;
  markDirty({ scheduleOnly: true });
  updateUndoRedoButtons();
}

function updateUndoRedoButtons() {
  els.undoBtn.disabled = history.undo.length < 2;
  els.redoBtn.disabled = history.redo.length < 1;
}

function doUndo() {
  if (history.undo.length < 2) return;
  const current = history.undo.pop();
  if (current) history.redo.push(current);
  applySnapshot(history.undo[history.undo.length - 1]);
}

function doRedo() {
  if (!history.redo.length) return;
  const next = history.redo.pop();
  history.undo.push(next);
  applySnapshot(next);
}

function markDirty({ scheduleOnly = false } = {}) {
  dirty = true;
  setStatus("Unsaved...");
  if (!scheduleOnly) scheduleHistorySnapshot();
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => void autosave(), AUTOSAVE_MS);
}

async function autosave({ force = false } = {}) {
  if (!dirty && !force) return;
  const topicId = selectedTopicId();
  if (!topicId) return;
  setStatus("Saving...");
  state = await api(`/api/topics/${encodeURIComponent(topicId)}`, {
    method: "PUT",
    body: { title: els.topicTitle.value, content: els.topicContent.value },
  });
  dirty = false;
  lastSavedAt = new Date();
  renderAll();
  setStatus(`Saved ${lastSavedAt.toLocaleTimeString()}`);
}

async function refresh() {
  state = await api("/api/state");
  renderAll();
  setViewMode("home");
  setStatus("Loaded");
}

function fillSelectOptions() {
  els.accent.innerHTML = Object.keys(ACCENTS).map((key) => `<option value="${escapeHtml(key)}">${escapeHtml(key)}</option>`).join("");
  els.font.innerHTML = FONTS.map((font) => `<option value="${escapeHtml(font.key)}">${escapeHtml(font.label)}</option>`).join("");
}

async function saveSettings() {
  state = await api("/api/settings", {
    method: "POST",
    body: { app_title: els.appTitle.value, accent: els.accent.value, font: els.font.value, theme: state?.theme || "light" },
  });
  renderAll();
  setStatus("Saved settings");
}

async function toggleTheme() {
  state = {
    ...state,
    theme: state?.theme === "dark" ? "light" : "dark",
  };
  setTheme(state.theme);
  state = await api("/api/settings", {
    method: "POST",
    body: {
      app_title: els.appTitle.value,
      accent: els.accent.value,
      font: els.font.value,
      theme: state.theme,
    },
  });
  renderAll();
  setStatus(`Switched to ${state.theme} mode`);
}

async function createCategory() {
  if (dirty) await autosave();
  const name = await promptModal({
    title: "Create Main Thread",
    message: "Give this main thread a clear name so you can find it quickly later.",
    confirmLabel: "Create",
    inputLabel: "Main thread name",
    inputPlaceholder: "Example: Weekly Review",
  });
  if (!name) return;
  state = await api("/api/categories", {
    method: "POST",
    body: { name, segment_key: selectedSegmentKey() },
  });
  renderAll();
  setViewMode("detail");
  setStatus("Created main thread");
}

async function createTopic() {
  if (dirty) await autosave();
  const categoryId = selectedCategoryId();
  if (!categoryId) {
    setStatus("Open a main thread first");
    return;
  }
  const title = (await promptModal({
    title: "Create Topic",
    message: "Add a topic inside the selected main thread.",
    confirmLabel: "Create",
    inputLabel: "Topic title",
    inputPlaceholder: "Example: April setup notes",
    inputValue: "Untitled",
  })) || "Untitled";
  state = await api("/api/topics", { method: "POST", body: { category_id: categoryId, title } });
  renderAll();
  setViewMode("detail");
  setStatus("Created topic");
}

async function deleteTopic(topicId) {
  if (dirty) await autosave();
  if (!topicId) return;
  const approved = await confirmModal({
    title: "Delete Topic",
    message: "This topic will move to the trash bin and can be restored until you empty it.",
    confirmLabel: "Delete",
  });
  if (!approved) return;
  state = await api(`/api/topics/${encodeURIComponent(topicId)}`, { method: "DELETE" });
  dirty = false;
  renderAll();
  setStatus("Moved to trash");
}

async function deleteCategory(categoryId) {
  if (dirty) await autosave();
  if (!categoryId) return;
  const approved = await confirmModal({
    title: "Delete Main Thread",
    message: "This main thread and all of its topics will move to the trash bin.",
    confirmLabel: "Delete",
  });
  if (!approved) return;
  state = await api(`/api/categories/${encodeURIComponent(categoryId)}`, { method: "DELETE" });
  dirty = false;
  renderAll();
  setStatus("Main thread moved to trash");
}

async function renameCategory(categoryId, nextName) {
  const name = String(nextName || "").trim();
  const category = getCategoryById(categoryId);
  if (!categoryId || !category) return;
  if (!name || name === category.name) return;
  if (dirty) await autosave();
  state = await api(`/api/categories/${encodeURIComponent(categoryId)}`, {
    method: "PUT",
    body: { name },
  });
  renderAll();
  setStatus("Main thread renamed");
}

async function openRenameCategoryModal(categoryId) {
  const category = getCategoryById(categoryId);
  if (!category) return;
  const name = await promptModal({
    title: "Rename Main Thread",
    message: "Update the name for this main thread.",
    confirmLabel: "Save",
    cancelLabel: "Cancel",
    inputLabel: "Main thread title",
    inputPlaceholder: "Example: Weekly Review",
    inputValue: category.name,
  });
  if (!name) return;
  await renameCategory(categoryId, name);
}

async function restoreTrash(kind, itemId) {
  if (!kind || !itemId) return;
  state = await api("/api/trash/restore", { method: "POST", body: { kind, id: itemId } });
  renderAll();
  setStatus("Restored from trash");
}

async function emptyTrash() {
  const approved = await confirmModal({
    title: "Empty Trash Bin",
    message: "This permanently removes every deleted main thread and topic from the trash bin.",
    confirmLabel: "Empty Bin",
  });
  if (!approved) return;
  state = await api("/api/trash/empty", { method: "POST" });
  renderAll();
  setStatus("Trash bin emptied");
}

async function openSegment(segmentKey) {
  if (dirty) await autosave();
  state = await api("/api/select", { method: "POST", body: { segment_key: segmentKey } });
  dirty = false;
  renderAll();
  setViewMode("detail");
}

async function selectCategory(categoryId) {
  if (dirty) await autosave();
  state = await api("/api/select", { method: "POST", body: { category_id: categoryId } });
  dirty = false;
  renderAll();
  setViewMode("detail");
}

async function selectTopic(topicId) {
  if (dirty) await autosave();
  state = await api("/api/select", { method: "POST", body: { topic_id: topicId } });
  dirty = false;
  renderAll();
  setViewMode("detail");
}

function handleClick(ev) {
  const target = ev.target.closest("[data-action]");
  if (!target) return;
  const action = target.getAttribute("data-action");
  const id = target.getAttribute("data-id");
  if (action === "open-segment") void openSegment(id);
  if (action === "select-category") void selectCategory(id);
  if (action === "select-topic") void selectTopic(id);
  if (action === "delete-category") {
    ev.preventDefault();
    ev.stopPropagation();
    void deleteCategory(id);
  }
  if (action === "delete-topic") {
    ev.preventDefault();
    ev.stopPropagation();
    void deleteTopic(id);
  }
  if (action === "restore-trash") {
    void restoreTrash(target.getAttribute("data-kind"), id);
  }
}

function bind() {
  fillSelectOptions();
  els.segmentGrid.addEventListener("click", handleClick);
  els.categoryList.addEventListener("click", handleClick);
  els.categoryList.addEventListener("dblclick", (ev) => {
    const card = ev.target.closest("[data-action='select-category']");
    if (!card || ev.target.closest(".cardDelete")) return;
    ev.preventDefault();
    ev.stopPropagation();
    void openRenameCategoryModal(card.getAttribute("data-id"));
  });
  els.topicList.addEventListener("click", handleClick);
  els.trashList.addEventListener("click", handleClick);

  els.homeToggle.addEventListener("click", async () => {
    if (dirty) await autosave();
    setViewMode("home");
  });
  els.backToHome.addEventListener("click", async () => {
    if (dirty) await autosave();
    setViewMode("home");
  });
  els.openTrash.addEventListener("click", async () => {
    if (dirty) await autosave();
    trashOpen = !trashOpen;
    renderTrash();
  });
  els.closeTrash.addEventListener("click", () => {
    trashOpen = false;
    renderTrash();
  });
  els.emptyTrash.addEventListener("click", () => void emptyTrash());
  els.modalBackdrop.addEventListener("click", () => closeModal({ confirmed: false }));
  els.modalCancel.addEventListener("click", () => closeModal({ confirmed: false }));
  els.modalConfirm.addEventListener("click", () => {
    if (!modalState) return;
    if (modalState.requireInput) {
      const value = els.modalInput.value.trim();
      if (!value) {
        els.modalInput.focus();
        return;
      }
      closeModal({ confirmed: true, value });
      return;
    }
    closeModal({ confirmed: true });
  });
  els.modalInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      els.modalConfirm.click();
    }
  });

  els.undoBtn.addEventListener("click", doUndo);
  els.redoBtn.addEventListener("click", doRedo);
  els.saveNowBtn.addEventListener("click", () => void autosave({ force: true }));
  els.newCategory.addEventListener("click", () => void createCategory());
  els.newTopic.addEventListener("click", () => void createTopic());
  els.themeToggle.addEventListener("click", () => void toggleTheme());

  els.accent.addEventListener("change", () => {
    setAccent(els.accent.value);
    void saveSettings();
  });
  els.font.addEventListener("change", () => {
    setFont(els.font.value);
    void saveSettings();
  });
  els.appTitle.addEventListener("input", () => {
    document.title = els.appTitle.value || "Daily-Journal";
  });
  els.appTitle.addEventListener("change", () => void saveSettings());

  els.topicTitle.addEventListener("input", () => markDirty());
  els.topicContent.addEventListener("input", () => markDirty());

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalState) {
      e.preventDefault();
      closeModal({ confirmed: false });
      return;
    }
    const isMac = navigator.platform.toLowerCase().includes("mac");
    const mod = isMac ? e.metaKey : e.ctrlKey;
    if (!mod) return;
    const key = (e.key || "").toLowerCase();
    if (key === "s") {
      e.preventDefault();
      void autosave({ force: true });
      return;
    }
    if (key === "z") {
      e.preventDefault();
      if (e.shiftKey) doRedo();
      else doUndo();
      return;
    }
    if (key === "y") {
      e.preventDefault();
      doRedo();
    }
  });
}

bind();
refresh().catch((err) => {
  setStatus("Failed to load");
  console.error(err);
});
