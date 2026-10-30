/// <reference types="vite/client" />
// The cases both runtimes must agree on (tests/shared/*.mtp, compiled by `just web-examples`).
// tests/test_shared.py runs the same cases with matplotlib's evaluator; its docstring describes
// the steps.
import type { Doc } from "../src/doc.ts";
import type { Runtime } from "../src/runtime.ts";

// just web-examples copies each case's source next to its JSON, inside the web project.
const sources = import.meta.glob("./data/shared/*.mtp", { query: "?raw", import: "default", eager: true });
const docs = import.meta.glob("./data/shared/*.json", { import: "default", eager: true });

export interface Case {
  name: string;
  doc: Doc;
  page: boolean;
  steps: [kind: "expect" | "write", target: string, value: unknown][];
}

export function cases(): Case[] {
  return Object.entries(sources).map(([path, text]) => {
    const name = path.split("/").pop()!.replace(/\.mtp$/, "");
    const doc = docs[`./data/shared/${name}.json`] as Doc | undefined;
    if (!doc) throw new Error(`${name} is not compiled; run just web-examples`);
    const lines = (text as string).split("\n");
    const steps = lines.flatMap((line) => {
      const m = /^; (expect|write) (\S+) (.+)$/.exec(line);
      return m ? [[m[1] as "expect" | "write", m[2]!, JSON.parse(m[3]!)] as Case["steps"][number]] : [];
    });
    return { name, doc, page: lines.includes("; page"), steps };
  });
}

function target(doc: Doc, path: string): [number, string] {
  const m = /^([\w-]+)(?:\[(-?\d+)\])?(?:\.([\w-]+))?$/.exec(path);
  if (!m) throw new Error(`bad target ${path}`);
  let id = doc.names[m[1]!];
  if (id === undefined) throw new Error(`no object named ${m[1]}`);
  if (m[2] !== undefined) {
    const members = doc.objects[id]!.members!;
    id = members.at(Number(m[2]))!;
  }
  return [id, m[3] ?? "value"];
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
