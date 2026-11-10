import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testIgnore: "external.spec.ts",
  fullyParallel: true,
  workers: 1,
  forbidOnly: true,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1400, height: 1050 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm dev --host 127.0.0.1 --port 5174 --strictPort",
    url: "http://127.0.0.1:5174",
    reuseExistingServer: false,
    env: { CALENDAR_API_TEST_URL: "http://127.0.0.1:8001" },
  },
});
