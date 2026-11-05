import { playwright } from "@vitest/browser-playwright";
import { defineConfig } from "vitest/config";

// One ES module file each, so mtp build can put them inside a standalone HTML page: the runtime,
// and, built apart with --mode inventory so that the runtime an author loads does not grow, the
// script of the inventory page mtp build writes.
export default defineConfig(({ mode }) => {
  const inventory = mode === "inventory";
  return {
    build: {
      lib: inventory
        ? { entry: "src/inventory-page.ts", formats: ["es"], fileName: () => "inventory.js" }
        : { entry: "src/index.ts", formats: ["es"], fileName: () => "mathterpiece.js" },
      outDir: "dist",
      emptyOutDir: !inventory,
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
  };
});
