import { expect, test } from "@playwright/test";

test("главная открывается без обращений к API", async ({ page }) => {
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api")) {
      apiRequests.push(request.url());
    }
  });

  await page.goto("/");

  await expect(page).toHaveTitle("Calendar — запись на звонок");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Calendar");
  await expect(
    page.getByText(
      "Один экран, понятные слоты, быстрая бронь. Выберите время и запишитесь на звонок без лишних шагов.",
    ),
  ).toBeVisible();
  await expect(page.getByText("Бронирование слотов с 09:00 до 18:00.")).toBeVisible();
  await expect(page.getByText("Проверка конфликта при бронировании.")).toBeVisible();
  await expect(
    page.getByText("Предпросмотр предстоящих событий в отдельном разделе."),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    ),
  ).toBe(false);
  expect(apiRequests).toEqual([]);
});

test("ссылка в шапке ведёт на страницу записи", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("navigation").getByRole("link", { name: "Записаться", exact: true }).click();

  await expect(page).toHaveURL(/\/book$/);
});

test("основная кнопка ведёт на страницу записи", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("main").getByRole("link", { name: "Записаться", exact: true }).click();

  await expect(page).toHaveURL(/\/book$/);
});
