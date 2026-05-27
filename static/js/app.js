const STATUSES = ["New", "Contacted", "Qualified", "Proposal", "Closed-Won", "Closed-Lost"];

const state = {
  authMode: "login",
  view: "list",
  user: null,
  leads: [],
  stats: null,
  reminders: { stale: [], overdue: [] },
  draggedLeadId: null,
};

const $ = (selector) => document.querySelector(selector);

function createNode(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1] || "";
}

function currency(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);
}

function shortDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

function fullDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(date);
}

async function apiFetch(url, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  const csrf = getCookie("csrf_token");
  if (csrf) headers["X-CSRF-Token"] = decodeURIComponent(csrf);
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  let payload = { success: false, error: "Invalid server response." };
  try {
    payload = await response.json();
  } catch (_error) {
    payload = { success: response.ok };
  }
  if (!response.ok && !payload.error) {
    payload.error = "Something went wrong.";
  }
  payload.statusCode = response.status;
  return payload;
}

function showToast(message, tone = "info") {
  const container = $("#toast-container");
  const toast = createNode("div", `toast toast-${tone}`);
  const icon = createNode("span", "toast-icon", tone === "success" ? "✓" : tone === "error" ? "✕" : tone === "warn" ? "⚠" : "ℹ");
  const body = createNode("span", "toast-msg", String(message));
  const close = createNode("button", "toast-close", "✕");
  close.type = "button";
  close.addEventListener("click", () => toast.remove());
  toast.append(icon, body, close);
  container.appendChild(toast);
  window.setTimeout(() => toast.remove(), 5000);
}

function clearInvalid(fields) {
  fields.forEach((field) => field && field.classList.remove("invalid"));
}

function markInvalid(field, message) {
  if (field) {
    field.classList.add("invalid");
    field.focus();
  }
  showToast(message, "warn");
}

function validateAuthForm() {
  const username = $("#auth-username");
  const email = $("#auth-email");
  const password = $("#auth-password");
  clearInvalid([username, email, password]);

  if (!username.value.trim()) {
    markInvalid(username, "Username or email is required.");
    return false;
  }
  if (state.authMode === "register") {
    if (!/^[a-zA-Z0-9_-]{3,32}$/.test(username.value.trim())) {
      markInvalid(username, "Username must be 3-32 characters using letters, numbers, hyphens, or underscores.");
      return false;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim())) {
      markInvalid(email, "A valid email address is required.");
      return false;
    }
  }
  if (password.value.length < 10) {
    markInvalid(password, "Password must be at least 10 characters.");
    return false;
  }
  return true;
}

function collectLead(prefix) {
  return {
    name: $(`#${prefix}-name`).value.trim(),
    company: $(`#${prefix}-company`).value.trim(),
    email: $(`#${prefix}-email`).value.trim(),
    phone: $(`#${prefix}-phone`).value.trim(),
    source: $(`#${prefix}-source`).value.trim(),
    status: $(`#${prefix}-status`).value,
    priority: $(`#${prefix}-priority`).value,
    value: $(`#${prefix}-value`).value.trim(),
    next_followup: $(`#${prefix}-followup`).value,
    message: $(`#${prefix}-message`).value.trim(),
    notes: $(`#${prefix}-notes`).value.trim(),
  };
}

function validateLeadPayload(payload, prefix) {
  const fields = [
    $(`#${prefix}-name`),
    $(`#${prefix}-email`),
    $(`#${prefix}-value`),
    $(`#${prefix}-followup`),
  ];
  clearInvalid(fields);

  if (payload.name.length < 2) {
    markInvalid($(`#${prefix}-name`), "Contact name must be at least 2 characters.");
    return false;
  }
  if (payload.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.email)) {
    markInvalid($(`#${prefix}-email`), "Email address is invalid.");
    return false;
  }
  if (payload.value && Number.isNaN(Number(payload.value))) {
    markInvalid($(`#${prefix}-value`), "Deal value must be numeric.");
    return false;
  }
  return true;
}

