import { defineConfig } from "vitest/config";

// One ES module file, so mtp build can put the whole runtime inside a standalone HTML page.
export default defineConfig({
  build: {
    lib: { entry: "src/index.ts", formats: ["es"], fileName: () => "mathterpiece.js" },
    outDir: "dist",
  },
  test: { environment: "happy-dom" },
});
