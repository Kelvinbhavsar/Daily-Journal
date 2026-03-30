/* global window, document, fetch, setTimeout, clearTimeout */

const ACCENTS = window.__ACCENTS__ || {};
const FONTS = window.__FONTS__ || [];
const INITIAL = window.__INITIAL__ || {};

const els = {
  appTitle: document.getElementById("appTitle"),
  accent: document.getElementById("accent"),
  font: document.getElementById("font"),
  newCategory: document.getElementById("newCategory"),
  newTopic: document.getElementById("newTopic"),
  categoryList: document.getElementById("categoryList"),
  topicList: document.getElementById("topicList"),
  topicTitle: document.getElementById("topicTitle"),
  topicContent: document.getElementById("topicContent"),
  saveStatus: document.getElementById("saveStatus"),
  deleteTopic: document.getElementById("deleteTopic"),
};

let state = null;
let saveTimer = null;
let dirty = false;
let lastSavedAt = null;

function setStatus(text) {
  els.saveStatus.textContent = text;
}

function setAccent(accentKey) {
  const hex = ACCENTS[accentKey] || ACCENTS.indigo || "#3F51B5";
  document.documentElement.style.setProperty("--accent", hex);
  document.documentElement.style.setProperty("--accent-weak", hexToRgba(hex, 0.14));
}

