import { expect, startBackend, test } from "./backend";

test("связывает создание типа, запись гостя и повестку владельца", async ({ page }) => {
  await startBackend();
  await page.goto("/event-types");

  const types = page.getByRole("list", { name: "Доступные типы событий" }).getByRole("listitem");
  await expect(types).toHaveCount(3);
  await expect(types.nth(0)).toContainText("Знакомство");
  await expect(types.nth(1)).toContainText("Консультация");
  await expect(types.nth(2)).toContainText("Глубокий разбор");

  await page.getByRole("link", { name: "Создать тип события", exact: true }).click();
  await page.getByLabel("Название").fill("Стратегическая сессия");
  await page.getByLabel("Описание").fill("Согласуем цели и план работы");
  await page.getByLabel("Длительность").selectOption("120");
  await page.getByRole("button", { name: "Создать тип события", exact: true }).click();
  await expect(types).toHaveCount(4);
  await expect(types.nth(3)).toContainText("Стратегическая сессия");

  await page.goto("/book");
  await page.getByRole("button", { name: "Стратегическая сессия · 120 минут" }).click();
  const intervals = page.getByRole("list", { name: "Интервалы" }).getByRole("button");
  await expect(intervals).toHaveCount(15);
  await intervals.first().click();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await page.getByLabel("Имя").fill("Иван Петров");
  await page.getByLabel("Email").fill("ivan@example.com");
  await page.getByRole("button", { name: "Подтвердить запись" }).click();
  await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();

  await page.getByRole("button", { name: "Забронировать ещё" }).click();
  await page.getByRole("button", { name: "Стратегическая сессия · 120 минут" }).click();
  const bookedInterval = page.getByRole("list", { name: "Интервалы" }).getByRole("button").first();
  await expect(bookedInterval).toBeDisabled();
  await expect(bookedInterval).toContainText("Занято");

  await page.goto("/events");
  const booking = page.getByRole("article").filter({ hasText: "Стратегическая сессия" });
  await expect(booking).toHaveCount(1);
  await expect(booking).toContainText("Иван Петров");
  await expect(booking).toContainText("ivan@example.com");
  await expect(booking).toContainText("120 минут");
});
