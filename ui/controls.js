// Controls submit bounded requests to the runtime; they never advance the
// authoritative simulation clock from a render callback.

const status = document.getElementById("status");
const snapshotFile = document.getElementById("snapshot-file");

async function send(action, payload = {}) {
  try {
    return await window.universeGenomeControl(action, payload);
  } catch (error) {
    status.textContent = `Action ${action} failed: ${error.message}`;
    return null;
  }
}

for (const node of document.querySelectorAll("button[data-action]")) {
  node.addEventListener("click", async () => {
    const action = node.dataset.action;
    if (action === "load") {
      snapshotFile.click();
      return;
    }
    if (action === "select") {
      await send("select", { index: window.universeGenomeState?.selected_index || 0 });
      return;
    }
    const result = await send(action);
    if (action === "save" && result?.snapshot) {
      const blob = new Blob([JSON.stringify(result.snapshot, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "universegenome-population.json";
      link.click();
      URL.revokeObjectURL(link.href);
    }
  });
}

document.querySelector("select[data-action=rewind]").addEventListener("change", (event) => {
  send("rewind", { generations: Number(event.target.value) });
});

snapshotFile.addEventListener("change", async () => {
  const file = snapshotFile.files?.[0];
  if (!file) return;
  try {
    await send("load", { snapshot: JSON.parse(await file.text()) });
  } catch (error) {
    status.textContent = `Snapshot load failed: ${error.message}`;
  } finally {
    snapshotFile.value = "";
  }
});
