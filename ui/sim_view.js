// Observation lineage: kinoko34077/2bit-cell-automaton @
// e9e9a6895f70d9153676abf3656e3805588d60da
//
// Phase 3 reuses only grid/inspection concepts. The runtime API owns the
// authoritative simulation clock is external to this view; this module only
// polls and renders state.

const canvas = document.getElementById("universe");
const ctx = canvas.getContext("2d");
const overview = document.getElementById("overview");
const status = document.getElementById("status");
const mode = document.getElementById("mode");
let currentState = null;

function token(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function renderOverview(summaries = []) {
  overview.replaceChildren();
  for (const summary of summaries) {
    const tile = document.createElement("button");
    tile.className = "thumbnail";
    tile.dataset.category = summary.category;
    tile.dataset.index = String(summary.index);
    tile.textContent = `${summary.index}\n${summary.active_cells || 0}`;
    tile.setAttribute("aria-label", `Universe ${summary.index}, ${summary.active_cells || 0} active cells`);
    tile.addEventListener("click", () => window.universeGenomeControl("select", { index: summary.index }));
    overview.append(tile);
  }
}

export function renderDetail(detail = { cells: [] }, selectedMode = "HP") {
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
    const intensity = selectedMode === "bond/contact" ? item.bond : selectedMode === "hierarchy" ? item.structure : item.hp;
    ctx.fillStyle = intensity > 170 ? token("--cell-high", "#60a5fa") : intensity > 60 ? token("--cell-mid", "#34d399") : token("--cell-low", "#f87171");
    ctx.fillRect(item.x * cell, item.y * cell, cell, cell);
  }
}

export async function refreshState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`state request failed: ${response.status}`);
  currentState = await response.json();
  window.universeGenomeState = currentState;
  renderOverview(currentState.summaries);
  document.getElementById("selected-label").textContent = `Universe ${currentState.selected_index}`;
  renderDetail(currentState.selected, mode.value);
  status.textContent = `Generation ${currentState.generation}; ${currentState.running ? "running" : "paused"}.`;
  return currentState;
}

mode.addEventListener("change", () => renderDetail(currentState?.selected, mode.value));
window.universeGenomeRefresh = refreshState;
window.universeGenomeControl = async (action, payload = {}) => {
  const response = await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...payload }),
  });
  if (!response.ok) throw new Error(`control request failed: ${response.status}`);
  const state = await response.json();
  currentState = state;
  window.universeGenomeState = state;
  renderOverview(state.summaries || []);
  renderDetail(state.selected, mode.value);
  document.getElementById("selected-label").textContent = `Universe ${state.selected_index}`;
  status.textContent = `Action ${action}; generation ${state.generation}.`;
  return state;
};

refreshState().catch((error) => {
  status.textContent = `Runtime unavailable: ${error.message}`;
});
window.setInterval(() => refreshState().catch((error) => {
  status.textContent = `Runtime unavailable: ${error.message}`;
}), 500);
