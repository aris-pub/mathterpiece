import { describe, expect, it } from "vitest";
import { Animator } from "../src/animate.ts";
import type { Doc, Obj } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { draw } from "../src/svg.ts";

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, x: 0, y: 0, stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };

// ink (2) is a color token drawn by circle c (3); state s (4) is ink being red; readout r (5).
function world(resolve?: (css: string) => string | null) {
  const objects: Omit<Obj, "id">[] = [
    { kind: "canvas", name: "view", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [1] },
    { kind: "root", name: "s", attrs: { transform: ID }, members: [3] },
    { kind: "color", name: "ink", attrs: { value: "#1f2a44ff" } },
    { kind: "circle", name: "c", parent: 1, attrs: { ...style, r: 1, fill: ["read", 2, "value"] } },
    { kind: "state", name: "red", attrs: {}, conditions: [["color=", ["read", 2, "value"], "#ff0000ff"]], moves: [[2, "value", "#ff0000ff"]] },
    { kind: "readout", name: "r", attrs: { value: ["str", "ink is ", ["show", ["read", 2, "value"], "color"]] } },
  ];
  const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
  const rt = new Runtime(doc, Math.random, resolve);
  return { rt, anim: new Animator(rt, () => {}, () => {}) };
}

const fill = (rt: Runtime) => (draw(rt, 0).querySelector("circle") as SVGElement).style.getPropertyValue("fill");

describe("color tokens", () => {
  it("draw as a CSS variable the page can set, with the figure's default", () => {
    expect(fill(world().rt)).toBe("var(--mtp-ink, #1f2a44ff)");
  });

  it("show the color the page gave them", () => {
    const { rt } = world(() => "#e8e4d8ff");
    expect(rt.value(5, "value")).toBe("ink is #e8e4d8ff");
  });

  it("show their default outside a page", () => {
    expect(world().rt.value(5, "value")).toBe("ink is #1f2a44ff");
  });

  it("compare with strings by color", () => {
    const { rt } = world(() => "#ff0000ff");
    expect(rt.holds(4)).toBe(true);
    expect(world().rt.holds(4)).toBe(false);
  });

  it("can be written, and then draw what was written", () => {
    const { rt, anim } = world();
    anim.go(4, 0, "linear");
    expect(fill(rt)).toBe("#ff0000ff");
    expect(rt.holds(4)).toBe(true);
  });

  it("blend through CSS while animating", () => {
    const { rt, anim } = world();
    anim.go(4, 2, "linear");
    anim.tick(1);
    expect(fill(rt)).toBe("color-mix(in srgb, var(--mtp-ink, #1f2a44ff), #ff0000ff 50%)");
    anim.tick(1);
    expect(fill(rt)).toBe("#ff0000ff");
  });
});

describe("comparisons", () => {
  it.each([
    [["=", "red", "#f00"], false],
    [["=", "a", "a"], true],
    [["color=", "teal", "#008080ff"], true],
    [["color=", "#f80", "#ff8800"], true],
    [["color=", "red", "blue"], false],
    [["color!=", "red", "#f00"], false],
  ])("%j", (expr, result) => {
    const objects: Obj[] = [{ id: 0, kind: "real", name: "v", attrs: { value: expr } }];
    const rt = new Runtime({ mtp: 1, objects, functions: {}, names: {}, depends: {} });
    expect(rt.value(0, "value")).toBe(result);
  });
});

describe("mix, lighten and darken", () => {
  const value = (expr: unknown, resolve?: (css: string) => string | null) => {
    const objects: Obj[] = [
      { id: 0, kind: "color", name: "ink", attrs: { value: "#1f2a44ff" } },
      { id: 1, kind: "real", name: "v", attrs: { value: expr } },
    ];
    return new Runtime({ mtp: 1, objects, functions: {}, names: {}, depends: {} }, Math.random, resolve).value(1, "value");
  };

  it.each([
    [["call", "mix", "#000000ff", "#ffffffff", 0.5], "color-mix(in srgb, #000000ff, #ffffffff 50%)"],
    [["call", "lighten", ["read", 0, "value"], 0.3], "color-mix(in srgb, var(--mtp-ink, #1f2a44ff), white 30%)"],
    [["call", "darken", "#ffffffff", 0.25], "color-mix(in srgb, #ffffffff, black 25%)"],
  ])("%j is left to CSS", (expr, css) => {
    expect(value(expr)).toBe(css);
  });

  it("shows what the browser made of a mix", () => {
    const expr = ["str", ["show", ["call", "mix", "#000000ff", "#ffffffff", 0.5], "paint"]];
    expect(value(expr, () => "#808080ff")).toBe("#808080ff");
  });

  it("refuses amounts outside 0 to 1", () => {
    expect(() => value(["call", "mix", "red", "blue", 1.5])).toThrow(/between 0 and 1/);
  });
});
