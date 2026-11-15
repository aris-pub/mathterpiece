// The check of a .mtpc against the schema of its version, docs/mtpc.schema.json, before the
// runtime runs any part of it (docs/spec/compiler-runtime.md, rule runtime-loads-mtpc).
import validate, { type SchemaError } from "virtual:mtpc-schema";
import { FORMAT_VERSION } from "./doc.ts";

/** Why a .mtpc does not match the schema, in plain words, or null when it matches. */
export function schemaProblem(doc: unknown): string | null {
  if (validate(doc)) return null;
  const errors = validate.errors ?? [];
  // The validator stops at the first place that breaks the schema, but where the schema allows
  // several forms it lists what each form finds wrong. The form that matched the .mtpc furthest
  // gives the deepest error, so that one is the most useful. When no form gets past the value
  // itself, the error that none of the forms matches is the one that is true.
  let first = errors[0];
  for (const e of errors) if (first && depth(e) > depth(first)) first = e;
  const none = errors.find(
    (e) => (e.keyword === "oneOf" || e.keyword === "anyOf") && e.instancePath === first?.instancePath,
  );
  if (none) first = none;
  const head = `the .mtpc does not match the schema of version ${FORMAT_VERSION}`;
  if (!first) return head;
  const where = first.instancePath === "" ? "at the top level" : `at ${first.instancePath}`;
  return `${head}: ${where}, ${explain(first, valueAt(doc, first.instancePath))}`;
}

const depth = (e: SchemaError): number => (e.instancePath === "" ? 0 : e.instancePath.split("/").length);

function valueAt(doc: unknown, pointer: string): unknown {
  let value = doc;
  for (const step of pointer.split("/").slice(1)) {
    const key = step.replaceAll("~1", "/").replaceAll("~0", "~");
    value = (value as Record<string, unknown> | null)?.[key];
  }
  return value;
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
      return `the list must have at least ${String(p["limit"])} items`;
    case "maxItems":
      return `the list must have at most ${String(p["limit"])} items`;
    case "minLength":
      return `the string must have at least ${String(p["limit"])} characters`;
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
    default:
      return `${shown(found)} breaks the schema rule "${e.keyword}"`;
  }
}
