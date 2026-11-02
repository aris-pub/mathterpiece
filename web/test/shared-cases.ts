/// <reference types="vite/client" />
// The shared cases (tests/shared/*.mtp, compiled by `just web-examples`): each file's comments
// say what to write and what to expect, as "; write NAME VALUE" and "; expect NAME VALUE".
import type { Doc } from "../src/doc.ts";
import type { Runtime } from "../src/runtime.ts";

// just web-examples copies each case's source next to its JSON, inside the web project.
const sources = import.meta.glob("./data/shared/*.mtp", { query: "?raw", import: "default", eager: true });
const docs = import.meta.glob("./data/shared/*.mtpc", { query: "?raw", import: "default", eager: true });

export interface Case {
  name: string;
  doc: Doc;
  page: boolean;
  steps: [kind: "expect" | "write", target: string, value: unknown][];
}

export function cases(): Case[] {
  return Object.entries(sources).map(([path, text]) => {
    const name = path.split("/").pop()!.replace(/\.mtp$/, "");
    const raw = docs[`./data/shared/${name}.mtpc`] as string | undefined;
    if (!raw) throw new Error(`${name} is not compiled; run just web-examples`);
    const doc = JSON.parse(raw) as Doc;
    const lines = (text as string).split("\n");
    const steps = lines.flatMap((line) => {
      const m = /^; (expect|write) (\S+) (.+)$/.exec(line);
      return m ? [[m[1] as "expect" | "write", m[2]!, parseValue(m[3]!)] as Case["steps"][number]] : [];
    });
    return { name, doc, page: lines.includes("; page"), steps };
  });
}

// A value as the case writes it: JSON, except that a list's items are separated by spaces, as in
// mtp: [3 4].
function parseValue(text: string): unknown {
  return JSON.parse(/^\[.*\]$/.test(text) ? text.trim().replace(/\s+/g, ",") : text);
}

// A variable by its name alone is its value; any other object, its value attribute.
function target(doc: Doc, path: string): [number, string | null] {
  // A name may hold dots itself (d1.face), so the attribute is what follows the longest name.
  const dot = path in doc.names || /\]$/.test(path) ? -1 : path.lastIndexOf(".");
  const base = dot < 0 ? path : path.slice(0, dot);
  const attr = dot < 0 ? undefined : path.slice(dot + 1);
  const m = /^(.+?)(?:\[(-?\d+)\])?$/.exec(base);
  let id = doc.names[m![1]!];
  if (id === undefined) throw new Error(`no object named ${m![1]}`);
  if (m![2] !== undefined) id = doc.objects[id]!.members!.at(Number(m![2]))!;
  if (attr !== undefined) return [id, attr];
  return [id, doc.objects[id]!.kind === "variable" ? null : "value"];
}

// Numbers agree to rounding; a bool only matches a bool, and a string only the same string.
function agrees(got: unknown, want: unknown): boolean {
  if (typeof want === "number") return typeof got === "number" && Math.abs(got - want) <= 1e-9 * Math.max(1, Math.abs(want));
  return got === want;
}

/** Runs a case's steps; returns what disagreed. */
export function run(rt: Runtime, c: Case): string[] {
  const wrong: string[] = [];
  for (const [kind, path, value] of c.steps) {
    const [id, attr] = target(c.doc, path);
    if (kind === "write") {
      rt.write(id, attr, value);
      continue;
    }
    const got = rt.value(id, attr);
    if (!agrees(got, value)) wrong.push(`${path}: expected ${JSON.stringify(value)}, got ${JSON.stringify(got)}`);
  }
  return wrong;
}
