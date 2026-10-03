// Controls emit requests; they never advance the authoritative simulation clock.

const status = document.getElementById("status");
const actions = {
  run: "run",
  pause: "pause",
  step: "step",
  reset: "reset",
  select: "select-universe",
  clone: "clone-for-observation",
  rewind: "rewind",
  save: "save-snapshot",
  load: "load-snapshot",
};

for (const [selector, action] of Object.entries(actions)) {
  const nodes = document.querySelectorAll(`[data-action="${selector}"]`);
  for (const node of nodes) {
    node.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("universegenome-control", { detail: { action } }));
      status.textContent = `Requested ${action}; the external core clock remains authoritative.`;
    });
  }
}
