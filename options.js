const STORAGE_KEY = "routingRules";
const WINDOWS_RESERVED_NAMES = new Set([
  "con",
  "prn",
  "aux",
  "nul",
  "com1",
  "com2",
  "com3",
  "com4",
  "com5",
  "com6",
  "com7",
  "com8",
  "com9",
  "lpt1",
  "lpt2",
  "lpt3",
  "lpt4",
  "lpt5",
  "lpt6",
  "lpt7",
  "lpt8",
  "lpt9"
]);

const state = {
  rules: [],
  editingId: null
};

const elements = {
  form: document.getElementById("ruleForm"),
  formTitle: document.getElementById("formTitle"),
  status: document.getElementById("status"),
  emptyState: document.getElementById("emptyState"),
  ruleList: document.getElementById("ruleList"),
  newRuleButton: document.getElementById("newRuleButton"),
  resetButton: document.getElementById("resetButton"),
  enabled: document.getElementById("enabled"),
  name: document.getElementById("name"),
  category: document.getElementById("category"),
  domains: document.getElementById("domains"),
  keywords: document.getElementById("keywords")
};

initialize().catch((error) => {
  console.error("TidyPaper options failed to initialize", error);
  setStatus("Failed to load rules.", "error");
});

async function initialize() {
  bindEvents();
  await loadRules();
  render();
  resetForm();
}

function bindEvents() {
  elements.form.addEventListener("submit", onSubmit);
  elements.newRuleButton.addEventListener("click", () => resetForm());
  elements.resetButton.addEventListener("click", () => resetForm());
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName !== "local" || !changes[STORAGE_KEY]) {
      return;
    }

    state.rules = normalizeRules(changes[STORAGE_KEY].newValue);
    if (state.editingId && !state.rules.some((rule) => rule.id === state.editingId)) {
      resetForm();
    }
    render();
  });
}

async function loadRules() {
  const stored = await chrome.storage.local.get({
    [STORAGE_KEY]: []
  });
  state.rules = normalizeRules(stored[STORAGE_KEY]);
}

async function onSubmit(event) {
  event.preventDefault();

  const domains = normalizeDomainList(elements.domains.value);
  const keywords = normalizeKeywordList(elements.keywords.value);
  const category = sanitizePathSegment(elements.category.value);
  const name = elements.name.value.trim();
  if (!category) {
    setStatus("Category is required.", "error");
    elements.category.focus();
    return;
  }

  if (domains.length === 0 && keywords.length === 0) {
    setStatus("Add at least one domain or keyword.", "error");
    elements.domains.focus();
    return;
  }

  const rule = {
    id: state.editingId || createRuleId(),
    enabled: elements.enabled.checked,
    name,
    category,
    domains,
    keywords
  };

  const existingIndex = state.rules.findIndex((item) => item.id === rule.id);
  if (existingIndex >= 0) {
    state.rules.splice(existingIndex, 1, rule);
  } else {
    state.rules.push(rule);
  }

  await saveRules();
  setStatus(existingIndex >= 0 ? "Rule updated." : "Rule saved.", "success");
  state.editingId = rule.id;
  render();
  populateForm(rule);
}

async function saveRules() {
  await chrome.storage.local.set({
    [STORAGE_KEY]: state.rules
  });
}

function render() {
  elements.ruleList.textContent = "";
  elements.emptyState.hidden = state.rules.length > 0;

  state.rules.forEach((rule, index) => {
    const item = document.createElement("li");
    item.className = "rule-card";

    const top = document.createElement("div");
    top.className = "rule-top";

    const summary = document.createElement("div");

    const titleRow = document.createElement("div");
    titleRow.className = "rule-title-row";

    const title = document.createElement("h3");
    title.textContent = rule.name || rule.category;

    const badge = document.createElement("span");
    badge.className = `badge${rule.enabled ? "" : " disabled"}`;
    badge.textContent = rule.enabled ? "Enabled" : "Disabled";

    titleRow.append(title, badge);
    summary.append(titleRow);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.append(
      buildMetaLine(`Category: ${rule.category}`),
      buildMetaLine(`Domains: ${rule.domains.length > 0 ? rule.domains.join(", ") : "Any"}`),
      buildMetaLine(`Keywords: ${rule.keywords.length > 0 ? rule.keywords.join(", ") : "Any"}`),
      buildMetaLine(`Target: Papers/${rule.category}/<year>/`)
    );
    summary.append(meta);

    const actions = document.createElement("div");
    actions.className = "rule-actions";
    actions.append(
      buildButton("Edit", "secondary-button", () => populateForm(rule)),
      buildButton("Up", "secondary-button", () => moveRule(index, -1), index === 0),
      buildButton("Down", "secondary-button", () => moveRule(index, 1), index === state.rules.length - 1),
      buildButton(rule.enabled ? "Disable" : "Enable", "secondary-button", () => toggleRule(rule.id)),
      buildButton("Delete", "danger-button", () => removeRule(rule.id))
    );

    top.append(summary, actions);
    item.append(top);
    elements.ruleList.append(item);
  });
}

