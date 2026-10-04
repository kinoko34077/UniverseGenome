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
  await expect(page.locator("#overview .thumbnail").nth(0)).toContainText(/e\d+/);

  await page.getByRole("button", { name: "Run Search" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(true);
  await page.getByRole("button", { name: "Pause Search" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(false);
});
