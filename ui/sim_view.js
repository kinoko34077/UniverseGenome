// Observation lineage: kinoko34077/2bit-cell-automaton @
// e9e9a6895f70d9153676abf3656e3805588d60da
//
// Phase 3 reuses only grid/inspection concepts. Old physics and render-driven
// simulation timing are not reused. The authoritative simulation clock is external to this view.

const canvas = document.getElementById("universe");
const ctx = canvas.getContext("2d");
const overview = document.getElementById("overview");
const status = document.getElementById("status");

export function renderOverview(summaries = []) {
  overview.replaceChildren();
  for (let index = 0; index < 128; index += 1) {
    const summary = summaries[index] || { category: "masked_copy", active_cells: 0 };
    const tile = document.createElement("button");
    tile.className = "thumbnail";
    tile.dataset.category = summary.category;
    tile.dataset.index = String(index);
    tile.textContent = `${index}\n${summary.active_cells || 0}`;
    tile.addEventListener("click", () => {
      document.getElementById("selected-label").textContent = `Universe ${index}`;
    });
    overview.append(tile);
  }
}

export function renderDetail() {
  const size = 32;
  const cell = canvas.width / size;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#374151";
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
}

renderOverview();
renderDetail();
status.textContent = "Core owns the authoritative Phase 3 clock; this UI observes and sends explicit controls.";
