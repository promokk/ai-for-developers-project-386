import { defineConfig } from "@playwright/test";

const baseURL = process.env.CALENDAR_BASE_URL;
if (!baseURL) {
  throw new Error("Укажите CALENDAR_BASE_URL для внешних сценариев");
}

export default defineConfig({
  testDir: "./tests",
  testMatch: ["booking-flow.spec.ts", "external.spec.ts"],
  fullyParallel: true,
  workers: 1,
  forbidOnly: true,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    viewport: { width: 1400, height: 1050 },
    trace: "retain-on-failure",
  },
});
