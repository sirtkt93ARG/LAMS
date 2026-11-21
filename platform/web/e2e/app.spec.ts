import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function login(page: Page, role: "student" | "teacher" | "admin" | "network") {
  await page.goto("/");
  await page.getByLabel("Usuario").fill(`browser-${role}`);
  await page.getByRole("textbox", { name: "Escuela" }).fill("escuela-browser");
  await page.getByRole("combobox", { name: "Rol", exact: true }).selectOption(role);
  await page.getByRole("button", { name: "Entrar como usuario de prueba" }).click();
}

async function expectNoA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
    .analyze();
  const violations = results.violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    targets: v.nodes.map((n) => n.target),
  }));
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
}

test("login page is keyboard navigable and has no automated accessibility violations", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Saltar al contenido" })).toBeFocused();
  await expectNoA11yViolations(page);
});

test("student can start a practice and submit an answer", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await login(page, "student");
  await expect(page).toHaveURL(/\/practice$/);
  await expect(page.getByRole("heading", { name: "Práctica de matemática" })).toBeVisible();
  await page.getByRole("button", { name: "Empezar práctica de 24 preguntas" }).click();

  const radios = page.locator(".choices input[type=\"radio\"]");
  if (await radios.count()) {
    await radios.first().check();
  } else {
    await page.locator('input[name="response"]').fill("1");
  }
  await page.getByRole("button", { name: "Responder" }).click();
  await expect(page.getByRole("heading", { name: /Respuesta correcta|Esta vez no fue correcta/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Siguiente pregunta|Ver mi resultado/ })).toBeVisible();
  expect(pageErrors).toEqual([]);
  await expectNoA11yViolations(page);
});

test("teacher dashboard renders its data and accessibility controls", async ({ page }) => {
  await login(page, "teacher");
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByRole("heading", { name: "Panel docente" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Niveles" })).toBeVisible();
  await expect(page.getByText("Accesibilidad")).toBeVisible();
  await expectNoA11yViolations(page);
});

test("only content administrators can open global item curation", async ({ page }) => {
  await login(page, "teacher");
  await page.goto("/review");
  await expect(page).toHaveURL(/\/teacher$/);
  await login(page, "admin");
  await expect(page.getByRole("link", { name: "Curaduría" })).toBeVisible();
  await page.getByRole("link", { name: "Curaduría" }).click();
  await expect(page.getByRole("heading", { name: "Revisión de plantillas de ejercicios" })).toBeVisible();
  await expectNoA11yViolations(page);
});

test("network role can open the aggregated dashboard", async ({ page }) => {
  await login(page, "network");
  await expect(page).toHaveURL(/\/network$/);
  await expect(page.getByRole("heading", { name: "Resumen de la red de escuelas" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Invitar una escuela" })).toBeVisible();
  await expectNoA11yViolations(page);
});
