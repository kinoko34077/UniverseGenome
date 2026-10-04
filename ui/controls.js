// Controls submit bounded requests to the runtime; browser rendering never
// advances authoritative search or physical time.

const status = document.getElementById("status");
const snapshotFile = document.getElementById("snapshot-file");
const historyLength = document.getElementById("history-length");
const parameterForm = document.getElementById("reset-parameters");

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
    if (action === "search_step") {
      await send("search_step", { iterations: 1 });
      return;
    }
    if (action === "step") {
      await send("step", { generations: 1 });
      return;
    }
    if (action === "rewind") {
      await send("rewind", { generations: 1 });
      return;
    }
    const result = await send(action);
    if (action === "save" && result?.snapshot) {
      const blob = new Blob([JSON.stringify(result.snapshot, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "universegenome-optimizer.json";
      link.click();
      URL.revokeObjectURL(link.href);
    }
  });
}

historyLength.addEventListener("change", (event) => {
  send("set_history_length", { history_length: Number(event.target.value) });
});

parameterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const collisionDamage = Number(document.getElementById("collision-damage").value);
  const noiseAttempts = Number(document.getElementById("noise-attempts").value);
  await send("set_parameters", {
    parameters: {
      collision_damage: collisionDamage,
      noise_attempts: noiseAttempts,
    },
  });
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
