// Conformance tests of the rule mtpc-only-boundary (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { type Doc } from "../../../src/doc.ts";
import { Runtime } from "../../../src/runtime.ts";
import { compile, live } from "../compile.ts";
import { FIGURE } from "./shared.ts";

describe("rule mtpc-only-boundary: the runtime needs only the .mtpc", () => {
  it("builds the live model from the JSON alone", () => {
    const doc = JSON.parse(JSON.stringify(compile(FIGURE))) as Doc;
    const rt = new Runtime(doc);
    expect(rt.value(rt.id("c"), "r")).toBe(1);
  });
});
