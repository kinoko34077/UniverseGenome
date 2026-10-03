// Observation lineage: kinoko34077/2bit-cell-automaton @
// e9e9a6895f70d9153676abf3656e3805588d60da
//
// Phase 0 intentionally reuses only the grid/inspection concept. Old physics
// and render-driven simulation timing are not reused.
// The authoritative simulation clock is external to this view.

const canvas = document.getElementById("universe");
const ctx = canvas.getContext("2d");

export function renderScaffold() {
  const size = 32;
  const cell = canvas.width / size;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#d0d0d0";
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

renderScaffold();
