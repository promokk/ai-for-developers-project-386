import { expect, startBackend, test } from "./backend";

test("связывает создание типа, запись гостя и повестку владельца", async ({ page }) => {
  test.setTimeout(60_000);
  if (!process.env.CALENDAR_BASE_URL) {
    await startBackend();
  }
  const runId = crypto.randomUUID();
  const eventTypeName = `Стратегическая сессия ${runId.slice(0, 8)}`;
  const guestName = `Иван Петров ${runId.slice(0, 8)}`;
  const guestEmail = `ivan-${runId}@example.com`;
  await page.goto("/event-types");

  const types = page.getByRole("list", { name: "Доступные типы событий" }).getByRole("listitem");
  if (!process.env.CALENDAR_BASE_URL) {
    await expect(types).toHaveCount(3);
    await expect(types.nth(0)).toContainText("Знакомство");
    await expect(types.nth(1)).toContainText("Консультация");
    await expect(types.nth(2)).toContainText("Глубокий разбор");
  } else {
    await expect(types).not.toHaveCount(0);
  }
  await page.getByRole("link", { name: "Создать тип события", exact: true }).click();
  await page.getByLabel("Название").fill(eventTypeName);
  await page.getByLabel("Описание").fill("Согласуем цели и план работы");
  await page.getByLabel("Длительность").selectOption("120");
  await page.getByRole("button", { name: "Создать тип события", exact: true }).click();
  await expect(types.filter({ hasText: eventTypeName })).toHaveCount(1);

  await page.goto("/book");
  await page.getByRole("button", { name: `${eventTypeName} · 120 минут`, exact: true }).click();
  const days = page.getByRole("list", { name: "Дни записи" }).getByRole("button");
  const intervals = page.getByRole("list", { name: "Интервалы" }).getByRole("button");
  const availableIntervals = page
    .getByRole("list", { name: "Интервалы" })
    .locator("button:enabled");
  let selectedDay = 0;
  let selectedTime = "";
  for (let day = 0; day < 14; day += 1) {
    const dayButton = days.nth(day);
    if ((await dayButton.getAttribute("aria-pressed")) !== "true") {
      await dayButton.click();
    }
    await expect(intervals).toHaveCount(15);
    if ((await availableIntervals.count()) > 0) {
      selectedDay = day;
      selectedTime = (await availableIntervals.first().textContent())?.trim() || "";
      await availableIntervals.first().click();
      break;
    }
  }
  expect(selectedTime).not.toBe("");

  await page.getByRole("button", { name: "Продолжить" }).click();
  await page.getByLabel("Имя").fill(guestName);
  await page.getByLabel("Email").fill(guestEmail);
  await page.getByRole("button", { name: "Подтвердить запись" }).click();
  await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();

  await page.getByRole("button", { name: "Забронировать ещё" }).click();
  await page.getByRole("button", { name: `${eventTypeName} · 120 минут`, exact: true }).click();
  const bookedDay = days.nth(selectedDay);
  await expect(bookedDay).toBeVisible();
  if ((await bookedDay.getAttribute("aria-pressed")) !== "true") {
    await bookedDay.click();
  }
  const bookedInterval = intervals.filter({ hasText: selectedTime });
  await expect(bookedInterval).toHaveCount(1);
  await expect(bookedInterval).toBeDisabled();
  await expect(bookedInterval).toContainText("Занято");

  await page.goto("/events");
  const booking = page.getByRole("article").filter({ hasText: eventTypeName });
  await expect(booking).toHaveCount(1);
  await expect(booking).toContainText(guestName);
  await expect(booking).toContainText(guestEmail);
  await expect(booking).toContainText("120 минут");
});
