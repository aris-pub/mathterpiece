import { describe, expect, it } from "vitest";
import { Runtime } from "../src/runtime.ts";
import { Complex, STDLIB, fold, mod } from "../src/stdlib.ts";
import type { Doc, Obj } from "../src/doc.ts";

// Builds a document from objects given without ids; ids are list positions.
function doc(objects: Omit<Obj, "id">[], functions: Doc["functions"] = {}): Doc {
  const objs = objects.map((o, id) => ({ ...o, id }) as Obj);
  const names = Object.fromEntries(objs.filter((o) => o.name).map((o) => [o.name, o.id]));
  return { mtp: 1, objects: objs, functions, names, depends: {} };
}

const real = (name: string, value: unknown) => ({ kind: "real", name, attrs: { value } });
const circle = (name: string | null, attrs: Record<string, unknown>, parent?: number) => ({
  kind: "circle",
  name,
  ...(parent === undefined ? {} : { parent }),
  attrs: {
    transform: [1, 0, 0, 0, 1, 0],
    x: 0,
    y: 0,
    fill: "black",
    stroke: "none",
    "stroke-width": 1,
    opacity: 1,
    "fill-opacity": 1,
    "stroke-opacity": 1,
    r: 1,
    ...attrs,
  },
});

describe("values", () => {
  it("reads plain values and expressions", () => {
    const rt = new Runtime(doc([real("k", 2), circle("c", { r: ["*", 3, ["read", 0, "value"]] })]));
    expect(rt.value(1, "r")).toBe(6);
  });

  it("caches, and drops the cache on a write", () => {
    const rt = new Runtime(doc([real("k", 2), circle("c", { r: ["read", 0, "value"] })]));
    expect(rt.value(1, "r")).toBe(2);
    rt.write(0, "value", 5);
    expect(rt.value(1, "r")).toBe(5);
  });

  it("reports cycles", () => {
    const rt = new Runtime(doc([circle("c", { x: ["read", 0, "y"], y: ["read", 0, "x"] })]));
    expect(() => rt.value(0, "x")).toThrow(/cycle/);
  });

  it("turns six numbers into a transform", () => {
    const rt = new Runtime(doc([circle("c", { transform: [2, 0, 1, 0, 2, 0] })]));
    expect(rt.value(0, "transform").apply(1, 1)).toEqual([3, 2]);
  });

  it.each([
    [["if", ["<", 1, 2], "a", "b"], "a"],
    [["cond", [false, 1], [true, 2]], 2],
    [["let", [["a", 2], ["b", ["*", ["arg", "a"], 3]]], ["+", ["arg", "a"], ["arg", "b"]]], 8],
    [["list", ["+", 1, 1], 3], [2, 3]],
    [["part", [4, 5], 1], 5],
    [["str", "n=", ["show", 7, "int"], " r=", ["show", 2, "real"]], "n=7 r=2.0"],
    [["str", ["show", 3.14159, "real", ".2f"]], "3.14"],
    [["mod", -1, 3], 2],
    [["abs", ["complex", 3, -4]], 5],
    [["call", "polar", 2, 90], [0, 2]],
    [["call", "lerp", [0, 0], [10, 20], 0.5], [5, 10]],
    [["+", ["splice", 1, 2], 3], 6],
    [["call", "max", 1, 3, 2], 3],
    [["call", "min", 1, 3, 2], 1],
    [["inf"], Infinity],
    [["-inf"], -Infinity],
    [["list", ["inf"], 1], [Infinity, 1]],
  ])("%j", (expr, value) => {
    const rt = new Runtime(doc([real("v", expr)]));
    expect(rt.value(0, "value")).toEqual(value);
  });

  it("errors while drawing", () => {
    for (const expr of [["/", 1, 0], ["mod", 1, 0], ["call", "sqrt", -1], ["call", "to-polar", [0, 0]]]) {
      const rt = new Runtime(doc([real("v", expr)]));
      expect(() => rt.value(0, "value")).toThrow();
    }
  });
});

