import { test, expect } from "@playwright/test";

test("observer renders population and drives the server-owned runtime", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/UniverseGenome/);
  await expect(page.locator("#overview .thumbnail")).toHaveCount(128);
  await expect(page.locator("#selected-label")).toHaveText("Universe 0");
  await expect(page.locator("#status")).toContainText("Generation");

  const initialGeneration = await page.evaluate(() => window.universeGenomeState.generation);
  await page.getByRole("button", { name: "1 Step" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.generation)).toBe(initialGeneration + 1);

  await page.locator("#overview .thumbnail").nth(2).click();
  await expect(page.locator("#selected-label")).toHaveText("Universe 2");
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.selected_index)).toBe(2);

  await page.getByRole("button", { name: "Clone for Observation" }).click();
  await expect(page.locator("#selected-label")).toHaveText("Universe 2 (clone)");
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.observation_target)).toBe("clone");

  const mode = page.getByLabel("Mode", { exact: true });
  await mode.selectOption("activity");
  await expect(mode).toHaveValue("activity");

  await page.getByRole("button", { name: "Run" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(true);
  await page.getByRole("button", { name: "Pause" }).click();
  await expect.poll(() => page.evaluate(() => window.universeGenomeState.running)).toBe(false);
});
