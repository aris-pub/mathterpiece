// The check of a .mtpc against the schema of its version, docs/mtpc.schema.json, before the
// runtime runs any part of it (docs/spec/compiler-runtime.md, rule runtime-loads-mtpc).
//
// The build puts the schema itself in the runtime (vite.config.ts), so a change to the schema
// needs no edit here. The check handles only the keywords of JSON Schema 2020-12 that the schema
// uses, and the build fails when the schema uses another. A validator that Ajv writes from the
// schema would handle them all, but would add about 520 kB to the runtime, against under 50 kB for
// this check and the schema. test/schema.test.ts checks that Ajv and this check give the same
// answers.
import SCHEMA from "virtual:mtpc-schema";
import { SPEC_VERSION } from "./doc.ts";

type Schema = boolean | { readonly [keyword: string]: unknown };

/** The first place where a value breaks a schema: the keys from that place up to the value
 * checked, and the keyword of JSON Schema that it breaks. */
interface SchemaError {
  steps: (string | number)[];
  keyword: string;
  params: Record<string, unknown>;
}

// A check gives the first place where a value breaks a part of the schema, or null. When report
// is false, it gives FAILED in place of a new error. The tests of an if, oneOf or anyOf are run that
// way, since most of them fail on every file, and making an error for each would slow the check.
type Check = (value: unknown, report: boolean) => SchemaError | null;
const FAILED: SchemaError = Object.freeze({ steps: [], keyword: "", params: {} }) as SchemaError;

let checkDoc: Check | null = null;

/** Why a .mtpc does not match the schema, in plain words, or null when it matches. */
export function schemaProblem(doc: unknown): string | null {
  checkDoc ??= checker(SCHEMA as Schema);
  const first = checkDoc(doc, true);
  if (!first) return null;
  const steps = [...first.steps].reverse();
  let found = doc;
  for (const step of steps) found = (found as Record<string | number, unknown>)[step];
  const path = steps.map((s) => `/${String(s).replaceAll("~", "~0").replaceAll("/", "~1")}`).join("");
  const where = path === "" ? "at the top level" : `at ${path}`;
  return `the .mtpc does not match the schema of spec version ${SPEC_VERSION}: ${where}, ${explain(first, found)}`;
}

const made = new Map<Schema, Check>();

/** A function that checks a value against a part of the schema, made once for each part. */
function checker(schema: Schema): Check {
  let check = made.get(schema);
  if (!check) {
    check = make(schema);
    made.set(schema, check);
  }
  return check;
}

function fail(report: boolean, keyword: string, params: () => Record<string, unknown> = () => ({})): SchemaError {
  return report ? { steps: [], keyword, params: params() } : FAILED;
}