describe("motifs and frames", () => {
  // d is a motif at (3, 0) turned 90 degrees, with a circle c at local (1, 0) whose r reads d's
  // parameter, and a real v reading c.x from outside.
  const motif = {
    kind: "motif",
    name: "d",
    motif: "dot",
    members: [1],
    attrs: { transform: [0, -1, 0, 1, 0, 0], x: 3, y: 0, opacity: 0.5 },
    params: { r: 2 },
  };
  const world = () =>
    new Runtime(
      doc([
        motif,
        circle("c", { x: 1, r: ["param", 0, "r"], opacity: 0.5 }, 0),
        real("v", ["read", 1, "y", null]),
      ]),
    );

  it("reads parameters", () => {
    expect(world().value(1, "r")).toBe(2);
  });

  it("converts positions into the reader's frame", () => {
    expect(world().value(2, "value")).toBeCloseTo(1);
  });

  it("places shapes through their parents", () => {
    const [x, y] = world().shape(1).apply(0, 0);
    expect(x).toBeCloseTo(3);
    expect(y).toBeCloseTo(1);
  });

  it("multiplies opacity down motifs", () => {
    expect(world().opacity(1)).toBeCloseTo(0.25);
  });

  it("passes objects as points in scene coordinates", () => {
    const rt = new Runtime(
      doc([motif, circle("c", { x: 1 }, 0), real("v", ["call", "dist", ["obj", 1], [3, 0]])]),
    );
    expect(rt.value(2, "value")).toBeCloseTo(1);
  });
});

describe("functions", () => {
  const fact = {
    fact: {
      params: [["n", 0]] as [string, unknown][],
      body: ["if", ["<", ["arg", "n"], 2], 1, ["*", ["arg", "n"], ["call", "fact", ["-", ["arg", "n"], 1]]]],
    },
  };

  it("calls and recurses", () => {
    const rt = new Runtime(doc([real("k", 5), real("v", ["call", "fact", ["read", 0, "value"]])], fact));
    expect(rt.value(1, "value")).toBe(120);
  });

  it("stops at the recursion limit", () => {
    const down = { down: { params: [["n", 0]] as [string, unknown][], body: ["call", "down", ["arg", "n"]] } };
    const rt = new Runtime(doc([real("v", ["call", "down", 0])], down));
    expect(() => rt.value(0, "value")).toThrow(/1000/);
  });

  it("reads object arguments", () => {
    const radius = { "radius-of": { params: [["o", null]] as [string, unknown][], body: ["read", ["arg", "o"], "r"] } };
    const rt = new Runtime(doc([circle("c", { r: 4 }), real("v", ["call", "radius-of", ["obj", 0]])], radius));
    expect(rt.value(1, "value")).toBe(4);
  });
});

describe("states", () => {
  const states = () =>
    new Runtime(
      doc([
        real("k", 2.0000000001),
        { kind: "state", name: "s", attrs: {}, conditions: [["=", ["read", 0, "value"], 2]], moves: [[0, "value", 2]] },
      ]),
    );

  it("holds within a tolerance", () => {
    expect(states().holds(1)).toBe(true);
  });

  it("knows its targets", () => {
    expect(states().targets(1)).toEqual([[0, "value", 2]]);
  });
});

describe("stdlib", () => {
  it("adds, scales and multiplies", () => {
    expect(fold("+", [[1, 2], [3, 4]])).toEqual([4, 6]);
    expect(fold("*", [2, [1, 2]])).toEqual([2, 4]);
    expect(fold("*", [new Complex(0, 1), new Complex(0, 1)])).toEqual(new Complex(-1, 0));
    expect(fold("-", [5])).toBe(-5);
  });

  it("takes mod with the sign of the divisor", () => {
    expect(mod(-1, 3)).toBe(2);
    expect(mod(1, -3)).toBe(-2);
  });

  it("is exact at right angles in degrees", () => {
    const rng = () => 0;
    expect(STDLIB.sind?.(rng, 180)).toBe(0);
    expect(STDLIB.cosd?.(rng, 90)).toBe(0);
    expect(() => STDLIB.tand?.(rng, 90)).toThrow();
  });
});
