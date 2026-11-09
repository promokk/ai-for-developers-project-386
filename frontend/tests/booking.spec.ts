import type { APIRequestContext, Page } from "@playwright/test";

import { moscowDate } from "../src/moscowDate";
import { expect, startBackend, test } from "./backend";

test.describe.serial("бронирование гостем", () => {
  test("проходит путь от выбора слота до успеха и нового сценария", async ({ page }) => {
    await startBackend();
    await page.goto("/book");

    const typeButtons = page.getByRole("group", { name: "Тип события" }).getByRole("button");
    await expect(typeButtons).toHaveCount(3);
    await expect(typeButtons.first()).toHaveAttribute("aria-pressed", "true");
    const days = page.getByRole("list", { name: "Дни записи" }).getByRole("listitem");
    await expect(days).toHaveCount(14);
    await expect(page.getByText("Europe/Moscow", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeDisabled();

    const intervals = page.getByRole("list", { name: "Интервалы" }).getByRole("button");
    await expect(intervals).toHaveCount(18);
    await intervals.first().click();
    await page.getByRole("button", { name: "Продолжить" }).click();

    await expect(page.getByRole("heading", { name: "Подтверждение записи" })).toBeVisible();
    await page.getByRole("button", { name: "Подтвердить запись" }).click();
    await expect(page.getByText("Введите имя", { exact: true })).toBeVisible();
    await expect(page.getByText("Введите email", { exact: true })).toBeVisible();
    await page.getByLabel("Имя").fill("Иван Петров");
    await page.getByLabel("Email").fill("ivan@example.com");
    await page.getByRole("button", { name: "Подтвердить запись" }).click();

    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
    await expect(page.getByText("Иван Петров", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Забронировать ещё" }).click();
    await expect(page.getByRole("group", { name: "Тип события" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeDisabled();
  });

  test("отклоняет управляющие символы в email до отправки", async ({ page }) => {
    await startBackend();
    let bookingRequests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/api/bookings" && request.method() === "POST") {
        bookingRequests += 1;
      }
    });

    for (const control of ["\u0000", "\u001f", "\u007f", "\u0080", "\u009f"]) {
      await openConfirmation(page);
      await page.getByLabel("Email").fill(`guest${control}@example.com`);
      await page.getByRole("button", { name: "Подтвердить запись" }).click();
      await expect(page.getByText("Введите корректный email", { exact: true })).toBeVisible();
      expect(bookingRequests).toBe(0);
    }
  });
});

function tomorrowMoscow() {
  return moscowDate(1);
}

async function bookSlot(
  request: APIRequestContext,
  eventTypeId: string,
  date: string,
  slot: number,
) {
  const hour = 9 + Math.floor(slot / 2);
  const minute = slot % 2 ? "30" : "00";
  const response = await request.post("/api/bookings", {
    data: {
      eventTypeId,
      startsAt: `${date}T${String(hour).padStart(2, "0")}:${minute}+03:00`,
      guestName: "Гость",
      guestEmail: "guest@example.com",
    },
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
  expect(response.status(), await response.text()).toBe(201);
}

test.describe.serial("бронирование: выбор и конфликт", () => {
  test("показывает занятый интервал и сбрасывает время при смене типа", async ({
    page,
    request,
  }) => {
    await startBackend();
    const types = (await (await request.get("/api/event-types")).json()) as Array<{
      id: string;
    }>;
    const date = tomorrowMoscow();
    const occupied = await request.post("/api/bookings", {
      data: {
        eventTypeId: types[0].id,
        startsAt: `${date}T09:00+03:00`,
        guestName: "Первый гость",
        guestEmail: "first@example.com",
      },
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    expect(occupied.status()).toBe(201);

    await page.goto("/book");
    const firstInterval = page.getByRole("list", { name: "Интервалы" }).getByRole("button").first();
    await expect(firstInterval).toBeDisabled();
    await expect(firstInterval).toContainText("Занято");
    const days = page.getByRole("list", { name: "Дни записи" }).getByRole("button");
    await days.nth(1).click();
    await page.getByRole("list", { name: "Интервалы" }).getByRole("button").first().click();
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeEnabled();

    await page.getByRole("button", { name: /Консультация · 60 минут/ }).click();

    await expect(days.nth(1)).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeDisabled();
    await expect(page.getByRole("list", { name: "Интервалы" }).getByRole("button")).toHaveCount(17);
  });

  test("после конфликта обновляет интервалы и сохраняет контакты", async ({ page, request }) => {
    await startBackend();
    const types = (await (await request.get("/api/event-types")).json()) as Array<{
      id: string;
    }>;
    const startsAt = `${tomorrowMoscow()}T09:00+03:00`;
    await page.goto("/book");
    await page.getByRole("list", { name: "Интервалы" }).getByRole("button").first().click();
    await page.getByRole("button", { name: "Продолжить" }).click();
    await page.getByLabel("Имя").fill("Иван Петров");
    await page.getByLabel("Email").fill("ivan@example.com");
    const occupied = await request.post("/api/bookings", {
      data: {
        eventTypeId: types[0].id,
        startsAt,
        guestName: "Другой гость",
        guestEmail: "other@example.com",
      },
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    expect(occupied.status()).toBe(201);

    await page.getByRole("button", { name: "Подтвердить запись" }).click();

    await expect(page.getByRole("alert")).toHaveText("Это время уже занято");
    await expect(page.getByRole("group", { name: "Тип события" })).toBeVisible();
    await expect(
      page.getByRole("list", { name: "Интервалы" }).getByRole("button").first(),
    ).toBeDisabled();
    await expect(page.getByRole("button", { name: "Продолжить" })).toBeDisabled();
    await page.getByRole("list", { name: "Интервалы" }).getByRole("button").nth(1).click();
    await page.getByRole("button", { name: "Продолжить" }).click();
    await expect(page.getByLabel("Имя")).toHaveValue("Иван Петров");
    await expect(page.getByLabel("Email")).toHaveValue("ivan@example.com");
  });
});

test.describe.serial("бронирование: пустые состояния", () => {
  test("предлагает ближайший свободный день для занятой даты", async ({ page, request }) => {
    test.setTimeout(60_000);
    await startBackend();
    const types = (await (await request.get("/api/event-types")).json()) as Array<{
      id: string;
    }>;
    const date = tomorrowMoscow();
    for (let slot = 0; slot < 18; slot += 1) {
      await bookSlot(request, types[0].id, date, slot);
    }

    await page.goto("/book");

    await expect(page.getByText("На эту дату всё занято", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Перейти к ближайшему свободному дню" }).click();
    await expect(
      page.getByRole("list", { name: "Дни записи" }).getByRole("button").nth(1),
    ).toHaveAttribute("aria-pressed", "true");
  });

  test("показывает отдельное сообщение при полностью занятом окне", async ({ page, request }) => {
    test.setTimeout(90_000);
    await startBackend();
    const types = (await (await request.get("/api/event-types")).json()) as Array<{
      id: string;
    }>;
    const firstDay = new Date(`${tomorrowMoscow()}T00:00:00Z`);
    for (let day = 0; day < 14; day += 1) {
      for (let slot = 0; slot < 18; slot += 1) {
        const date = firstDay.toISOString().slice(0, 10);
        await bookSlot(request, types[0].id, date, slot);
      }
      firstDay.setUTCDate(firstDay.getUTCDate() + 1);
    }

    await page.goto("/book");

    await expect(
      page.getByText("В ближайшие 14 дней нет свободных слотов", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Выберите другой тип события или вернитесь позже.", { exact: true }),
    ).toBeVisible();
  });
});

async function openConfirmation(page: Page) {
  await page.goto("/book");
  await page.getByRole("list", { name: "Интервалы" }).getByRole("button").first().click();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await page.getByLabel("Имя").fill("Иван Петров");
  await page.getByLabel("Email").fill("ivan@example.com");
}

test.describe.serial("бронирование: повторная отправка", () => {
  test("создаёт один активный POST при двух синхронных submit", async ({ page }) => {
    await startBackend();
    await openConfirmation(page);
    let bookingRequests = 0;
    let markPostSeen!: () => void;
    const postSeen = new Promise<void>((resolve) => {
      markPostSeen = resolve;
    });
    let releasePost!: () => void;
    const postReleased = new Promise<void>((resolve) => {
      releasePost = resolve;
    });
    await page.route("**/api/bookings", async (route) => {
      bookingRequests += 1;
      markPostSeen();
      await postReleased;
      await route.continue();
    });

    await page.locator("form.confirmation-form").evaluate((form) => {
      const submit = () =>
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      window.addEventListener("submit", submit, { once: true });
      submit();
    });
    await postSeen;
    const requestsDuringDoubleSubmit = bookingRequests;
    releasePost();

    expect(requestsDuringDoubleSubmit).toBe(1);
    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
  });

  test("сохраняет данные после 5xx и разрешает ручной повтор", async ({ page }) => {
    await startBackend(["--booking-failures", "1"]);
    await openConfirmation(page);

    await page.getByRole("button", { name: "Подтвердить запись" }).click();

    await expect(page.getByRole("alert")).toContainText("Не удалось подтвердить запись");
    await expect(page.getByLabel("Имя")).toHaveValue("Иван Петров");
    await expect(page.getByLabel("Email")).toHaveValue("ivan@example.com");
    await expect(page.getByLabel("Имя")).toBeEnabled();
    await page.getByRole("button", { name: "Попробовать снова" }).click();
    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
  });

  test("сохраняет данные при сетевой ошибке и не создаёт дубль при повторе", async ({
    page,
    context,
    request,
  }) => {
    await startBackend();
    await openConfirmation(page);
    await context.setOffline(true);

    await page.getByRole("button", { name: "Подтвердить запись" }).click();

    await expect(page.getByRole("alert")).toContainText("Не удалось подтвердить запись");
    await context.setOffline(false);
    await page.getByRole("button", { name: "Попробовать снова" }).click();
    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
    const bookings = await request.get("/api/bookings?scope=upcoming");
    expect(await bookings.json()).toHaveLength(1);
  });

  test("прерывает ожидание через 10 секунд и повторяет тем же ключом", async ({
    page,
    request,
  }) => {
    test.setTimeout(40_000);
    await startBackend(["--booking-delay", "11"]);
    await openConfirmation(page);

    await page.getByRole("button", { name: "Подтвердить запись" }).click();
    await expect(page.getByLabel("Имя")).toBeDisabled();
    await expect(page.getByRole("button", { name: "Отправляем…" })).toBeDisabled();
    await expect(page.getByRole("alert")).toContainText("Не удалось подтвердить запись", {
      timeout: 12_000,
    });
    await page.getByRole("button", { name: "Попробовать снова" }).click();

    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
    expect(await (await request.get("/api/bookings?scope=upcoming")).json()).toHaveLength(1);
  });

  test("повтор после потерянного успешного ответа не создаёт дубль", async ({ page, request }) => {
    await startBackend(["--drop-booking-response", "1"]);
    await openConfirmation(page);
    await page.getByRole("button", { name: "Подтвердить запись" }).click();
    await expect(page.getByRole("alert")).toContainText("Не удалось подтвердить запись");

    await page.getByRole("button", { name: "Попробовать снова" }).click();

    await expect(page.getByRole("heading", { name: "Запись подтверждена" })).toBeVisible();
    expect(await (await request.get("/api/bookings?scope=upcoming")).json()).toHaveLength(1);
  });

  test("запрещает изменение данных после закрепления ключа", async ({ page }) => {
    await startBackend(["--drop-booking-response", "1"]);
    await openConfirmation(page);
    await page.getByRole("button", { name: "Подтвердить запись" }).click();
    await expect(page.getByRole("alert")).toContainText("Не удалось подтвердить запись");
    await page.getByLabel("Имя").fill("Другой гость");

    await page.getByRole("button", { name: "Попробовать снова" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Данные изменились после попытки отправки. Начните бронирование заново",
    );
    await expect(page.getByRole("button", { name: "Попробовать снова" })).toHaveCount(0);
    await expect(page.getByLabel("Имя")).toBeDisabled();
    await expect(page.getByRole("button", { name: "Вернуться к выбору времени" })).toBeVisible();
  });
});
