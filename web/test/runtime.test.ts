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
        { kind: "state", name: "s", attrs: {}, conditions: [["=", ["read", 0, "value"], 2]] },
      ]),
    );

  it("holds within a tolerance", () => {
    expect(states().holds(1)).toBe(true);
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

describe("sorting", () => {
  const list = (...xs: unknown[]) => ["list", ...xs];

  it.each([
    ["sort-asc", [1, 2, 3]],
    ["sort-desc", [3, 2, 1]],
    ["reverse", [2, 1, 3]],
  ])("%s", (op, expected) => {
    const rt = new Runtime(doc([real("v", [op, list(3, 1, 2)])]));
    expect([0, 1, 2].map((k) => rt.eval(["part", ["read", 0, "value"], k], null, {}))).toEqual(expected);
  });

  // Circles a (r 3, x 1), b (r 1, x 2), c (r 2, x 3); v holds them by r, w reads the first one's x.
  function members(direction: string) {
    const d = doc([
      circle("a", { r: 3, x: 1 }),
      circle("b", { r: 1, x: 2 }),
      circle("c", { r: 2, x: 3 }),
      {
        kind: "value",
        name: "v",
        attrs: {
          value: ["sort-by", direction, ...[0, 1, 2].flatMap((i) => [["obj", i], ["read", i, "r"]])],
        },
      },
      real("w", ["read", ["part", ["read", 3, "value"], 0], "x"]),
    ]);
    d.depends = Object.fromEntries(
      [0, 1, 2].flatMap((i) => [
        [`${i}.r`, ["3.value", "4.value"]],
        [`${i}.x`, ["3.value", "4.value"]],
      ]),
    );
    return new Runtime(d);
  }

  it("orders members by their key", () => {
    expect(members("asc").value(4, "value")).toBe(2);
    expect(members("desc").value(4, "value")).toBe(1);
  });

  it("follows the scene", () => {
    const rt = members("asc");
    expect(rt.value(4, "value")).toBe(2);
    rt.write(2, "r", 0.5);
    expect(rt.value(4, "value")).toBe(3);
  });

  it("reverses a list of members", () => {
    const rt = members("asc");
    expect(rt.eval(["read", ["part", ["reverse", ["read", 3, "value"]], 0], "x"], null, {})).toBe(1);
  });
});

describe("and, or, not", () => {
  // k is 2 and n is 0; reading (/ 1 n) would be a division by zero.
  const rt = () => new Runtime(doc([real("k", 2), real("n", 0)]));
  const k = ["read", 0, "value"];
  const n = ["read", 1, "value"];
  const risky = [">", ["/", 1, n], 2];

  it.each([
    [["and", [">", k, 1], ["<", k, 3]], true],
    [["and", [">", k, 1], [">", k, 0], ["<", k, 2]], false],
    [["or", [">", k, 5], ["<", k, 3]], true],
    [["or", [">", k, 5], ["<", k, 0]], false],
    [["not", [">", k, 1]], false],
  ])("evaluates %j", (expr, expected) => {
    expect(rt().eval(expr, null, {})).toBe(expected);
  });

  it("stops at the first argument that decides", () => {
    expect(rt().eval(["and", ["!=", n, 0], risky], null, {})).toBe(false);
    expect(rt().eval(["or", ["=", n, 0], risky], null, {})).toBe(true);
  });
});

describe("lists of bools", () => {
  const rt = () => new Runtime(doc([real("k", 2)]));
  const k = ["read", 0, "value"];

  it("keeps bools in a list", () => {
    expect(rt().eval(["list", [">", k, 1], ["<", k, 1]], null, {})).toEqual([true, false]);
  });

  it.each([
    ["any", [false, true], true],
    ["any", [false, false], false],
    ["all", [true, true], true],
    ["all", [true, false], false],
  ])("%s of %j", (op, items, expected) => {
    expect(rt().eval([op, ["list", ...items]], null, {})).toBe(expected);
  });
});

describe("walks: loops run while drawing", () => {
  // A group g (0) of circles with r 1, 2, 3 (ids 1 to 3), and n (4) holding 0.
  const rt = () =>
    new Runtime(
      doc([
        { kind: "group", name: "g", attrs: { transform: [1, 0, 0, 0, 1, 0] }, members: [1, 2, 3] },
        circle(null, { r: 1, x: 3 }, 0),
        circle(null, { r: 2, x: 1 }, 0),
        circle(null, { r: 3, x: 2 }, 0),
        real("n", 0),
      ]),
    );
  const g = ["obj", 0];
  const r = ["read", ["arg", "p"], "r"];
  const run = (e: unknown) => rt().eval(e, null, {});

  it("maps over a group's members", () => {
    expect(run(["walk-map", g, "p", ["*", 2, r]])).toEqual([2, 4, 6]);
  });

  it("reduces", () => {
    expect(run(["walk-reduce", g, "p", "t", 0, ["+", ["arg", "t"], r]])).toBe(6);
  });

  it("sorts members by a key", () => {
    const x = ["read", ["arg", "p"], "x"];
    const sorted = ["walk-sort", "asc", g, "p", x];
    expect(run(["read", ["part", sorted, 0], "r"])).toBe(2);
    expect(run(["read", ["part", ["walk-sort", "desc", g, "p", x], 0], "r"])).toBe(1);
  });

  it("stops any and all at the first deciding item", () => {
    const risky = [">", ["/", 1, ["read", 4, "value"]], 0];
    expect(run(["walk-any", g, "p", ["or", [">", r, 0], risky]])).toBe(true);
    expect(run(["walk-all", g, "p", ["and", [">", r, 5], risky]])).toBe(false);
  });

  it("indexes a group reference", () => {
    expect(run(["read", ["part", g, 1], "r"])).toBe(2);
  });

  it("walks a list too", () => {
    expect(run(["walk-map", ["list", 1, 2], "v", ["+", ["arg", "v"], 1]])).toEqual([2, 3]);
  });
});
