import { expect, test } from "@playwright/test";

test("public login page renders without loading protected data", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
  await expect(page.locator("body")).toContainText(/登录|Login/i);
});

test("protected route redirects unauthenticated users", async ({ page }) => {
  await page.goto("/teacher/courseware-agent");
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
});
