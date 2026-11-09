import { expect, startBackend, test } from "./backend";

test.describe.serial("типы событий", () => {
  test("открывается из навигации и показывает стартовые типы из API", async ({ page }) => {
    await startBackend();
    await page.goto("/");
    const requestThroughProxy = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return url.origin === "http://127.0.0.1:5174" && url.pathname === "/api/event-types";
    });
    await page
      .getByRole("navigation")
      .getByRole("link", { name: "Типы событий", exact: true })
      .click();

    await requestThroughProxy;
    await expect(page).toHaveURL(/\/event-types$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Типы событий");
    const items = page.getByRole("list", { name: "Доступные типы событий" }).getByRole("listitem");
    await expect(items).toHaveCount(3);
    await expect(items.nth(0)).toContainText("Знакомство");
    await expect(items.nth(0)).toContainText(
      "Короткий звонок, чтобы познакомиться, обсудить задачу и определить следующие шаги",
    );
    await expect(items.nth(0)).toContainText("30 минут");
    await expect(items.nth(1)).toContainText("Консультация");
    await expect(items.nth(1)).toContainText(
      "Подробное обсуждение вашего вопроса, разбор возможных решений и следующих шагов",
    );
    await expect(items.nth(1)).toContainText("60 минут");
    await expect(items.nth(2)).toContainText("Глубокий разбор");
    await expect(items.nth(2)).toContainText(
      "Детальный разбор сложной задачи и составление конкретного плана действий",
    );
    await expect(items.nth(2)).toContainText("90 минут");
  });

  test("показывает загрузку до получения списка", async ({ page }) => {
    await startBackend(["--delay", "1"]);
    await page.goto("/event-types");

    await expect(page.getByText("Загрузка типов событий…")).toBeVisible();
    await expect(page.getByRole("list", { name: "Доступные типы событий" })).toBeVisible();
  });

  test("показывает ошибку и повторяет загрузку по кнопке", async ({ page }) => {
    await startBackend(["--failures", "2"]);
    await page.goto("/event-types");

    await expect(page.getByRole("alert")).toHaveText("Не удалось загрузить типы событий");
    await page.getByRole("button", { name: "Повторить", exact: true }).click();

    await expect(page.getByRole("list", { name: "Доступные типы событий" })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("показывает пустое состояние и переход к созданию", async ({ page }) => {
    await startBackend(["--empty"]);
    await page.goto("/event-types");

    await expect(page.getByText("Типов событий пока нет")).toBeVisible();
    const createLink = page.getByRole("link", { name: "Создать тип события", exact: true });
    await expect(createLink).toHaveAttribute("href", "/event-types/new");
    await expect(page.getByRole("list", { name: "Доступные типы событий" })).toHaveCount(0);
  });

  test("создаёт тип через реальный API и показывает его в конце списка", async ({ page }) => {
    await startBackend();
    await page.goto("/event-types");
    await page.getByRole("link", { name: "Создать тип события", exact: true }).click();

    await expect(page).toHaveURL(/\/event-types\/new$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Новый тип события");
    await expect(page.getByLabel("Название")).toHaveValue("");
    await expect(page.getByLabel("Описание")).toHaveValue("");
    await expect(page.getByLabel("Длительность")).toHaveValue("30");

    const createRequest = page.waitForRequest(
      (request) =>
        new URL(request.url()).pathname === "/api/event-types" && request.method() === "POST",
    );
    await page.getByLabel("Название").fill("  Планирование спринта  ");
    await page.getByLabel("Описание").fill("  Определим цели.\nСоставим план.  ");
    await page.getByRole("button", { name: "Создать тип события", exact: true }).click();
    await createRequest;

    await expect(page).toHaveURL(/\/event-types\?created=1$/);
    await expect(page.getByText("Тип события создан", { exact: true })).toBeVisible();
    const items = page.getByRole("list", { name: "Доступные типы событий" }).getByRole("listitem");
    await expect(items).toHaveCount(4);
    await expect(items.nth(3)).toContainText("Планирование спринта");
    await expect(items.nth(3)).toContainText("Определим цели.\nСоставим план.");
    await expect(items.nth(3)).toContainText("30 минут");
  });

  test("показывает ошибки API у полей, фокусирует первое и сохраняет значения", async ({
    page,
  }) => {
    await startBackend();
    await page.goto("/event-types/new");
    const longDescription = "д".repeat(501);
    await page.getByLabel("Название").fill("   ");
    await page.getByLabel("Описание").fill(longDescription);
    await page.getByLabel("Длительность").selectOption("60");

    await page.getByRole("button", { name: "Создать тип события", exact: true }).click();

    await expect(page.getByText("Введите название", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Описание не должно превышать 500 символов", { exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Название")).toBeFocused();
    await expect(page.getByLabel("Название")).toHaveValue("   ");
    await expect(page.getByLabel("Описание")).toHaveValue(longDescription);
    await expect(page.getByLabel("Длительность")).toHaveValue("60");
    await expect(page).toHaveURL(/\/event-types\/new$/);
  });

  test("показывает общий сбой без очистки формы и позволяет повторить", async ({ page }) => {
    await startBackend(["--failures", "1"]);
    await page.goto("/event-types/new");
    await page.getByLabel("Название").fill("Повторная отправка");
    await page.getByLabel("Описание").fill("Данные не должны пропасть");
    await page.getByLabel("Длительность").selectOption("120");

    await page.getByRole("button", { name: "Создать тип события", exact: true }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Не удалось создать тип события. Попробуйте ещё раз",
    );
    await expect(page.getByLabel("Название")).toHaveValue("Повторная отправка");
    await expect(page.getByLabel("Описание")).toHaveValue("Данные не должны пропасть");
    await expect(page.getByLabel("Длительность")).toHaveValue("120");
    await expect(page).toHaveURL(/\/event-types\/new$/);

    await page.getByRole("button", { name: "Создать тип события", exact: true }).click();
    await expect(page).toHaveURL(/\/event-types\?created=1$/);
    await expect(page.getByText("Тип события создан", { exact: true })).toBeVisible();
  });

  test("блокирует повторную отправку во время создания", async ({ page }) => {
    await startBackend(["--delay", "0.5"]);
    await page.goto("/event-types/new");
    await page.getByLabel("Название").fill("Только один тип");
    let createRequests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/api/event-types" && request.method() === "POST") {
        createRequests += 1;
      }
    });
    const submit = page.getByRole("button", { name: "Создать тип события", exact: true });

    await submit.click();
    await expect(submit).toBeDisabled();
    await page.locator("form").evaluate((form) => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    await expect(page).toHaveURL(/\/event-types\?created=1$/);
    expect(createRequests).toBe(1);
  });

  test("запрашивает подтверждение при отмене изменённой формы", async ({ page }) => {
    await startBackend();
    await page.goto("/event-types/new");
    await page.getByLabel("Название").fill("Несохранённый тип");
    await page.getByLabel("Описание").fill("Черновик");

    page.once("dialog", (dialog) => void dialog.dismiss());
    await page.getByRole("link", { name: "Отмена", exact: true }).click();

    await expect(page).toHaveURL(/\/event-types\/new$/);
    await expect(page.getByLabel("Название")).toHaveValue("Несохранённый тип");
    await expect(page.getByLabel("Описание")).toHaveValue("Черновик");

    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("link", { name: "Отмена", exact: true }).click();
    await expect(page).toHaveURL(/\/event-types$/);
    await expect(page.getByText("Несохранённый тип", { exact: true })).toHaveCount(0);
  });

  test("закрывает неизменённую форму без подтверждения и сохранения", async ({ page }) => {
    await startBackend();
    await page.goto("/event-types/new");
    let dialogs = 0;
    page.on("dialog", (dialog) => {
      dialogs += 1;
      void dialog.dismiss();
    });

    await page.getByRole("link", { name: "Отмена", exact: true }).click();

    await expect(page).toHaveURL(/\/event-types$/);
    await expect(
      page.getByRole("list", { name: "Доступные типы событий" }).getByRole("listitem"),
    ).toHaveCount(3);
    expect(dialogs).toBe(0);
  });
});