function setFont(fontKey) {
  const font = FONTS.find((f) => f.key === fontKey) || FONTS[0];
  if (!font) return;
  document.documentElement.style.setProperty("--font", font.css);
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

function selectedCategoryId() {
  return state?.selected?.category_id || null;
}

function selectedTopicId() {
  return state?.selected?.topic_id || null;
}

function topicsForCategory(categoryId) {
  return (state?.topics || []).filter((t) => t.category_id === categoryId);
}

function getTopicById(topicId) {
  return (state?.topics || []).find((t) => t.id === topicId) || null;
}

function renderCategories() {
  const cats = state?.categories || [];
  const activeId = selectedCategoryId();
  els.categoryList.innerHTML = cats
    .map((c) => {
      const count = topicsForCategory(c.id).length;
      const active = c.id === activeId ? " item--active" : "";
      return `
        <div class="item${active}" data-action="select-category" data-id="${escapeHtml(c.id)}">
          <div class="item__main">
            <div class="item__title">${escapeHtml(c.name)}</div>
            <div class="item__sub">Major category</div>
          </div>
          <div class="chip">${count}</div>
        </div>
      `;
    })
    .join("");
}

function renderTopics() {
  const catId = selectedCategoryId();
  const list = catId ? topicsForCategory(catId) : [];
  const activeId = selectedTopicId();
  els.topicList.innerHTML = list
    .map((t) => {
      const active = t.id === activeId ? " item--active" : "";
      const preview = (t.content || "").trim().split("\n")[0] || "No content yet";
      return `
        <div class="item${active}" data-action="select-topic" data-id="${escapeHtml(t.id)}">
          <div class="item__main">
            <div class="item__title">${escapeHtml(t.title || "Untitled")}</div>
            <div class="item__sub">${escapeHtml(preview)}</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderEditor() {
  const topic = getTopicById(selectedTopicId());
  els.topicTitle.value = topic?.title || "";
  els.topicContent.value = topic?.content || "";
  els.deleteTopic.disabled = !topic;
}

function applyAppearanceFromState() {
  els.accent.value = state?.accent || "indigo";
  els.font.value = state?.font || (FONTS[0]?.key ?? "fredoka");
  setAccent(els.accent.value);
  setFont(els.font.value);
  els.appTitle.value = state?.app_title || "Trading journal";
  document.title = els.appTitle.value;
}

function markDirty() {
  dirty = true;
  setStatus("Unsaved…");
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    void autosave();
  }, 700);
}

async function autosave() {
  if (!dirty) return;
  const topicId = selectedTopicId();
  const topic = getTopicById(topicId);
  if (!topic) return;

  setStatus("Saving…");
  const updated = await api(`/api/topics/${encodeURIComponent(topicId)}`, {
    method: "PUT",
    body: {
      title: els.topicTitle.value,
      content: els.topicContent.value,
    },
  });
  state = updated;
  dirty = false;
  lastSavedAt = new Date();
  setStatus(`Saved ${lastSavedAt.toLocaleTimeString()}`);
  renderTopics();
}

async function refresh() {
  state = await api("/api/state");
  applyAppearanceFromState();
  renderCategories();
  renderTopics();
  renderEditor();
  setStatus(state?.updated_at ? `Loaded` : "Ready");
}

function fillSelectOptions() {
  els.accent.innerHTML = Object.keys(ACCENTS)
    .map((k) => `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`)
    .join("");
  els.font.innerHTML = FONTS.map((f) => `<option value="${escapeHtml(f.key)}">${escapeHtml(f.label)}</option>`).join("");

  els.accent.value = INITIAL.accent || "indigo";
  els.font.value = INITIAL.font || (FONTS[0]?.key ?? "fredoka");
}

async function saveSettings() {
  const payload = {
    app_title: els.appTitle.value,
    accent: els.accent.value,
    font: els.font.value,
  };
  state = await api("/api/settings", { method: "POST", body: payload });
  applyAppearanceFromState();
  setStatus("Saved settings");
}

async function createCategory() {
  const name = prompt("Category name?");
  if (!name) return;
  state = await api("/api/categories", { method: "POST", body: { name } });
  renderCategories();
  renderTopics();
  renderEditor();
  setStatus("Created category");
}

async function createTopic() {
  const catId = selectedCategoryId();
  if (!catId) return;
  const title = prompt("Subtopic title?") || "Untitled";
  state = await api("/api/topics", { method: "POST", body: { category_id: catId, title } });
  renderTopics();
  renderEditor();
  setStatus("Created subtopic");
}

async function deleteSelectedTopic() {
  const topicId = selectedTopicId();
  if (!topicId) return;
  if (!confirm("Delete this subtopic?")) return;
  state = await api(`/api/topics/${encodeURIComponent(topicId)}`, { method: "DELETE" });
  dirty = false;
  renderTopics();
  renderEditor();
  setStatus("Deleted");
}

async function selectCategory(categoryId) {
  state = await api("/api/select", { method: "POST", body: { category_id: categoryId } });
  dirty = false;
  renderCategories();
  renderTopics();
  renderEditor();
}

async function selectTopic(topicId) {
  state = await api("/api/select", { method: "POST", body: { topic_id: topicId } });
  dirty = false;
  renderTopics();
  renderEditor();
}

function handleListClick(ev) {
  const target = ev.target.closest("[data-action]");
  if (!target) return;
  const action = target.getAttribute("data-action");
  const id = target.getAttribute("data-id");
  if (!id) return;
  if (action === "select-category") void selectCategory(id);
  if (action === "select-topic") void selectTopic(id);
}

function bind() {
  fillSelectOptions();
  els.categoryList.addEventListener("click", handleListClick);
  els.topicList.addEventListener("click", handleListClick);

  els.accent.addEventListener("change", () => {
    setAccent(els.accent.value);
    void saveSettings();
  });
  els.font.addEventListener("change", () => {
    setFont(els.font.value);
    void saveSettings();
  });

  els.appTitle.addEventListener("input", () => {
    document.title = els.appTitle.value || "Trading journal";
  });
  els.appTitle.addEventListener("change", () => {
    void saveSettings();
  });

  els.newCategory.addEventListener("click", () => void createCategory());
  els.newTopic.addEventListener("click", () => void createTopic());
  els.deleteTopic.addEventListener("click", () => void deleteSelectedTopic());

  els.topicTitle.addEventListener("input", () => markDirty());
  els.topicContent.addEventListener("input", () => markDirty());
}

bind();
refresh().catch((err) => {
  setStatus("Failed to load");
  console.error(err);
});

