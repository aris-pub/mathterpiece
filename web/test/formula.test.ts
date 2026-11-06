// Formulas (mtp-bz6h; docs/reference.md, "Formulas"): typeset math with terms, shown by a
// display. A term's content may follow an expression, a term may not exist, and its look follows
// its attributes; on-click, on-enter and on-leave listen to it.
import { beforeEach, describe, expect, it } from "vitest";
import { type MtpModel, define, frames } from "../src/elements.ts";
import { latexOf } from "../src/math.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

describe("the LaTeX typeset", () => {
  const none = () => undefined;
  const all = () => true;

  it("is the formula's own when no term changes it", () => {
    expect(latexOf("\\term{a}{x} + 1", none, all)).toBe("\\term{a}{x} + 1");
  });

  it("puts a term's content in place of what the LaTeX marks", () => {
    expect(latexOf("p = \\term{v}{}", (t) => (t === "v" ? "0.30" : undefined), all)).toBe("p = \\term{v}{0.30}");
  });

  it("leaves out a term that does not exist, with the terms inside it", () => {
    const tex = "x + \\term{b}{\\frac{\\term{c}{1}}{2}} = y";
    expect(latexOf(tex, none, (t) => t !== "b")).toBe("x +  = y");
  });

  it("goes into terms inside terms", () => {
    const tex = "\\term{b}{\\frac{\\term{c}{1}}{2}}";
    expect(latexOf(tex, (t) => (t === "c" ? "n" : undefined), all)).toBe("\\term{b}{\\frac{\\term{c}{n}}{2}}");
  });

  it("keeps braces and escaped braces inside a term", () => {
    expect(latexOf("\\term{a}{\\{x^{2}\\}}", none, all)).toBe("\\term{a}{\\{x^{2}\\}}");
  });
});

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};
function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string): Runtime {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("formula");
  return model.runtime!;
}

const term = (name: string, at = document.body) => at.querySelector(`.mtp-term-${name}`) as SVGGElement | null;

beforeEach(() => {
  queued = [];
  clock = 0;
});

describe("a display", () => {
  it("typesets its formula, each term marked with its id", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    const display = document.querySelector("mtp-display")!;
    expect(display.querySelector("mjx-container svg")).not.toBeNull();
    expect(term("a")!.getAttribute("data-mtp-id")).toBe(String(rt.id("f.a")));
  });

  it("is a block, or inline inside a paragraph", () => {
    page(`<mtp-display model="m" name="d"></mtp-display><p>so <mtp-display model="m" name="di"></mtp-display></p>`);
    const [block, inline] = [...document.querySelectorAll("mtp-display")] as HTMLElement[];
    expect(block!.style.display).toBe("block");
    expect(block!.querySelector("mjx-container")!.getAttribute("display")).toBe("true");
    expect(inline!.style.display).toBe("inline");
    expect(inline!.querySelector("mjx-container")!.getAttribute("display")).toBeNull();
  });

  it("shows a term's content, and typesets it again when it changes", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    const display = document.querySelector("mtp-display") as HTMLElement & { latex: string };
    expect(display.latex).toContain("\\term{v}{0.30}");
    rt.write(rt.id("q"), null, 0.5);
    pass(0.5);
    expect(display.latex).toContain("\\term{v}{0.50}");
    expect(term("v")).not.toBeNull();
  });

  it("leaves out a term that does not exist", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    expect(term("b")).toBeNull();
    rt.write(rt.id("lit"), null, true);
    pass(0.5);
    expect(term("b")).not.toBeNull();
    expect(term("c")).not.toBeNull();
  });

  it("colors a term and sets its opacity, following its attributes", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    expect(term("a")!.style.color).toBe("#008080ff");
    expect(term("a")!.style.opacity).toBe("0.4");
    rt.write(rt.id("shown"), null, "a");
    expect(term("a")!.style.opacity).toBe("1");
  });

  it("draws a box behind a term and an outline around it", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    const box = () => term("a")!.querySelector(":scope > rect.mtp-term-box") as SVGRectElement;
    expect(box().getAttribute("fill")).toBe("none");
    rt.write(rt.id("f.a"), "background", "#ffe08aff");
    expect(box().getAttribute("fill")).toBe("#ffe08aff");
    rt.write(rt.id("lit"), null, true);
    pass(0.5);
    const outline = term("c")!.querySelector(":scope > rect.mtp-term-box") as SVGRectElement;
    expect(outline.getAttribute("stroke")).toBe("#ff0000ff");
  });

  it("plays a term's on-click", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    term("a")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    pass(0.2);
    expect(rt.value(rt.id("shown"), null)).toBe("a");
  });

  it("plays a term's on-enter and on-leave", () => {
    const rt = page(`<mtp-display model="m" name="d"></mtp-display>`);
    term("a")!.dispatchEvent(new PointerEvent("pointerenter"));
    pass(0.2);
    expect(rt.value(rt.id("f.a"), "background")).toBe(rt.value(rt.id("wash"), null));
    term("a")!.dispatchEvent(new PointerEvent("pointerleave"));
    pass(0.2);
    expect(rt.value(rt.id("f.a"), "background")).toBeNull();
  });

  it("shows a pointer over a term that takes a click", () => {
    page(`<mtp-display model="m" name="d"></mtp-display>`);
    expect(term("a")!.style.cursor).toBe("pointer");
    expect(term("v")!.style.cursor).toBe("");
  });
});
