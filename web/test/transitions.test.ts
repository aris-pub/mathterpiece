import { describe, expect, it } from "vitest";
import { type Spec, type ValueKind, totalDuration, valueAt, valueAtProgress } from "../src/transitions.ts";

const call = (name: string, args: unknown[]): unknown => {
  if (name === "square") return (args[0] as number) ** 2;
  if (name === "far-first") return args[2] === 0 ? args[0] : args[1];
  throw new Error(`no ${name}`);
};
const at = (spec: Spec, start: unknown, t: number, kind: ValueKind = "number") => valueAt(spec, start, t, kind, call);
const single = (s: Partial<Extract<Spec, { kind: "single" }>>): Spec => ({ kind: "single", ...s });

describe("one transition", () => {
  it("runs from where the value is to its end, over its duration", () => {
    const t = single({ to: 10, duration: 2 });
    expect([at(t, 0, 0), at(t, 0, 1), at(t, 0, 2), at(t, 0, 5)]).toEqual([0, 5, 10, 10]);
    expect(totalDuration(t)).toBe(2);
  });

  it("starts from its own from when it has one", () => {
    expect(at(single({ from: 4, to: 10, duration: 2 }), 0, 0)).toBe(4);
  });

  it("eases", () => {
    expect(at(single({ to: 8, duration: 2, ease: "ease-in" }), 0, 1)).toBeCloseTo(1);
  });

  it("takes an ease and a path given as functions", () => {
    expect(at(single({ to: 8, duration: 2, ease: ["fn", "square"] }), 0, 1)).toBeCloseTo(2);
    expect(at(single({ to: 8, duration: 2, path: ["fn", "far-first"] }), 0, 1)).toBe(8);
  });

  it("jumps at once with no duration", () => {
    expect(at(single({ to: 3, duration: 0 }), 0, 0)).toBe(3);
  });

  it("refuses to run without an end or a duration", () => {
    expect(() => at(single({ duration: 1 }), 0, 0)).toThrow(/needs an end/);
    expect(() => at(single({ to: 1 }), 0, 0)).toThrow(/needs a duration/);
  });
});

describe("default paths by kind of value", () => {
  it("moves points in a straight line", () => {
    expect(at(single({ to: [4, 8], duration: 2 }), [0, 0], 1, "point")).toEqual([2, 4]);
  });

  it("leaves mixing colors to CSS", () => {
    expect(at(single({ to: "#ffffffff", duration: 2 }), "#000000ff", 1, "color")).toBe(
      "color-mix(in srgb, #000000ff, #ffffffff 50%)",
    );
  });

  it("switches values with no in-between at the end", () => {
    const t = single({ to: true, duration: 2 });
    expect([at(t, false, 1.9, "bool"), at(t, false, 2, "bool")]).toEqual([false, true]);
  });

  it("switches when a step ease says", () => {
    const t = single({ to: true, duration: 2, ease: ["step", 0.25] });
    expect([at(t, false, 0.4, "bool"), at(t, false, 0.6, "bool")]).toEqual([false, true]);
  });

  it("crossfades text, so it reports how far the change has gone", () => {
    expect(at(single({ to: "b", duration: 2 }), "a", 0.5, "text")).toEqual({ from: "a", to: "b", progress: 0.25 });
    expect(at(single({ to: "b", duration: 2 }), "a", 2, "text")).toBe("b");
  });
});

describe("in-order", () => {
  const sweep: Spec = {
    kind: "in-order",
    defaultDuration: 1,
    parts: [single({ to: 90 }), { kind: "wait", duration: 0.5 }, single({ to: 180, duration: 2 })],
  };

  it("glues its parts end to end, each starting where the last ended", () => {
    expect(totalDuration(sweep)).toBe(3.5);
    expect([at(sweep, 0, 0.5), at(sweep, 0, 1.2), at(sweep, 0, 2.5), at(sweep, 0, 3.5)]).toEqual([45, 90, 135, 180]);
  });

  it("fills in parts without an ease", () => {
    const t: Spec = { kind: "in-order", defaultDuration: 2, defaultEase: "ease-in", parts: [single({ to: 8 })] };
    expect(at(t, 0, 1)).toBeCloseTo(1);
  });

  it("warps time across the whole sequence with its own ease", () => {
    const t: Spec = { kind: "in-order", ease: ["fn", "square"], parts: [single({ to: 1, duration: 1 }), single({ to: 2, duration: 1 })] };
    expect(at(t, 0, 1)).toBeCloseTo(0.5);
  });

  it("nests", () => {
    const t: Spec = { kind: "in-order", parts: [sweep, single({ to: 0, duration: 1 })] };
    expect(at(t, 0, 4)).toBeCloseTo(90);
  });
});

describe("scrubbed by progress, as a slider does", () => {
  it("maps the track onto the transition", () => {
    const t = single({ from: 0, to: 360 });
    expect([valueAtProgress(t, 0, 0, "number", call), valueAtProgress(t, 0, 0.25, "number", call)]).toEqual([0, 90]);
  });

  it("gives each part a share of the track by its duration, and waits stay flat", () => {
    const t: Spec = {
      kind: "in-order",
      parts: [single({ from: 0, to: 90, duration: 2 }), { kind: "wait", duration: 1 }, single({ to: 180, duration: 1 })],
    };
    const u = (p: number) => valueAtProgress(t, 0, p, "number", call);
    expect([u(0.25), u(0.6), u(0.875), u(1)]).toEqual([45, 90, 135, 180]);
  });

  it("shares the track equally among parts with no duration", () => {
    const t: Spec = { kind: "in-order", parts: [single({ from: 0, to: 10 }), single({ to: 20 })] };
    expect(valueAtProgress(t, 0, 0.75, "number", call)).toBe(15);
  });
});

describe("ints", () => {
  it("stay whole numbers all the way", () => {
    expect(at(single({ to: 9, duration: 2 }), 2, 1, "int")).toBe(6);
  });
});
