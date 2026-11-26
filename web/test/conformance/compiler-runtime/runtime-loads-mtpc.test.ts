// Conformance tests of the rule runtime-loads-mtpc (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { type Doc, SPEC_VERSION } from "../../../src/doc.ts";
import { type MtpModel } from "../../../src/elements.ts";
import { compile } from "../compile.ts";
import { FIGURE, page, errorIn } from "./shared.ts";

describe("rule runtime-loads-mtpc: the runtime refuses what it cannot run", () => {
  it("loads a valid .mtpc", () => {
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, compile(FIGURE));
    expect(model.runtime).toBeTruthy();
    expect(errorIn("mtp-readout")).toBe(null);
  });

  it("refuses a .mtpc of another version, with both versions in the error", () => {
    const doc = { ...compile(FIGURE), mtpc: SPEC_VERSION + 1 };
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, doc);
    expect(model.runtime).toBeFalsy();
    const error = errorIn("mtp-readout")!;
    expect(error).toContain(String(SPEC_VERSION));
    expect(error).toContain(String(SPEC_VERSION + 1));
  });

  /** Loads a .mtpc that does not match the schema, and gives the error that each component shows. */
  function refused(doc: Record<string, unknown>): string[] {
    let model: MtpModel | null = null;
    expect(() => {
      model = page(
        `<mtp-canvas model="m" name="v"></mtp-canvas><mtp-readout model="m" name="r"></mtp-readout>`,
        doc as unknown as Doc,
      );
    }).not.toThrow();
    expect(model!.runtime).toBeFalsy();
    expect(document.querySelector("mtp-canvas circle")).toBe(null);
    expect(document.querySelector("mtp-readout")!.textContent).not.toContain("k =");
    const errors = [errorIn("mtp-canvas")!, errorIn("mtp-readout")!];
    for (const error of errors) expect(error).toContain("does not match the schema");
    return errors;
  }

  it("refuses a .mtpc with a member of the wrong kind", () => {
    const doc = compile(FIGURE) as unknown as Record<string, unknown>;
    doc["objects"] = "not a list";
    for (const error of refused(doc)) expect(error).toContain("/objects");
  });

  it("refuses a .mtpc with a required member missing, and names the member", () => {
    const doc = compile(FIGURE) as unknown as Record<string, unknown>;
    delete doc["names"];
    for (const error of refused(doc)) expect(error).toContain(`"names"`);
  });

  it("refuses a .mtpc with an unknown kind of expression, and gives where it is", () => {
    const doc = compile(FIGURE);
    const at = doc.names["c"]!;
    const c = doc.objects[at] as unknown as { attrs: Record<string, { bound: unknown[] }> };
    c.attrs["r"]!.bound[0] = "no-such-kind";
    for (const error of refused(doc as unknown as Record<string, unknown>)) {
      expect(error).toContain(`/objects/${at}/attrs/r/bound/0`);
      expect(error).toContain("no-such-kind");
    }
  });

  it("refuses a .mtpc with a listener in the older form, which has no in", () => {
    const doc = compile(`(real k 1 (>= 0) (<= 10))
(scene s (circle c (r k)))
(canvas v s (on-click c (animation (move k (to (+ k 1)) (duration 0)))))
(readout r f'k = {k:.1f}')
`);
    const at = doc.objects.findIndex((o) => o.kind === "on-click");
    const listener = doc.objects[at] as unknown as Record<string, unknown>;
    expect(listener["in"]).toBeTruthy();
    delete listener["in"];
    for (const error of refused(doc as unknown as Record<string, unknown>)) {
      expect(error).toContain(`/objects/${at}`);
      expect(error).toContain(`the member "in" is missing`);
    }
  });

  it.fails("refuses a corrupt .mtpc (mtp-ydd4.7.27: a corrupt file loads)", () => {
    const doc = compile(FIGURE);
    // The radius reads an object that the file does not hold.
    const c = doc.objects[doc.names["c"]!] as unknown as { attrs: Record<string, { bound: unknown[] }> };
    c.attrs["r"]!.bound = ["read", "real", 999, null, null];
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, doc);
    expect(model.runtime).toBeFalsy();
  });
});
