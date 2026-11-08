import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";

import { expect, test } from "@playwright/test";

let backend: ChildProcess | undefined;

async function waitForBackend(server: ChildProcess) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error("Backend exited before becoming ready");
    }
    try {
      const response = await fetch("http://127.0.0.1:8000/api/health");
      if (response.ok) {
        return;
      }
    } catch {
      // Сервер ещё запускается.
    }
    await delay(100);
  }
  throw new Error("Backend did not become ready");
}

async function startBackend(args: string[] = []) {
  backend = spawn(
    "uv",
    ["run", "--directory", "../backend", "python", "../frontend/tests/backend_server.py", ...args],
    { detached: process.platform !== "win32", stdio: "ignore" },
  );
  await waitForBackend(backend);
}

test.describe.serial("типы событий", () => {
  test.afterEach(async () => {
    if (backend?.exitCode === null && backend.pid) {
      if (process.platform === "win32") {
        const taskkill = spawn("taskkill", ["/pid", String(backend.pid), "/T", "/F"], {
          stdio: "ignore",
        });
        await once(taskkill, "exit");
      } else {
        const exited = once(backend, "exit");
        process.kill(-backend.pid, "SIGTERM");
        await Promise.race([exited, delay(5000)]);
      }
    }
    backend = undefined;
  });

  test("открывается из навигации и показывает стартовые типы из API", async ({ page }) => {
    await startBackend();
    await page.goto("/");
    const requestThroughProxy = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return url.origin === "http://127.0.0.1:5173" && url.pathname === "/api/event-types";
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
});
