// Conformance tests for docs/spec/compiler-runtime.md: what the runtime must do and must never do.
// A test that today's code fails, by a "Code differs" note of the spec, is written with it.fails
// and names the bead of the note.
import { describe, expect, it } from "vitest";
import { type Doc, FORMAT_VERSION } from "../../src/doc.ts";
import { type MtpModel, define, frames } from "../../src/elements.ts";
import { Runtime } from "../../src/runtime.ts";
import { compile, live } from "./compile.ts";

define();
frames.request = () => {};

const FIGURE = `(real k 1 (>= 0) (<= 10))
(scene s (circle c (r k)))
(canvas v s)
(readout r $'k = {k:.1f}')
`;

/** A page with one model and the given elements, loaded from a .mtpc. */
function page(body: string, doc: Doc): MtpModel {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  return model;
}

const errorIn = (selector: string) => document.querySelector(`${selector} .mtp-error`)?.textContent ?? null;

describe("rule runtime-loads-mtpc: the runtime refuses what it cannot run", () => {
  it("loads a valid .mtpc", () => {
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, compile(FIGURE));
    expect(model.runtime).toBeTruthy();
    expect(errorIn("mtp-readout")).toBe(null);
  });

  it("refuses a .mtpc of another version, with both versions in the error", () => {
    const doc = { ...compile(FIGURE), mtpc: FORMAT_VERSION + 1 };
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, doc);
    expect(model.runtime).toBeFalsy();
    const error = errorIn("mtp-readout")!;
    expect(error).toContain(String(FORMAT_VERSION));
    expect(error).toContain(String(FORMAT_VERSION + 1));
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

  it.fails("refuses a corrupt .mtpc (mtp-ydd4.7.27: a corrupt file loads)", () => {
    const doc = compile(FIGURE);
    // The radius reads an object that the file does not hold.
    const c = doc.objects[doc.names["c"]!] as unknown as { attrs: Record<string, { bound: unknown[] }> };
    c.attrs["r"]!.bound = ["read", "real", 999, null, null];
    const model = page(`<mtp-readout model="m" name="r"></mtp-readout>`, doc);
    expect(model.runtime).toBeFalsy();
  });
});

describe("rule no-errors-after-loading: nothing fails once the model is loaded", () => {
  it("an operation with no value gives none", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1)) (real|none q (/ 1 x))`);
    expect(() => rt.write(rt.id("x"), null, 0)).not.toThrow();
    expect(v("q")).toBe(null);
  });

  it("a write beyond a constraint is brought into it", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1))`);
    expect(() => rt.write(rt.id("x"), null, 5)).not.toThrow();
    expect(v("x")).toBe(1);
  });

  it.fails("a deep chain of calls (mtp-ydd4.7.15: a call too deep throws RangeError)", () => {
    const [rt, v] = live(`(int n 1 (>= 0) (<= 100000))
(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))
(int d (down n))`);
    rt.write(rt.id("n"), null, 100000);
    expect(() => v("d")).not.toThrow();
  });
});

describe("rule runtime-builds-live-model: the live model is built once, then kept current", () => {
  it("gives every free variable its starting value", () => {
    const [, v] = live(`(real k 3) (point p [1 2])`);
    expect([v("k"), v("p")]).toEqual([3, [1, 2]]);
  });

  it("reads a free starting value once", () => {
    const [rt, v] = live(`(real a 1 (>= 0) (<= 10)) (real k free@(* 2 a))`);
    expect(v("k")).toBe(2);
    rt.write(rt.id("a"), null, 5);
    expect(v("k")).toBe(2);
  });

  it("computes again only what depends on what changed", () => {
    const [rt, v] = live(`(real a 1) (real b 1) (real x (* 2 a)) (real y (* 3 b))`);
    expect([v("x"), v("y")]).toEqual([2, 3]);
    const before = rt.evaluations;
    rt.write(rt.id("a"), null, 2);
    expect([v("x"), v("y")]).toEqual([4, 3]);
    expect(rt.evaluations - before).toBe(1);
  });
});

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

describe("rule runtime-adds-no-objects: the live model holds the objects of the .mtpc", () => {
  it("drawing and writing add no object", () => {
    const doc = compile(FIGURE);
    const count = doc.objects.length;
    const model = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc);
    model.runtime!.write(model.runtime!.id("k"), null, 4);
    expect(model.runtime!.doc.objects.length).toBe(count);
  });
});

describe("rule runtime-no-type-work-while-drawing: a write is brought into its constraints", () => {
  it("clamped", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 3))`);
    rt.write(rt.id("n"), null, 5);
    expect(v("n")).toBe(3);
  });

  it("rounded into an int", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 3))`);
    rt.write(rt.id("n"), null, 1.6);
    expect(v("n")).toBe(2);
  });

  it("wrapped", () => {
    const [rt, v] = live(`(real a 0 (wrap 0 360))`);
    rt.write(rt.id("a"), null, 370);
    expect(v("a")).toBeCloseTo(10, 9);
  });
});

describe("rule mtpc-only-boundary: the runtime needs only the .mtpc", () => {
  it("builds the live model from the JSON alone", () => {
    const doc = JSON.parse(JSON.stringify(compile(FIGURE))) as Doc;
    const rt = new Runtime(doc);
    expect(rt.value(rt.id("c"), "r")).toBe(1);
  });
});

describe("rule spec-version: the runtime and the compiler implement one version", () => {
  it("the version of a .mtpc is the version of the runtime", () => {
    expect(compile(FIGURE).mtpc).toBe(FORMAT_VERSION);
  });
});
