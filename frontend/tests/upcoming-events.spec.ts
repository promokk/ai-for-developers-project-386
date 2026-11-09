import { expect, startBackend, test } from "./backend";

test.describe.serial("предстоящие события", () => {
  test("открывается из навигации и показывает пустое состояние", async ({ page }) => {
    await startBackend();
    await page.goto("/");
    const requestThroughProxy = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        url.origin === "http://127.0.0.1:5174" &&
        url.pathname === "/api/bookings" &&
        url.searchParams.get("scope") === "upcoming"
      );
    });

    await page
      .getByRole("navigation")
      .getByRole("link", { name: "Предстоящие события", exact: true })
      .click();

    await requestThroughProxy;
    await expect(page).toHaveURL(/\/events$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Предстоящие события");
    await expect(page.getByText("Запланированные бронирования · Europe/Moscow")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Предстоящих событий нет", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Новые бронирования появятся здесь автоматически")).toBeVisible();
    await expect(page.getByRole("main").getByRole("link", { name: "Записаться" })).toHaveCount(0);
  });

  test("показывает повестку по московским дням и скрывает завершённое событие", async ({
    page,
  }) => {
    await page.clock.install({ time: new Date("2026-03-27T09:00:00Z") });
    await startBackend(["--agenda", "--now", "2026-03-27T12:00:00+03:00"]);
    await page.goto("/events");

    const today = page.getByRole("region", { name: "пятница, 27 марта" });
    const tomorrow = page.getByRole("region", { name: "суббота, 28 марта" });
    await expect(page.getByRole("region")).toHaveCount(2);
    await expect(today).toBeVisible();
    await expect(tomorrow).toBeVisible();
    const items = page.getByRole("article");
    await expect(items).toHaveCount(3);

    const current = items.nth(0);
    await expect(current).toContainText("11:30");
    await expect(current).toContainText("12:30");
    await expect(current).toContainText("Знакомство");
    await expect(current).toContainText("30 минут");
    await expect(current).toContainText("Анна Смирнова");
    await expect(current.getByRole("link", { name: "anna@example.com" })).toHaveAttribute(
      "href",
      "mailto:anna@example.com",
    );
    await expect(current).toContainText("Идёт сейчас");
    await expect(current).not.toContainText("current-booking-id");
    await expect(current).not.toContainText("Короткий звонок");

    const later = items.nth(1);
    await expect(later).toContainText("14:00");
    await expect(later).toContainText("15:30");
    await expect(later).toContainText("Глубокий разбор");
    await expect(later).toContainText("90 минут");
    await expect(later).toContainText("Игорь Петров");
    await expect(later).toContainText("igor@example.com");
    await expect(later).not.toContainText("Идёт сейчас");

    const nextDay = items.nth(2);
    await expect(nextDay).toContainText("09:00");
    await expect(nextDay).toContainText("10:00");
    await expect(nextDay).toContainText("Консультация");
    await expect(nextDay).toContainText("60 минут");
    await expect(nextDay).toContainText("Мария Волкова");
    await expect(nextDay).toContainText("maria@example.com");
    await expect(page.getByText("past@example.com")).toHaveCount(0);

    await page.clock.fastForward(31 * 60 * 1000);

    await expect(items).toHaveCount(2);
    await expect(page.getByText("anna@example.com")).toHaveCount(0);
    await expect(page.getByText("Идёт сейчас")).toHaveCount(0);
  });
});
