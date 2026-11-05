// Loading the .mtpc files the compiler writes from test/fixtures/runtime/*.mtp (built by
// `just web-examples`).
import type { Doc } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";

const docs = import.meta.glob("./data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });

/** A fresh copy of the document compiled from test/fixtures/runtime/<name>.mtp. */
export function doc(name: string): Doc {
  const raw = docs[`./data/runtime/${name}.mtpc`] as string | undefined;
  if (!raw) throw new Error(`${name} is not compiled; run just web-examples`);
  return JSON.parse(raw) as Doc;
}

/** The text of the document compiled from test/fixtures/runtime/<name>.mtp, as written. */
export function source(name: string): string {
  const raw = docs[`./data/runtime/${name}.mtpc`] as string | undefined;
  if (!raw) throw new Error(`${name} is not compiled; run just web-examples`);
  return raw;
}

export function load(name: string): Runtime {
  return new Runtime(doc(name));
}
