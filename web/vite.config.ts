import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { playwright } from "@vitest/browser-playwright";
import Ajv2020 from "ajv/dist/2020.js";
import standaloneCode from "ajv/dist/standalone/index.js";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const SCHEMA = fileURLToPath(new URL("../docs/mtpc.schema.json", import.meta.url));
const SCHEMA_MODULE = "virtual:mtpc-schema";

// The runtime checks each .mtpc against docs/mtpc.schema.json with a validator that Ajv writes
// from the schema at each build, so the runtime carries no schema compiler and a change to the
// schema needs no edit here. Messages are left out of the code to keep it small: the runtime
// writes its own (src/schema.ts).
function mtpcSchema(): Plugin {
  return {
    name: "mtpc-schema",
    resolveId: (id) => (id === SCHEMA_MODULE ? `\0${SCHEMA_MODULE}` : undefined),
    load(id) {
      if (id !== `\0${SCHEMA_MODULE}`) return undefined;
      this.addWatchFile(SCHEMA);
      const ajv = new Ajv2020({
        code: { source: true, esm: true, optimize: true },
        messages: false,
        inlineRefs: false,
        // Strict about keywords that Ajv does not know, but the schema may give a type more than
        // one kind of value, and a list of fixed items no upper length.
        strictSchema: true,
        strictTypes: false,
        strictTuples: false,
        strictRequired: false,
      });
      const code = standaloneCode(ajv, ajv.compile(JSON.parse(readFileSync(SCHEMA, "utf8"))));
      // Ajv writes require() for its few helper functions even in an ES module. The helpers are
      // CommonJS modules, and the build and the test server in a browser give their default
      // export differently: as the function, or as the object that holds it.
      const imports: string[] = [];
      const body = code.replace(/require\("([^"]+)"\)\.default/g, (_, path: string) => {
        const n = imports.length;
        imports.push(
          `import helper${n}Module from "${path}.js";`,
          `const helper${n} = typeof helper${n}Module === "function" ? helper${n}Module : helper${n}Module.default;`,
        );
        return `helper${n}`;
      });
      return `${imports.join("\n")}\n${body}`;
    },
  };
}

// One ES module file each, so mtp build can put them inside a standalone HTML page: the runtime,
// and, built apart with --mode inventory so that the runtime an author loads does not grow, the
// script of the inventory page mtp build writes.
export default defineConfig(({ mode }) => {
  const inventory = mode === "inventory";
  return {
    plugins: [mtpcSchema()],
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
          test: { name: "unit", environment: "happy-dom", include: ["test/*.test.ts", "test/conformance/*.test.ts"] },
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
