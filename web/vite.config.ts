import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { playwright } from "@vitest/browser-playwright";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const SCHEMA = fileURLToPath(new URL("../docs/spec/mtpc.schema.json", import.meta.url));
const SCHEMA_MODULE = "virtual:mtpc-schema";

// The keywords that the runtime's check of a .mtpc handles (src/schema.ts), and what each one holds:
// a schema, a list of schemas, a map of schemas, or something else.
const KEYWORDS: Record<string, "schema" | "list" | "map" | "data"> = {
  $ref: "data",
  type: "data",
  const: "data",
  enum: "data",
  minimum: "data",
  maximum: "data",
  exclusiveMinimum: "data",
  exclusiveMaximum: "data",
  minLength: "data",
  maxLength: "data",
  minItems: "data",
  maxItems: "data",
  uniqueItems: "data",
  prefixItems: "list",
  items: "schema",
  required: "data",
  properties: "map",
  additionalProperties: "schema",
  allOf: "list",
  anyOf: "list",
  oneOf: "list",
  if: "schema",
  then: "schema",
  else: "schema",
  not: "schema",
  $defs: "map",
  $schema: "data",
  $id: "data",
  title: "data",
  description: "data",
};

/** The first keyword in a schema that the runtime's check does not handle, with where it is. */
function unknownKeyword(schema: unknown, at: string): string | null {
  if (typeof schema === "boolean") return null;
  for (const [keyword, sub] of Object.entries(schema as Record<string, unknown>)) {
    const kind = KEYWORDS[keyword];
    if (!kind) return `${keyword} at ${at}`;
    if (keyword === "$ref" && !String(sub).startsWith("#")) return `$ref to ${String(sub)} at ${at}`;
    const subs: [string, unknown][] =
      kind === "schema"
        ? [["", sub]]
        : kind === "list"
          ? (sub as unknown[]).map((s, i) => [`/${i}`, s])
          : kind === "map"
            ? Object.entries(sub as object).map(([k, s]) => [`/${k}`, s])
            : [];
    for (const [step, s] of subs) {
      const found = unknownKeyword(s, `${at}/${keyword}${step}`);
      if (found) return found;
    }
  }
  return null;
}

// The runtime checks each .mtpc against docs/spec/mtpc.schema.json, which this puts in the runtime, so a
// change to the schema needs no edit in the runtime. The build fails when the schema uses a keyword
// that the check does not handle. The schema goes in as a string for JSON.parse, so that the build
// does not spread it over thousands of lines.
function mtpcSchema(): Plugin {
  return {
    name: "mtpc-schema",
    resolveId: (id) => (id === SCHEMA_MODULE ? `\0${SCHEMA_MODULE}` : undefined),
    load(id) {
      if (id !== `\0${SCHEMA_MODULE}`) return undefined;
      this.addWatchFile(SCHEMA);
      const schema: unknown = JSON.parse(readFileSync(SCHEMA, "utf8"));
      const unknown = unknownKeyword(schema, "#");
      if (unknown) throw new Error(`the runtime cannot check a .mtpc against ${SCHEMA}: its check does not handle the keyword ${unknown}`);
      return `export default JSON.parse(${JSON.stringify(JSON.stringify(schema))});`;
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
          test: { name: "unit", environment: "happy-dom", include: ["test/*.test.ts", "test/conformance/**/*.test.ts"] },
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
