// Observation lineage: kinoko34077/2bit-cell-automaton @
// e9e9a6895f70d9153676abf3656e3805588d60da
//
// Phase 3 reuses only grid/inspection concepts. The runtime API owns the
// authoritative simulation clock is external to this view; this module only
// polls and renders state.

import { DETAIL_MODES, detailColor, overviewColor } from "./view_model.mjs";

const canvas = document.getElementById("universe");
const ctx = canvas.getContext("2d");
const overview = document.getElementById("overview");
const status = document.getElementById("status");
const mode = document.getElementById("mode");
const modeLock = document.getElementById("mode-lock");
const rewind = document.querySelector("select[data-action=rewind]");
let currentState = null;
let detailFrame = 0;

function token(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function renderOverview(summaries = []) {
  overview.replaceChildren();
  for (const summary of summaries) {
    const tile = document.createElement("button");
    tile.className = "thumbnail";
    tile.dataset.category = summary.category;
    tile.dataset.index = String(summary.index);
    tile.setAttribute("aria-label", `Universe ${summary.index}, ${summary.active_cells || 0} active cells`);
    const map = document.createElement("canvas");
    map.width = 8;
    map.height = 8;
    map.setAttribute("aria-hidden", "true");
    const mapContext = map.getContext("2d");
    for (let index = 0; index < 64; index += 1) {
      mapContext.fillStyle = overviewColor(summary.overview?.[index]);
      mapContext.fillRect(index % 8, Math.floor(index / 8), 1, 1);
    }
    const label = document.createElement("span");
    label.textContent = `${summary.index} · ${summary.active_cells || 0}`;
    tile.append(map, label);
    tile.addEventListener("click", () => window.universeGenomeControl("select", { index: summary.index }));
    overview.append(tile);
  }
}

function renderDetail(detail = { cells: [] }, selectedMode = "HP") {
  const size = 32;
  const cell = canvas.width / size;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = token("--grid", "#374151");
  ctx.lineWidth = 1;
  for (let i = 0; i <= size; i += 1) {
    const p = i * cell;
    ctx.beginPath();
    ctx.moveTo(p, 0);
    ctx.lineTo(p, canvas.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, p);
    ctx.lineTo(canvas.width, p);
    ctx.stroke();
  }
  for (const item of detail.cells || []) {
    ctx.fillStyle = detailColor(item, selectedMode);
    ctx.fillRect(item.x * cell, item.y * cell, cell, cell);
  }
}

function updateRewindOptions(historyLength) {
  for (const option of rewind.options) {
    option.disabled = Number(option.value) > Number(historyLength || 0);
  }
}

function updateLabels() {
  const target = currentState?.observation_target === "clone" ? " (clone)" : "";
  document.getElementById("selected-label").textContent = `Universe ${currentState?.selected_index ?? 0}${target}`;
}

export async function refreshState({ updateOverview = true, updateDetail = true } = {}) {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`state request failed: ${response.status}`);
  currentState = await response.json();
  window.universeGenomeState = currentState;
  if (updateOverview) renderOverview(currentState.summaries);
  if (updateDetail) renderDetail(currentState.selected, mode.value);
  updateLabels();
  updateRewindOptions(currentState.history_length);
  status.textContent = `Generation ${currentState.generation}; ${currentState.running ? "running" : "paused"}.`;
  return currentState;
}

function advanceAutomaticMode() {
  if (modeLock.checked || detailFrame % 4 !== 0) return;
  const alternating = ["HP", "hierarchy"];
  const index = alternating.indexOf(mode.value);
  mode.value = index < 0 ? "HP" : alternating[(index + 1) % alternating.length];
}

mode.replaceChildren(...DETAIL_MODES.map((value) => {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = value;
  return option;
}));
mode.addEventListener("change", () => renderDetail(currentState?.selected, mode.value));
window.universeGenomeRefresh = refreshState;
window.universeGenomeControl = async (action, payload = {}) => {
  const response = await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...payload }),
  });
  if (!response.ok) throw new Error(`control request failed: ${response.status}`);
  currentState = await response.json();
  window.universeGenomeState = currentState;
  renderOverview(currentState.summaries || []);
  renderDetail(currentState.selected, mode.value);
  updateLabels();
  updateRewindOptions(currentState.history_length);
  status.textContent = `Action ${action}; generation ${currentState.generation}.`;
  return currentState;
};

refreshState().catch((error) => {
  status.textContent = `Runtime unavailable: ${error.message}`;
});
window.setInterval(() => refreshState({ updateOverview: true, updateDetail: false }).catch((error) => {
  status.textContent = `Runtime unavailable: ${error.message}`;
}), 500);
window.setInterval(() => {
  detailFrame += 1;
  advanceAutomaticMode();
  refreshState({ updateOverview: false, updateDetail: true }).catch((error) => {
    status.textContent = `Runtime unavailable: ${error.message}`;
  });
}, 125);
