import { expect, test } from "@playwright/test";

test("отклоняет повторную бронь и не дублирует идемпотентный retry", async ({ request }) => {
  const runId = crypto.randomUUID();
  const guestEmail = `http-${runId}@example.com`;
  const createdTypeResponse = await request.post("/api/event-types", {
    data: {
      name: `HTTP-проверка ${runId.slice(0, 8)}`,
      description: "Проверка конфликта и идемпотентности",
      durationMinutes: 30,
    },
  });
  expect(createdTypeResponse.status()).toBe(201);
  const eventType = (await createdTypeResponse.json()) as { id: string };
  const date = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(Date.now() + 24 * 60 * 60 * 1000));
  const availabilityResponse = await request.get(`/api/event-types/${eventType.id}/availability`, {
    params: { date },
  });
  expect(availabilityResponse.status()).toBe(200);
  const availability = (await availabilityResponse.json()) as {
    intervals: Array<{ startsAt: string; available: boolean }>;
  };
  const interval = availability.intervals.find((item) => item.available);
  if (!interval) {
    throw new Error("В новом типе события нет доступных интервалов");
  }

  const bookingData = {
    eventTypeId: eventType.id,
    startsAt: interval.startsAt,
    guestName: "Внешний HTTP-гость",
    guestEmail,
  };
  const idempotencyKey = crypto.randomUUID();
  const createdResponse = await request.post("/api/bookings", {
    data: bookingData,
    headers: { "Idempotency-Key": idempotencyKey },
  });
  expect(createdResponse.status()).toBe(201);
  const created = (await createdResponse.json()) as { id: string };

  const conflict = await request.post("/api/bookings", {
    data: bookingData,
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
  expect(conflict.status()).toBe(409);
  expect(await conflict.json()).toMatchObject({ code: "SLOT_CONFLICT" });

  const retry = await request.post("/api/bookings", {
    data: bookingData,
    headers: { "Idempotency-Key": idempotencyKey },
  });
  expect(retry.status()).toBe(201);
  expect(await retry.json()).toEqual(created);

  const bookingsResponse = await request.get("/api/bookings", {
    params: { scope: "upcoming" },
  });
  expect(bookingsResponse.status()).toBe(200);
  const bookings = (await bookingsResponse.json()) as Array<{ guestEmail: string }>;
  expect(bookings.filter((booking) => booking.guestEmail === guestEmail)).toEqual([created]);
});

const clientRoutes = [
  ["/", "Calendar"],
  ["/book", "Запись на звонок"],
  ["/event-types", "Типы событий"],
  ["/event-types/new", "Новый тип события"],
  ["/events", "Предстоящие события"],
] as const;

for (const [path, heading] of clientRoutes) {
  test(`открывает прямой переход на ${path}`, async ({ page }) => {
    const response = await page.goto(path);

    expect(response?.ok()).toBe(true);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
  });
}
