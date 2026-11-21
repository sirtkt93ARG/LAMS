import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
});
