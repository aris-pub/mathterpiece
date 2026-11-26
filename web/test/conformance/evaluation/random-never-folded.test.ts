// Conformance tests of the rule random-never-folded (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { compile } from "../compile.ts";
import { RANDOM } from "./shared.ts";

describe("rule random-never-folded: a random value is known only while drawing", () => {
  it("is not written as a value in the .mtpc", () => {
    const doc = compile(RANDOM);
    const a = doc.objects[doc.names["a"]!]! as { value: { bound?: unknown } };
    expect(a.value.bound).toBeDefined();
  });
});
