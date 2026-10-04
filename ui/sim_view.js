// Observation lineage: kinoko34077/2bit-cell-automaton @
// e9e9a6895f70d9153676abf3656e3805588d60da
//
// The authoritative simulation clock is external to this view. The server owns
// the Phase 5 optimizer; these timers only poll and render state.

import { DETAIL_MODES, detailColor, overviewColor } from "./view_model.mjs";

const canvas = document.getElementById("universe");
const ctx = canvas.getContext("2d");
const overview = document.getElementById("overview");
const status = document.getElementById("status");
const mode = document.getElementById("mode");
const modeLock = document.getElementById("mode-lock");
const historyLength = document.getElementById("history-length");
const metadata = document.getElementById("optimizer-meta");
const pendingLabel = document.getElementById("pending-parameters");
const collisionDamage = document.getElementById("collision-damage");
const noiseAttempts = document.getElementById("noise-attempts");
const resetParameterForm = document.getElementById("reset-parameters");
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
    tile.setAttribute(
      "aria-label",
      `Universe ${summary.index}, ${summary.category}, seed ${summary.seed}, ${summary.active_cells || 0} active cells`,
    );
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
    label.textContent = `${summary.index} · ${summary.active_cells || 0} · e${summary.evidence_group_size ?? 0}`;
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

function updateLabels() {
  const selected = currentState?.selected || {};
  const target = currentState?.observation_target === "clone" ? " (clone)" : "";
  document.getElementById("selected-label").textContent =
    `Universe ${currentState?.selected_index ?? 0} · ${selected.category ?? "unknown"} · seed ${selected.seed ?? "?"}${target}`;
}

function updateMetadata() {
  const selected = currentState?.selected || {};
  const fitness = selected.fitness || {};
  const growth = (selected.growth_windows || []).map((value) => Number(value).toString(16).padStart(2, "0")).join(" ");
  const event = selected.last_event ? JSON.stringify(selected.last_event) : "none";
  metadata.textContent = [
    `Authority: ${currentState?.authority ?? "unknown"}`,
    `Search iteration: ${currentState?.optimizer_generation ?? 0} (${currentState?.running ? "running" : "paused"})`,
    `Selected physical generation: ${selected.generation ?? 0}`,
    `Category / seed: ${selected.category ?? "?"} / ${selected.seed ?? "?"}`,
    `Genome: ${JSON.stringify(selected.genome || {})}`,
    `Evidence: ${selected.evidence_group_size ?? 0} slots; mature=${Boolean(selected.evidence_mature)}`,
    `Lineage: parentGenome=${selected.parent_genome_key ?? "none"}; parentSlot=${selected.parent_index ?? "none"}; mutation=${selected.last_mutation_field ?? "none"}; allocation=${selected.allocation_reason ?? "?"}`,
    `Fitness: success=${fitness.success ?? 0}, wrong=${fitness.wrong_outputs ?? 0}, timeout=${fitness.timeouts ?? 0}, latency=${fitness.response_latency ?? 0}, activity=${fitness.activity_cost ?? 0}`,
    `Growth windows: ${growth || "none"}`,
    `Last replacement event: ${event}`,
    `Activity rendering: ${currentState?.activity_semantics ?? "unknown"}`,
  ].join("\n");
}

function updateResetControls() {
  const pending = currentState?.pending_reset_parameters || {};
  const config = currentState?.reset_config || {};
  const editingResetParameters = resetParameterForm?.contains(document.activeElement);
  if (!editingResetParameters) {
    collisionDamage.value = pending.collision_damage ?? config.collision_damage ?? 0;
    noiseAttempts.value = pending.noise_attempts ?? config.noise_attempts ?? 0;
  }
  const keys = Object.keys(pending);
  pendingLabel.textContent = keys.length ? `Pending Reset: ${keys.join(", ")}` : "No pending Reset edits.";
  historyLength.value = String(currentState?.history_length ?? 512);
}

function updateStatus(prefix = "") {
  const selectedGeneration = currentState?.selected?.generation ?? 0;
  const error = currentState?.last_error ? ` Error: ${currentState.last_error}` : "";
  status.textContent =
    `${prefix}Search ${currentState?.optimizer_generation ?? 0}; selected physical ${selectedGeneration}; ${currentState?.running ? "running" : "paused"}.${error}`;
}

function renderState({ updateOverview = true, updateDetail = true, prefix = "" } = {}) {
  if (updateOverview) renderOverview(currentState?.summaries || []);
  if (updateDetail) renderDetail(currentState?.selected, mode.value);
  updateLabels();
  updateMetadata();
  updateResetControls();
  updateStatus(prefix);
}

export async function refreshState({ updateOverview = true, updateDetail = true } = {}) {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`state request failed: ${response.status}`);
  currentState = await response.json();
  window.universeGenomeState = currentState;
  renderState({ updateOverview, updateDetail });
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
  option.textContent = value === "activity" ? "activity (visual proxy)" : value;
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
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.error || `control request failed: ${response.status}`);
  }
  currentState = await response.json();
  window.universeGenomeState = currentState;
  renderState({ prefix: `Action ${action}; ` });
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
