// The runtime's check of a .mtpc against docs/spec/mtpc.schema.json (src/schema.ts) handles only the
// keywords that the schema uses. These tests check that it gives the same answers as Ajv, a full
// validator of JSON Schema 2020-12, for every .mtpc that `just web-examples` compiles, and for many
// files made from them by changing one value each.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import { schemaProblem } from "../src/schema.ts";

const SCHEMA = JSON.parse(readFileSync(resolve(import.meta.dirname, "../../docs/spec/mtpc.schema.json"), "utf8")) as object;
const ajv = new Ajv2020({ strict: false }).compile(SCHEMA);

const raw = import.meta.glob("./data/**/*.mtpc", { query: "?raw", import: "default", eager: true });
const files = Object.entries(raw).map(([name, text]) => [name, JSON.parse(text as string)] as const);
// The changed files are copies, so only the smaller files are changed, to keep the test quick.
const small = files.filter(([name]) => (raw[name] as string).length < 100_000);

/** Every place in a JSON value, as a list of keys from the top. */
function places(value: unknown, at: (string | number)[] = [], found: (string | number)[][] = []): (string | number)[][] {
  found.push(at);
  if (Array.isArray(value)) value.forEach((v, i) => places(v, [...at, i], found));
  else if (value && typeof value === "object") for (const [k, v] of Object.entries(value)) places(v, [...at, k], found);
  return found;
}

// A small random number generator with a fixed seed, so each run makes the same files.
function random(seed: number): () => number {
  return () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed / 2147483648;
  };
}

const REPLACEMENTS: unknown[] = ["x", "", 7, -1, 0.5, null, true, [], {}, [0], ["lit"], { kind: "circle" }];

/** A copy of doc with one change at the given place: a value replaced, removed, added or doubled. */
function changed(doc: unknown, at: (string | number)[], pick: () => number): unknown {
  const copy = structuredClone(doc);
  if (at.length === 0) return REPLACEMENTS[Math.floor(pick() * REPLACEMENTS.length)];
  let parent = copy as Record<string | number, unknown>;
  for (const k of at.slice(0, -1)) parent = parent[k] as Record<string | number, unknown>;
  const key = at.at(-1)!;
  const how = Math.floor(pick() * 4);
  if (how === 0 && Array.isArray(parent)) parent.splice(key as number, 1);
  else if (how === 0) delete parent[key];
  else if (how === 1 && Array.isArray(parent)) parent.splice(key as number, 0, parent[key]);
  else if (how === 1) parent["zz"] = 1;
  else parent[key] = REPLACEMENTS[Math.floor(pick() * REPLACEMENTS.length)];
  return copy;
}

describe("the runtime's schema check", () => {
  it("has files to check", () => {
    if (files.length === 0) throw new Error("the examples are not compiled; run just web-examples");
  });

  it("finds that every compiled .mtpc matches the schema", () => {
    for (const [name, doc] of files) {
      expect(ajv(doc), name).toBe(true);
      expect(schemaProblem(doc), name).toBe(null);
    }
  });

  it("gives the same answer as Ajv for files changed in one place", () => {
    const pick = random(1);
    let refused = 0;
    for (const [name, doc] of small) {
      const all = places(doc);
      for (let n = 0; n < 30; n++) {
        const at = all[Math.floor(pick() * all.length)]!;
        const bad = changed(doc, at, pick);
        const ajvMatches = ajv(bad);
        const found = schemaProblem(bad);
        expect(found === null, `${name}, changed at /${at.join("/")}: ${found}`).toBe(ajvMatches);
        if (!ajvMatches) refused++;
      }
    }
    // Most changes break the schema, so the test checks refusals and not only files that match.
    expect(refused).toBeGreaterThan(small.length * 10);
  });
});

type Listener = { kind: string; shape?: number | null; in?: number[] };

/** Changes each listener that `which` picks, in every smaller file, one at a time, and checks that
 * Ajv and the runtime's check both refuse the file, with the runtime's message holding `words`. */
function refusesListeners(which: (l: Listener) => boolean, change: (l: Listener) => void, words: string): number {
  let changed = 0;
  for (const [name, doc] of small) {
    const objects = (doc as { objects: Listener[] }).objects;
    objects.forEach((listener, i) => {
      if (!listener.kind.startsWith("on-") || !which(listener)) return;
      const before = structuredClone(listener);
      change(listener);
      const ajvMatches = ajv(doc);
      const found = schemaProblem(doc);
      objects[i] = before;
      expect(ajvMatches, `${name}, object ${i}`).toBe(false);
      expect(found, `${name}, object ${i}`).toContain(`at /objects/${i}`);
      expect(found, `${name}, object ${i}`).toContain(words);
      changed++;
    });
  }
  return changed;
}

describe("the runtime's schema check of listeners", () => {
  it("refuses a listener on a shape with no in, as Ajv does", () => {
    const n = refusesListeners(
      (l) => l.shape != null,
      (l) => delete l.in,
      `the member "in" is missing`,
    );
    expect(n).toBeGreaterThan(0);
  });

  it("refuses a listener on a shape with two views in its in, as Ajv does", () => {
    const n = refusesListeners(
      (l) => l.shape != null,
      (l) => (l.in = [l.in![0]!, l.in![0]! + 1]),
      `the list must have at most 1 item`,
    );
    expect(n).toBeGreaterThan(0);
  });

  it("refuses an on-pointermove on its own view that has an in, as Ajv does", () => {
    const n = refusesListeners(
      (l) => l.kind === "on-pointermove" && l.shape === null,
      (l) => (l.in = [0]),
      `the member "in" must not be here`,
    );
    expect(n).toBeGreaterThan(0);
  });
});