function make(schema: Schema): Check {
  if (schema === true) return () => null;
  if (schema === false) return (_, report) => fail(report, "false schema");
  const s = schema;
  const checks: Check[] = [];
  if (typeof s["$ref"] === "string") {
    const target = resolve(s["$ref"]);
    // Made when first used, since a part of the schema may refer to itself.
    let check: Check | undefined;
    checks.push((v, report) => (check ??= checker(target))(v, report));
  }
  if (s["type"] !== undefined) {
    const types = Array.isArray(s["type"]) ? (s["type"] as string[]) : [s["type"] as string];
    const tests = types.map((t) => TYPES[t] ?? (() => false));
    checks.push((v, report) => {
      for (const test of tests) if (test(v)) return null;
      return fail(report, "type", () => ({ type: types.join(",") }));
    });
  }
  if ("const" in s) {
    const allowed = s["const"];
    checks.push((v, report) => (same(v, allowed) ? null : fail(report, "const", () => ({ allowedValue: allowed }))));
  }
  if (Array.isArray(s["enum"])) {
    const allowed = s["enum"] as unknown[];
    const plain = new Set(allowed.filter((a) => a === null || typeof a !== "object"));
    checks.push((v, report) =>
      plain.has(v) || allowed.some((a) => typeof a === "object" && same(v, a))
        ? null
        : fail(report, "enum", () => ({ allowedValues: allowed })),
    );
  }
  for (const [keyword, comparison, ok] of [
    ["minimum", ">=", (v: number, l: number) => v >= l],
    ["maximum", "<=", (v: number, l: number) => v <= l],
    ["exclusiveMinimum", ">", (v: number, l: number) => v > l],
    ["exclusiveMaximum", "<", (v: number, l: number) => v < l],
  ] as const) {
    const limit = s[keyword];
    if (typeof limit === "number")
      checks.push((v, report) =>
        typeof v !== "number" || ok(v, limit) ? null : fail(report, keyword, () => ({ comparison, limit })),
      );
  }
  for (const [keyword, ok] of [
    ["minLength", (n: number, l: number) => n >= l],
    ["maxLength", (n: number, l: number) => n <= l],
  ] as const) {
    const limit = s[keyword];
    // Counted in code points, as JSON Schema counts the length of a string.
    if (typeof limit === "number")
      checks.push((v, report) =>
        typeof v !== "string" || ok([...v].length, limit) ? null : fail(report, keyword, () => ({ limit })),
      );
  }
  for (const [keyword, ok] of [
    ["minItems", (n: number, l: number) => n >= l],
    ["maxItems", (n: number, l: number) => n <= l],
  ] as const) {
    const limit = s[keyword];
    if (typeof limit === "number")
      checks.push((v, report) => (!Array.isArray(v) || ok(v.length, limit) ? null : fail(report, keyword, () => ({ limit }))));
  }
  if (s["uniqueItems"] === true)
    checks.push((v, report) => {
      if (!Array.isArray(v)) return null;
      for (let i = 1; i < v.length; i++)
        for (let j = 0; j < i; j++) if (same(v[i], v[j])) return fail(report, "uniqueItems", () => ({ i, j }));
      return null;
    });
  if (s["prefixItems"] !== undefined || s["items"] !== undefined) {
    const prefix = ((s["prefixItems"] ?? []) as Schema[]).map(checker);
    const rest = s["items"] === undefined ? null : checker(s["items"] as Schema);
    checks.push((v, report) => {
      if (!Array.isArray(v)) return null;
      for (let i = 0; i < v.length; i++) {
        const check = i < prefix.length ? prefix[i]! : rest;
        if (!check) break;
        const found = check(v[i], report);
        if (found) {
          if (report) found.steps.push(i);
          return found;
        }
      }
      return null;
    });
  }
  if (Array.isArray(s["required"])) {
    const required = s["required"] as string[];
    checks.push((v, report) => {
      if (!isType(v, "object")) return null;
      for (const key of required)
        if (!Object.hasOwn(v as object, key)) return fail(report, "required", () => ({ missingProperty: key }));
      return null;
    });
  }
  if (s["properties"] !== undefined || s["additionalProperties"] !== undefined) {
    const properties = new Map(
      Object.entries((s["properties"] ?? {}) as Record<string, Schema>).map(([k, p]) => [k, checker(p)]),
    );
    const other = s["additionalProperties"];
    const rest = other === undefined || other === false ? null : checker(other as Schema);
    const named = [...properties];
    checks.push((v, report) => {
      if (!isType(v, "object")) return null;
      // Most parts of the schema with properties and nothing about other members are the tests of
      // an if, which name one member: only the members named need a look.
      if (other === undefined) {
        for (const [key, check] of named) {
          if (!Object.hasOwn(v as object, key)) continue;
          const found = check((v as Record<string, unknown>)[key], report);
          if (found) {
            if (report) found.steps.push(key);
            return found;
          }
        }
        return null;
      }
      for (const key in v as object) {
        const check = properties.get(key) ?? rest;
        if (!check) {
          if (other === false) return fail(report, "additionalProperties", () => ({ additionalProperty: key }));
          continue;
        }
        const found = check((v as Record<string, unknown>)[key], report);
        if (found) {
          if (report) found.steps.push(key);
          return found;
        }
      }
      return null;
    });
  }
  if (Array.isArray(s["allOf"])) checks.push(...allOf(s["allOf"] as Schema[]));
  for (const keyword of ["anyOf", "oneOf"] as const) {
    if (!Array.isArray(s[keyword])) continue;
    const branches = (s[keyword] as Schema[]).map(checker);
    checks.push((v, report) => {
      let passing = 0;
      for (const branch of branches) if (!branch(v, false)) passing++;
      if (keyword === "oneOf" && passing > 1)
        return fail(report, keyword, () => ({ passingSchemas: branches.flatMap((b, i) => (b(v, false) ? [] : [i])) }));
      if (passing > 0) return null;
      if (!report) return FAILED;
      // The branch that matched the value furthest gives the deepest error, so that one is the
      // most useful. When no branch gets past the value itself, the error that none of the
      // branches matches is the one that is true.
      let deepest: SchemaError | null = null;
      for (const branch of branches) {
        const found = branch(v, true)!;
        if (!deepest || found.steps.length > deepest.steps.length) deepest = found;
      }
      return deepest && deepest.steps.length > 0 ? deepest : fail(true, keyword, () => ({ passingSchemas: null }));
    });
  }
  if (s["not"] !== undefined) {
    const banned = s["not"] as Schema;
    const test = checker(banned);
    checks.push((v, report) => (test(v, false) ? null : fail(report, "not", () => ({ schema: banned }))));
  }
  if (s["if"] !== undefined) {
    const test = checker(s["if"] as Schema);
    const then = s["then"] === undefined ? null : checker(s["then"] as Schema);
    const otherwise = s["else"] === undefined ? null : checker(s["else"] as Schema);
    checks.push((v, report) => {
      const branch = test(v, false) ? otherwise : then;
      return branch ? branch(v, report) : null;
    });
  }
  if (checks.length === 1) return checks[0]!;
  return (v, report) => {
    for (const check of checks) {
      const found = check(v, report);
      if (found) return found;
    }
    return null;
  };
}

