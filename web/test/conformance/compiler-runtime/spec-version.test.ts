// Conformance tests of the rule spec-version (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { SPEC_VERSION } from "../../../src/doc.ts";
import { compile } from "../compile.ts";
import { FIGURE } from "./shared.ts";

describe("rule spec-version: the runtime and the compiler implement one version", () => {
  it("the version of a .mtpc is the version of the runtime", () => {
    expect(compile(FIGURE).mtpc).toBe(SPEC_VERSION);
  });

  it("the runtime implements version 1, the version of this draft", () => {
    expect(SPEC_VERSION).toBe(1);
  });
});
