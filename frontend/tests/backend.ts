import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";

import { test as base } from "@playwright/test";

export { expect } from "@playwright/test";

let backend: ChildProcess | undefined;

async function waitForBackend(server: ChildProcess) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error("Backend exited before becoming ready");
    }
    try {
      const response = await fetch("http://127.0.0.1:8001/api/health");
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

export async function startBackend(args: string[] = []) {
  backend = spawn(
    "uv",
    ["run", "--directory", "../backend", "python", "../frontend/tests/backend_server.py", ...args],
    { detached: process.platform !== "win32", stdio: "ignore" },
  );
  await waitForBackend(backend);
}

async function stopBackend() {
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
}

export const test = base.extend<{ backendLifecycle: void }>({
  backendLifecycle: [
    async ({ request: _request }, use) => {
      await use();
      await stopBackend();
    },
    { auto: true },
  ],
});