/** Where the test of an if looks, when it only asks that one place hold one of a few plain
 * values: the first item of a list, or a member of an object that must be there. */
function placeOf(test: unknown): { at: number | string; values: unknown[] } | null {
  if (typeof test !== "object" || test === null) return null;
  const t = test as Record<string, unknown>;
  const keys = Object.keys(t).sort().join(" ");
  const plain = (s: unknown): unknown[] | null => {
    if (typeof s !== "object" || s === null) return null;
    const k = Object.keys(s).join();
    const found = k === "const" ? [(s as { const: unknown }).const] : k === "enum" ? (s as { enum: unknown[] }).enum : null;
    return found?.every((v) => v === null || typeof v !== "object") ? found : null;
  };
  const prefix = t["prefixItems"] as unknown[] | undefined;
  if (keys === "prefixItems type" && t["type"] === "array" && prefix?.length === 1) {
    const values = plain(prefix[0]);
    if (values) return { at: 0, values };
  }
  const properties = Object.entries((t["properties"] ?? {}) as object);
  const required = t["required"] as unknown[] | undefined;
  if (
    keys === "properties required type" &&
    t["type"] === "object" &&
    properties.length === 1 &&
    required?.length === 1 &&
    required[0] === properties[0]![0]
  ) {
    const values = plain(properties[0]![1]);
    if (values) return { at: properties[0]![0], values };
  }
  return null;
}

/** The checks of an allOf. The schema picks the form of an expression or an object by its first
 * item or its kind, with a long list of ifs that each test for one or a few values there. Such ifs
 * are looked up by that value, so that each expression and object runs only the ifs that apply. */
function allOf(parts: Schema[]): Check[] {
  const others: Check[] = [];
  const thens = new Map<unknown, Check[]>();
  const all: Check[] = [];
  let at: number | string | null = null;
  for (const part of parts) {
    const p = typeof part === "object" ? part : {};
    const place = Object.keys(p).sort().join(" ") === "if then" ? placeOf(p["if"]) : null;
    if (!place || (at !== null && place.at !== at)) {
      others.push(checker(part));
      continue;
    }
    at = place.at;
    const then = checker(p["then"] as Schema);
    for (const value of place.values) thens.set(value, [...(thens.get(value) ?? []), then]);
    all.push(then);
  }
  if (at === null) return others;
  const key = at;
  const run = (list: Check[] | undefined, v: unknown, report: boolean) => {
    for (const check of list ?? []) {
      const found = check(v, report);
      if (found) return found;
    }
    return null;
  };
  const lookup: Check = (v, report) => {
    if (typeof key === "number") {
      if (!Array.isArray(v)) return null;
      // A list with no items passes every test of its first item.
      return v.length === 0 ? run(all, v, report) : run(thens.get(v[0]), v, report);
    }
    if (!isType(v, "object") || !Object.hasOwn(v as object, key)) return null;
    return run(thens.get((v as Record<string, unknown>)[key]), v, report);
  };
  return [...others, lookup];
}