function setAuthMode(mode) {
  state.authMode = mode;
  $("#register-email-group").classList.toggle("hidden", mode !== "register");
  $("#auth-title").textContent = mode === "register" ? "Create your workspace" : "Welcome back";
  $("#auth-copy").textContent = mode === "register"
    ? "Start with a secure CRM foundation built for outreach, partnerships, and inbound leads."
    : "Sign in to manage leads, reminders, and future AI workflows.";
  $("#auth-submit").textContent = mode === "register" ? "Create account" : "Sign in";
  $("#auth-toggle-text").textContent = mode === "register" ? "Already have an account?" : "Need an account?";
  $("#auth-toggle-btn").textContent = mode === "register" ? "Sign in" : "Create one";
  $("#auth-email").value = "";
}

function showAuthView() {
  $("#auth-view").classList.remove("hidden");
  $("#app-view").classList.add("hidden");
  $("#user-pill").classList.add("hidden");
  $("#logout-btn").classList.add("hidden");
}

function showAppView() {
  $("#auth-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  $("#user-pill").classList.remove("hidden");
  $("#logout-btn").classList.remove("hidden");
}

function resetLeadForm() {
  $("#lead-form").reset();
}

function renderHero() {
  const hours = new Date().getHours();
  const greeting = hours < 12 ? "Good morning" : hours < 18 ? "Good afternoon" : "Good evening";
  const username = state.user?.username || "there";
  $("#hero-title").textContent = `${greeting}, ${username}`;
  $("#hero-subtitle").textContent = "Monitor the pipeline, ship follow-ups, and prepare for AI automation.";
}

function renderUser() {
  const username = state.user?.username || "guest";
  $("#user-label").textContent = username;
  $("#user-initial").textContent = username.charAt(0).toUpperCase();
}

function renderStats() {
  const stats = state.stats || {};
  $("#s-total").textContent = String(stats.total || 0);
  $("#s-week").textContent = `${stats.added_this_week || 0} added this week`;
  $("#s-new").textContent = String(stats.new_count || 0);
  $("#s-qualified").textContent = String(stats.qualified || 0);
  $("#s-pipeline").textContent = currency(stats.pipeline_total || 0);
  $("#s-won").textContent = currency(stats.pipeline_won || 0);
  $("#s-overdue").textContent = String(stats.overdue_followups || 0);
  $("#s-won-rate").textContent = `${stats.won_rate || 0}%`;
}

function renderReminders() {
  const stale = state.reminders.stale || [];
  const overdue = state.reminders.overdue || [];
  const all = [...overdue.map((item) => ({ ...item, kind: "Overdue follow-up" })), ...stale.map((item) => ({ ...item, kind: "Stale new lead" }))];
  const strip = $("#reminder-strip");
  const empty = $("#reminder-empty");
  const list = $("#reminder-items");
  list.replaceChildren();

  if (!all.length) {
    strip.classList.add("hidden");
    empty.classList.remove("hidden");
    return;
  }

  all.forEach((item) => {
    const li = createNode("li");
    const strong = createNode("strong", "", item.name);
    li.append(strong, ` — ${item.kind}`);
    if (item.next_followup) {
      li.append(` (${fullDate(item.next_followup)})`);
    }
    list.appendChild(li);
  });

  empty.classList.add("hidden");
  strip.classList.remove("hidden");
}

function filteredLeads() {
  const filter = $("#filter-status").value;
  const sort = $("#filter-sort").value;
  let leads = [...state.leads];
  if (filter !== "All") {
    leads = leads.filter((lead) => lead.status === filter);
  }
  leads.sort((a, b) => {
    if (sort === "oldest") {
      return new Date(a.created_at) - new Date(b.created_at);
    }
    if (sort === "value") {
      return Number(b.value || 0) - Number(a.value || 0);
    }
    return new Date(b.created_at) - new Date(a.created_at);
  });
  return leads;
}

function statusClass(status) {
  return status.toLowerCase();
}

function buildBadge(status) {
  return createNode("span", `badge ${statusClass(status)}`, status.replace("-", " "));
}

function leadActionButton(label, tone, action, leadId) {
  const button = createNode("button", `btn ${tone} btn-sm`, label);
  button.type = "button";
  button.dataset.action = action;
  button.dataset.leadId = String(leadId);
  return button;
}

function renderList() {
  const container = $("#list-view");
  container.replaceChildren();
  const leads = filteredLeads();

  if (!leads.length) {
    const empty = createNode("div", "panel empty-state");
    empty.append(createNode("span", "empty-icon", "◌"), createNode("p", "", "No leads match this view yet."));
    container.appendChild(empty);
    return;
  }

  leads.forEach((lead) => {
    const card = createNode("article", "lead-card");
    const main = createNode("div", "lead-card-main");
    const top = createNode("div", "lead-card-top");
    const identity = createNode("div");
    identity.append(createNode("div", "lead-name", lead.name));
    if (lead.company) identity.append(createNode("div", "lead-company", lead.company));
    top.appendChild(identity);
    if (lead.value) top.appendChild(createNode("div", "lead-value", currency(lead.value)));
    main.appendChild(top);

    const meta = createNode("div", "lead-meta");
    const priority = createNode("span", `priority-dot priority-${lead.priority}`);
    meta.appendChild(priority);
    meta.appendChild(buildBadge(lead.status));
    if (lead.source) meta.appendChild(createNode("span", "source-tag", lead.source));
    if (lead.ai_score !== null && lead.ai_score !== undefined) meta.appendChild(createNode("span", "ai-tag", `AI ${lead.ai_score}`));
    if (lead.ai_category) meta.appendChild(createNode("span", "ai-tag", lead.ai_category));
    main.appendChild(meta);

    if (lead.message) main.appendChild(createNode("div", "lead-message", lead.message));
    if (lead.notes) main.appendChild(createNode("div", "lead-notes", `Notes: ${lead.notes}`));
    if (lead.ai_summary) main.appendChild(createNode("div", "lead-ai", lead.ai_summary));

    const footer = createNode("div", "lead-footer");
    if (lead.email) footer.appendChild(createNode("span", "source-tag", lead.email));
    if (lead.phone) footer.appendChild(createNode("span", "source-tag", lead.phone));
    if (lead.next_followup) footer.appendChild(createNode("span", "source-tag", `Follow-up ${fullDate(lead.next_followup)}`));
    footer.appendChild(createNode("span", "lead-date", `Created ${shortDate(lead.created_at)}`));
    main.appendChild(footer);

    const actions = createNode("div", "lead-actions");
    actions.appendChild(leadActionButton("Edit", "btn-ghost", "edit", lead.id));
    actions.appendChild(leadActionButton("Delete", "btn-danger", "delete", lead.id));
    actions.appendChild(leadActionButton("Score", "btn-ai", "score", lead.id));
    actions.appendChild(leadActionButton("Follow-up", "btn-ai", "followup", lead.id));
    actions.appendChild(leadActionButton("Summarize", "btn-ai", "summarize", lead.id));

    card.append(main, actions);
    container.appendChild(card);
  });
}

function renderBoard() {
  const grouped = Object.fromEntries(STATUSES.map((status) => [status, []]));
  state.leads.forEach((lead) => {
    if (grouped[lead.status]) grouped[lead.status].push(lead);
  });

  STATUSES.forEach((status) => {
    const lane = document.getElementById(`lane-${status}`);
    const count = document.getElementById(`count-${status}`);
    lane.replaceChildren();
    const leads = grouped[status];
    count.textContent = String(leads.length);

    if (!leads.length) {
      lane.appendChild(createNode("div", "empty-state empty-tight", "Drop leads here"));
      return;
    }

    leads.forEach((lead) => {
      const card = createNode("article", "board-card");
      card.draggable = true;
      card.dataset.leadId = String(lead.id);
      card.addEventListener("dragstart", () => {
        state.draggedLeadId = lead.id;
        card.classList.add("dragging");
      });
      card.addEventListener("dragend", () => {
        state.draggedLeadId = null;
        card.classList.remove("dragging");
      });

      card.appendChild(createNode("div", "board-card-name", lead.name));
      if (lead.company) card.appendChild(createNode("div", "board-card-meta", lead.company));
      card.appendChild(createNode("div", "board-card-meta", lead.source || "Manual"));
      if (lead.value) card.appendChild(createNode("div", "board-card-value", currency(lead.value)));
      lane.appendChild(card);
    });
  });
}

function renderEverything() {
  renderHero();
  renderUser();
  renderStats();
  renderReminders();
  renderList();
  renderBoard();
}

async function loadDashboard() {
  const [leadsRes, statsRes, remindersRes] = await Promise.all([
    apiFetch("/leads/"),
    apiFetch("/leads/stats"),
    apiFetch("/leads/reminders"),
  ]);

  if (!leadsRes.success && leadsRes.statusCode === 401) {
    state.user = null;
    showAuthView();
    return;
  }

  state.leads = leadsRes.leads || [];
  state.stats = statsRes.stats || {};
  state.reminders = remindersRes.success ? remindersRes : { stale: [], overdue: [] };
  renderEverything();
}

async function refreshSession() {
  const response = await apiFetch("/auth/me", { method: "GET" });
  if (!response.success) {
    state.user = null;
    showAuthView();
    return;
  }
  state.user = response.user;
  showAppView();
  await loadDashboard();
}

async function submitAuth() {
  if (!validateAuthForm()) return;
  const endpoint = state.authMode === "register" ? "/auth/register" : "/auth/login";
  const payload = {
    username: $("#auth-username").value.trim(),
    email: $("#auth-email").value.trim(),
    password: $("#auth-password").value,
  };
  const response = await apiFetch(endpoint, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!response.success) {
    showToast(response.error || "Authentication failed.", "error");
    return;
  }
  showToast(response.message || `${state.authMode === "register" ? "Account created" : "Signed in"} successfully.`, "success");
  $("#auth-form").reset();
  state.user = response.user || { username: response.username, email: response.email || "" };
  showAppView();
  await refreshSession();
}

async function submitLead() {
  const payload = collectLead("f");
  if (!validateLeadPayload(payload, "f")) return;
  const response = await apiFetch("/leads/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!response.success) {
    showToast(response.error || "Could not create lead.", "error");
    return;
  }
  showToast(response.message || "Lead added.", "success");
  resetLeadForm();
  await loadDashboard();
}

function openModal(lead) {
  $("#e-id").value = String(lead.id);
  $("#e-name").value = lead.name || "";
  $("#e-company").value = lead.company || "";
  $("#e-email").value = lead.email || "";
  $("#e-phone").value = lead.phone || "";
  $("#e-source").value = lead.source || "";
  $("#e-status").value = lead.status || "New";
  $("#e-priority").value = lead.priority || "medium";
  $("#e-value").value = lead.value || "";
  $("#e-followup").value = lead.next_followup || "";
  $("#e-message").value = lead.message || "";
  $("#e-notes").value = lead.notes || "";
  $("#edit-modal").classList.remove("hidden");
}

function closeModal() {
  $("#edit-modal").classList.add("hidden");
  $("#edit-form").reset();
}

async function saveEdit() {
  const payload = collectLead("e");
  const leadId = $("#e-id").value;
  if (!validateLeadPayload(payload, "e")) return;
  const response = await apiFetch(`/leads/${leadId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  if (!response.success) {
    showToast(response.error || "Could not update lead.", "error");
    return;
  }
  closeModal();
  showToast(response.message || "Lead updated.", "success");
  await loadDashboard();
}

async function deleteLead(leadId) {
  if (!window.confirm("Delete this lead?")) return;
  const response = await apiFetch(`/leads/${leadId}`, { method: "DELETE" });
  if (!response.success) {
    showToast(response.error || "Could not delete lead.", "error");
    return;
  }
  showToast(response.message || "Lead deleted.", "success");
  await loadDashboard();
}

async function runAiAction(action, leadId) {
  const response = await apiFetch(`/ai/leads/${leadId}/${action}`, { method: "POST" });
  if (!response.success) {
    showToast(response.error || "AI action failed.", "error");
    return;
  }
  if (response.followup_text) showToast("Follow-up draft generated.", "success");
  else if (response.summary) showToast("Summary generated.", "success");
  else if (response.score !== undefined) showToast("Lead scored.", "success");
  else showToast(response.message || "AI action complete.", "info");
  await loadDashboard();
}

async function patchStatus(leadId, status) {
  const response = await apiFetch(`/leads/${leadId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (!response.success) {
    showToast(response.error || "Could not update status.", "error");
    return;
  }
  showToast(response.message || "Status updated.", "success");
  await loadDashboard();
}

async function signOut() {
  const response = await apiFetch("/auth/logout", { method: "POST" });
  if (!response.success) {
    showToast(response.error || "Could not sign out.", "error");
    return;
  }
  state.user = null;
  showToast("Signed out.", "info");
  showAuthView();
}

function switchView(view) {
  state.view = view;
  $("#pill-list").classList.toggle("active", view === "list");
  $("#pill-board").classList.toggle("active", view === "board");
  $("#list-view").classList.toggle("hidden", view !== "list");
  $("#board-view").classList.toggle("hidden", view !== "board");
}

function attachBoardDnD() {
  document.querySelectorAll(".board-col").forEach((column) => {
    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      column.classList.add("drag-over");
    });
    column.addEventListener("dragleave", () => column.classList.remove("drag-over"));
    column.addEventListener("drop", async (event) => {
      event.preventDefault();
      column.classList.remove("drag-over");
      if (!state.draggedLeadId) return;
      const status = column.dataset.status;
      await patchStatus(state.draggedLeadId, status);
    });
  });
}

function attachEvents() {
  $("#auth-toggle-btn").addEventListener("click", () => setAuthMode(state.authMode === "login" ? "register" : "login"));
  $("#auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAuth();
  });
  $("#lead-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitLead();
  });
  $("#lead-reset").addEventListener("click", resetLeadForm);
  $("#logout-btn").addEventListener("click", signOut);
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal-cancel").addEventListener("click", closeModal);
  $("#edit-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveEdit();
  });
  $("#filter-status").addEventListener("change", renderList);
  $("#filter-sort").addEventListener("change", renderList);
  $("#pill-list").addEventListener("click", () => switchView("list"));
  $("#pill-board").addEventListener("click", () => switchView("board"));

  $("#list-view").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const leadId = Number(button.dataset.leadId);
    const action = button.dataset.action;
    const lead = state.leads.find((item) => item.id === leadId);
    if (!lead) return;

    if (action === "edit") openModal(lead);
    if (action === "delete") await deleteLead(leadId);
    if (action === "score") await runAiAction("score", leadId);
    if (action === "followup") await runAiAction("followup", leadId);
    if (action === "summarize") await runAiAction("summarize", leadId);
  });

  $("#edit-modal").addEventListener("click", (event) => {
    if (event.target === $("#edit-modal")) closeModal();
  });

  attachBoardDnD();
}

document.addEventListener("DOMContentLoaded", async () => {
  attachEvents();
  setAuthMode("login");
  switchView("list");
  await refreshSession();
});