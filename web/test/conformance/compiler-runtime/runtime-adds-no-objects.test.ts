// Conformance tests of the rule runtime-adds-no-objects (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { compile, live } from "../compile.ts";
import { FIGURE, page } from "./shared.ts";

describe("rule runtime-adds-no-objects: the live model holds the objects of the .mtpc", () => {
  it("drawing and writing add no object", () => {
    const doc = compile(FIGURE);
    const count = doc.objects.length;
    const model = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc);
    model.runtime!.write(model.runtime!.id("k"), null, 4);
    expect(model.runtime!.doc.objects.length).toBe(count);
  });
});
