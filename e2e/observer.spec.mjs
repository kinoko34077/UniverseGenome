import { test, expect } from "@playwright/test";

test("observer renders the authoritative Phase 5 optimizer and real replacement", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/UniverseGenome/);
  await expect(page.locator("#overview .thumbnail")).toHaveCount(128);
  await expect(page.locator("#selected-label")).toContainText("Universe 0");
  await expect(page.locator("#status")).toContainText("Search");

  const initial = await page.evaluate(() => window.universeGenomeState);
  expect(initial.authority).toBe("phase5_optimizer");
  expect(initial.slot_count).toBe(128);
  expect(initial.summaries[0].fitness).toBeTruthy();
  expect(initial.summaries[0].genome).toBeTruthy();

  await page.locator("#overview .thumbnail").nth(2).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.selected_index)).toBe(2);

  await page.getByRole("button", { name: "Clone for Observation" }).click();
  await expect(page.locator("#selected-label")).toContainText("(clone)");
  const authoritativeGeneration = await page.evaluate(
    () => window.universeGenomeState.summaries[2].generation,
  );
  const cloneGeneration = await page.evaluate(
    () => window.universeGenomeState.selected.generation,
  );
  await page.getByRole("button", { name: "1 Observation Step" }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.selected.generation),
  ).toBe(cloneGeneration + 1);
  expect(await page.evaluate(
    () => window.universeGenomeState.summaries[2].generation,
  )).toBe(authoritativeGeneration);

  const prepared = await page.evaluate(async () => {
    const saved = await window.universeGenomeControl("save");
    saved.snapshot.slots[0].absolute_failure = true;
    saved.snapshot.slots[0].absolute_failure_reason = "all_active_cells_gone";
    return window.universeGenomeControl("load", { snapshot: saved.snapshot });
  });
  expect(prepared.optimizer_generation).toBe(initial.optimizer_generation);

  await page.getByRole("button", { name: "1 Search Iteration" }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.optimizer_generation),
    { timeout: 30_000 },
  ).toBe(initial.optimizer_generation + 1);
  const replacement = await page.evaluate(
    () => window.universeGenomeState.last_search.replacements.find((item) => item.index === 0),
  );
  expect(replacement).toBeTruthy();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.summaries[0].parent_genome_key),
  ).not.toBeNull();
  await expect(page.locator("#optimizer-meta")).toContainText("parentGenome=");
  await expect(page.locator("#overview .thumbnail").nth(0)).toContainText(/e\d+/);

  await page.getByRole("button", { name: "Run Search" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(true);
  await page.getByRole("button", { name: "Pause Search" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(false);
});


test("observer clone rewind, optimizer snapshot load, modes, and reset edits remain bounded", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#overview .thumbnail")).toHaveCount(128);

  const mode = page.getByLabel("Mode", { exact: true });
  await mode.selectOption("latent bit 3");
  await expect(mode).toHaveValue("latent bit 3");
  await page.getByLabel("Lock mode").check();

  await page.getByRole("button", { name: "Clone for Observation" }).click();
  const authoritativeGeneration = await page.evaluate(
    () => window.universeGenomeState.summaries[0].generation,
  );
  const cloneGeneration = await page.evaluate(
    () => window.universeGenomeState.selected.generation,
  );
  await page.getByRole("button", { name: "1 Observation Step" }).click();
  await page.getByRole("button", { name: "1 Observation Step" }).click();
  await page.getByRole("button", { name: "Rewind Observation 1" }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.selected.generation),
  ).toBe(cloneGeneration + 1);
  expect(await page.evaluate(
    () => window.universeGenomeState.summaries[0].generation,
  )).toBe(authoritativeGeneration);

  const saved = await page.evaluate(() => window.universeGenomeControl("save"));
  await page.getByRole("button", { name: "1 Search Iteration" }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.optimizer_generation),
  ).toBe(saved.snapshot.generation + 1);
  await page.evaluate(
    (snapshot) => window.universeGenomeControl("load", { snapshot }),
    saved.snapshot,
  );
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.optimizer_generation),
  ).toBe(saved.snapshot.generation);

  await page.getByLabel("Collision damage").fill("16");
  await page.getByLabel("Noise attempts").fill("1");
  await page.getByRole("button", { name: "Apply on Reset" }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.pending_reset_parameters.collision_damage),
  ).toBe(16);
  expect(await page.evaluate(
    () => window.universeGenomeState.reset_config.collision_damage,
  )).not.toBe(16);

  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await expect.poll(
    () => page.evaluate(() => window.universeGenomeState.reset_config.collision_damage),
  ).toBe(16);
  expect(await page.evaluate(
    () => window.universeGenomeState.pending_reset_parameters,
  )).toEqual({});
});