function buildMetaLine(text) {
  const line = document.createElement("p");
  line.textContent = text;
  return line;
}

function buildButton(label, className, onClick, disabled = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.disabled = disabled;
  button.addEventListener("click", onClick);
  return button;
}

function populateForm(rule) {
  state.editingId = rule.id;
  elements.formTitle.textContent = "Edit Rule";
  elements.enabled.checked = rule.enabled;
  elements.name.value = rule.name;
  elements.category.value = rule.category;
  elements.domains.value = rule.domains.join(", ");
  elements.keywords.value = rule.keywords.join(", ");
  elements.category.focus();
}

function resetForm() {
  state.editingId = null;
  elements.formTitle.textContent = "Create Rule";
  elements.form.reset();
  elements.enabled.checked = true;
  clearStatus();
}

async function moveRule(index, delta) {
  const nextIndex = index + delta;
  if (nextIndex < 0 || nextIndex >= state.rules.length) {
    return;
  }

  const [rule] = state.rules.splice(index, 1);
  state.rules.splice(nextIndex, 0, rule);
  await saveRules();
  setStatus("Rule order updated.", "success");
  render();
}

async function toggleRule(ruleId) {
  const rule = state.rules.find((item) => item.id === ruleId);
  if (!rule) {
    return;
  }

  rule.enabled = !rule.enabled;
  await saveRules();
  if (state.editingId === ruleId) {
    populateForm(rule);
  }
  setStatus(rule.enabled ? "Rule enabled." : "Rule disabled.", "success");
  render();
}

async function removeRule(ruleId) {
  const rule = state.rules.find((item) => item.id === ruleId);
  if (!rule || !window.confirm(`Delete rule "${rule.name || rule.category}"?`)) {
    return;
  }

  state.rules = state.rules.filter((item) => item.id !== ruleId);
  await saveRules();
  if (state.editingId === ruleId) {
    resetForm();
  }
  setStatus("Rule deleted.", "success");
  render();
}

function setStatus(message, tone) {
  elements.status.textContent = message;
  elements.status.dataset.tone = tone || "";
}

function clearStatus() {
  elements.status.textContent = "";
  elements.status.dataset.tone = "";
}

function normalizeRules(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((rule) => normalizeRule(rule))
    .filter(Boolean);
}

function normalizeRule(rule) {
  if (!rule || typeof rule !== "object") {
    return null;
  }

  const category = sanitizePathSegment(rule.category);
  const domains = normalizeDomainList(rule.domains);
  const keywords = normalizeKeywordList(rule.keywords);
  if (!category || (domains.length === 0 && keywords.length === 0)) {
    return null;
  }

  return {
    id: typeof rule.id === "string" && rule.id ? rule.id : createRuleId(),
    enabled: rule.enabled !== false,
    name: typeof rule.name === "string" ? rule.name.trim() : "",
    category,
    domains,
    keywords
  };
}

function normalizeDomainList(value) {
  return normalizeList(value).map((entry) => normalizeDomain(entry)).filter(Boolean);
}

function normalizeKeywordList(value) {
  return normalizeList(value).map((entry) => entry.toLowerCase()).filter(Boolean);
}

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value
      .map((entry) => (typeof entry === "string" ? entry.trim() : ""))
      .filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  return [];
}

function normalizeDomain(domain) {
  const normalized = domain.toLowerCase().trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  return normalized.replace(/^\.+|\.+$/g, "");
}

function sanitizePathSegment(value) {
  const sanitized = String(value || "")
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");
  if (!sanitized) {
    return "";
  }

  const normalized = sanitized.replace(/[- ]+/g, " ").trim();
  const stem = normalized.toLowerCase();
  if (WINDOWS_RESERVED_NAMES.has(stem)) {
    return `paper ${normalized}`;
  }

  return normalized;
}

function createRuleId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `rule-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
