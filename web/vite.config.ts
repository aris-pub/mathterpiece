import { playwright } from "@vitest/browser-playwright";
import { defineConfig } from "vitest/config";

// One ES module file, so mtp build can put the whole runtime inside a standalone HTML page.
export default defineConfig({
  build: {
    lib: { entry: "src/index.ts", formats: ["es"], fileName: () => "mathterpiece.js" },
    outDir: "dist",
  },
  test: {
    projects: [
      {
        extends: true,
        test: { name: "unit", environment: "happy-dom", include: ["test/*.test.ts"] },
      },
      // What happy-dom cannot do, such as CSS variables and color-mix, runs in a real browser.
      {
        extends: true,
        test: {
          name: "browser",
          include: ["test/browser/*.test.ts"],
          browser: { enabled: true, provider: playwright(), headless: true, instances: [{ browser: "chromium" }] },
        },
      },
    ],
  },
});
