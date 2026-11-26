// Conformance tests of the rule runtime-serves-components (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { compile } from "../compile.ts";
import { FIGURE, page } from "./shared.ts";

describe("rule runtime-serves-components: each element draws the component that it names", () => {
  it("a readout", () => {
    page(`<mtp-readout model="m" name="r"></mtp-readout>`, compile(FIGURE));
    expect(document.querySelector("mtp-readout")!.textContent).toBe("k = 1.0");
  });

  it("a canvas draws its shapes", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, compile(FIGURE));
    expect(document.querySelector("mtp-canvas circle")).toBeTruthy();
  });

  it("an element follows the model as it changes", () => {
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, compile(FIGURE));
    const rt = model.runtime!;
    rt.write(rt.id("k"), null, 4);
    expect(document.querySelector("mtp-readout")!.textContent).toBe("k = 4.0");
  });
});
