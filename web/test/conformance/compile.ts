// The conformance tests of the runtime compile each small source with the mtp command, so that
// each test can hold the source written for it.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import type { Doc } from "../../src/doc.ts";
import { Runtime } from "../../src/runtime.ts";

const ROOT = resolve(import.meta.dirname, "../../..");

/** The .mtpc that the mtp command writes for a source, as JSON. */
export function compile(source: string): Doc {
  const dir = mkdtempSync(join(tmpdir(), "mtp-conformance-"));
  const src = join(dir, "figure.mtp");
  const out = join(dir, "figure.mtpc");
  writeFileSync(src, source);
  execFileSync("uv", ["run", "--project", ROOT, "mtp", "compile", src, "-o", out], { cwd: ROOT, stdio: "pipe" });
  return JSON.parse(readFileSync(out, "utf8")) as Doc;
}

/** The live model of a source, and a reader of its values by name. */
export function live(source: string): [Runtime, (name: string, attr?: string) => unknown] {
  const rt = new Runtime(compile(source));
  return [rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}