function resolve(ref: string): Schema {
  if (!ref.startsWith("#")) throw new Error(`the schema refers to ${ref}, outside itself`);
  let at: unknown = SCHEMA;
  for (const step of ref.slice(1).split("/").slice(1))
    at = (at as Record<string, unknown>)[step.replaceAll("~1", "/").replaceAll("~0", "~")];
  return at as Schema;
}

const TYPES: Record<string, (value: unknown) => boolean> = {
  null: (v) => v === null,
  boolean: (v) => typeof v === "boolean",
  string: (v) => typeof v === "string",
  number: (v) => typeof v === "number",
  integer: (v) => Number.isInteger(v),
  array: (v) => Array.isArray(v),
  object: (v) => typeof v === "object" && v !== null && !Array.isArray(v),
};

const isType = (value: unknown, type: string): boolean => TYPES[type]!(value);

/** Whether two JSON values are equal, as JSON Schema compares them for const, enum and uniqueItems. */
function same(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) {
    const bs = b as unknown[];
    return a.length === bs.length && a.every((x, i) => same(x, bs[i]));
  }
  const ao = a as Record<string, unknown>;
  const bo = b as Record<string, unknown>;
  const keys = Object.keys(ao);
  return keys.length === Object.keys(bo).length && keys.every((k) => Object.hasOwn(bo, k) && same(ao[k], bo[k]));
}

function shown(value: unknown): string {
  const text = JSON.stringify(value) ?? String(value);
  return text.length > 40 ? `${text.slice(0, 37)}...` : text;
}

const KINDS: Record<string, string> = {
  array: "a list",
  object: "an object",
  string: "a string",
  number: "a number",
  integer: "a whole number",
  boolean: "true or false",
  null: "null",
};

const count = (n: unknown, noun: string): string => `${String(n)} ${noun}${n === 1 ? "" : "s"}`;

const COMPARISONS: Record<string, string> = { ">=": "at least", ">": "more than", "<=": "at most", "<": "less than" };

function explain(e: SchemaError, found: unknown): string {
  const p = e.params;
  switch (e.keyword) {
    case "type":
      return `${shown(found)} must be ${String(p["type"])
        .split(",")
        .map((t) => KINDS[t] ?? t)
        .join(" or ")}`;
    case "required":
      return `the member "${String(p["missingProperty"])}" is missing`;
    case "additionalProperties":
      return `the member "${String(p["additionalProperty"])}" is not allowed here`;
    case "const":
      return `${shown(found)} must be ${shown(p["allowedValue"])}`;
    case "enum": {
      const allowed = p["allowedValues"] as unknown[];
      return allowed.length <= 8
        ? `${shown(found)} must be one of ${allowed.map(shown).join(", ")}`
        : `${shown(found)} is not one of the allowed values`;
    }
    case "minItems":
      return `the list must have at least ${count(p["limit"], "item")}`;
    case "maxItems":
      return `the list must have at most ${count(p["limit"], "item")}`;
    case "minLength":
      return `the string must have at least ${count(p["limit"], "character")}`;
    case "maxLength":
      return `the string must have at most ${count(p["limit"], "character")}`;
    case "minimum":
    case "maximum":
    case "exclusiveMinimum":
    case "exclusiveMaximum":
      return `${shown(found)} must be ${COMPARISONS[String(p["comparison"])] ?? ""} ${String(p["limit"])}`;
    case "uniqueItems":
      return `items ${String(p["j"])} and ${String(p["i"])} of the list are the same`;
    case "oneOf":
      return p["passingSchemas"]
        ? `${shown(found)} matches more than one of the forms that the schema allows here`
        : `${shown(found)} matches none of the forms that the schema allows here`;
    case "anyOf":
      return `${shown(found)} matches none of the forms that the schema allows here`;
    case "not": {
      // The schema bans a member with a not of a list of required members.
      const banned = p["schema"] as Record<string, unknown>;
      const members = banned["required"] as string[] | undefined;
      if (Object.keys(banned).join() === "required" && members && members.length > 0)
        return members.length === 1
          ? `the member "${members[0]}" must not be here`
          : `the members ${members.map((m) => `"${m}"`).join(", ")} must not all be here`;
      return `${shown(found)} has a form that the schema does not allow here`;
    }
    default:
      return `${shown(found)} is not allowed here`;
  }
}
