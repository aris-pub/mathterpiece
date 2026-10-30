import { describe, expect, it } from "vitest";
import { Animator, blend, parseColor } from "../src/animate.ts";
import type { Doc, Obj } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";

// k (0) is a real, t (1) a text, c (2) a circle; states 3 to 5; play is 6.
function world(): { rt: Runtime; anim: Animator; redraws: number[] } {
  const objects: Omit<Obj, "id">[] = [
    { kind: "real", name: "k", attrs: { value: 0 } },
    { kind: "text", name: "t", attrs: { value: "zero" } },
    { kind: "circle", name: "c", attrs: { fill: "#000000", opacity: 1 } },
    { kind: "state", name: "ten", attrs: {}, conditions: [], moves: [[0, "value", 10], [1, "value", "ten"], [2, "fill", "#ffffff"]] },
    { kind: "state", name: "twenty", attrs: {}, conditions: [], moves: [[0, "value", 20]] },
    { kind: "state", name: "zero", attrs: {}, conditions: [], moves: [[0, "value", 0]] },
    {
      kind: "play",
      name: "tour",
      attrs: { label: "play" },
      start: 5,
      steps: [["wait", 1], ["to", 3, 2, "linear"], ["to", 4, 1, "linear"]],
    },
  ];
  const doc: Doc = {
    mtp: 1,
    objects: objects.map((o, id) => ({ ...o, id }) as Obj),
    functions: {},
    names: {},
    depends: {},
  };
  const rt = new Runtime(doc);
  const redraws: number[] = [];
  const anim = new Animator(rt, () => redraws.push(1), () => {});
  return { rt, anim, redraws };
}

describe("going to a state", () => {
  it("jumps when there is no duration", () => {
    const { rt, anim } = world();
    anim.go(3, 0, "linear");
    expect(rt.value(0, "value")).toBe(10);
    expect(rt.value(1, "value")).toBe("ten");
  });

  it("moves numbers and colors over the duration, with easing", () => {
    const { rt, anim } = world();
    anim.go(3, 2, "linear");
    anim.tick(1);
    expect(rt.value(0, "value")).toBeCloseTo(5);
    expect(rt.value(2, "fill")).toBe("color-mix(in srgb, #000000, #ffffff 50%)");
    anim.tick(1);
    expect(rt.value(0, "value")).toBe(10);
    expect(anim.busy()).toBe(false);
  });

  it("eases", () => {
    const { rt, anim } = world();
    anim.go(4, 2, "ease-in");
    anim.tick(1);
    expect(rt.value(0, "value")).toBeCloseTo(20 * 0.125);
  });

  it("morphs text: the new text at once, and how far the change has gone", () => {
    const { rt, anim } = world();
    anim.go(3, 2, "linear");
    expect(rt.value(1, "value")).toBe("ten");
    anim.tick(0.5);
    expect(rt.morphs.get(1)).toEqual(["zero", 0.25]);
    anim.tick(1.5);
    expect(rt.morphs.size).toBe(0);
  });

  it("stops when cancelled", () => {
    const { rt, anim } = world();
    anim.go(3, 2, "linear");
    anim.tick(1);
    anim.cancel();
    anim.tick(1);
    expect(rt.value(0, "value")).toBeCloseTo(5);
  });
});

describe("play", () => {
  it("starts from its first state, then waits and moves in order", () => {
    const { rt, anim } = world();
    rt.write(0, "value", 7);
    anim.play(6);
    expect(rt.value(0, "value")).toBe(0);
    anim.tick(1);
    expect(rt.value(0, "value")).toBe(0);
    anim.tick(1);
    expect(rt.value(0, "value")).toBeCloseTo(5);
    anim.tick(1.5);
    expect(rt.value(0, "value")).toBeCloseTo(15);
    anim.tick(10);
    expect(rt.value(0, "value")).toBe(20);
    expect(anim.busy()).toBe(false);
  });

  it("starts over when played again", () => {
    const { rt, anim } = world();
    anim.play(6);
    anim.tick(2);
    anim.play(6);
    expect(rt.value(0, "value")).toBe(0);
  });

  it("redraws as it goes", () => {
    const { anim, redraws } = world();
    anim.play(6);
    anim.tick(0.5);
    expect(redraws.length).toBeGreaterThan(1);
  });
});

describe("colors", () => {
  it.each([
    ["#ff8000", [255, 128, 0, 1]],
    ["#ff800080", [255, 128, 0, 128 / 255]],
    ["#f80", [255, 136, 0, 1]],
    ["gold", [255, 215, 0, 1]],
    ["RED", [255, 0, 0, 1]],
  ])("reads %s", (text, rgba) => {
    expect(parseColor(text)).toEqual(rgba);
  });

  it("leaves mixing colors to CSS, with none as transparent", () => {
    expect(blend("none", "#ff0000", 0.5)).toBe("color-mix(in srgb, transparent, #ff0000 50%)");
    expect(blend("#000000", "#ffffff", 0.25)).toBe("color-mix(in srgb, #000000, #ffffff 25%)");
  });

  it("does not blend what it cannot read", () => {
    expect(parseColor("tab:blue")).toBeNull();
  });
});

describe("moving a whole position", () => {
  it("moves x and y together, as one point", () => {
    const objects: Obj[] = [
      { id: 0, kind: "circle", name: "c", attrs: { x: 0, y: 0, transform: [1, 0, 0, 0, 1, 0] } },
      { id: 1, kind: "state", name: "s", attrs: {}, conditions: [["=", ["read", 0, "pos", null], [4, 2]]], moves: [[0, "pos", [4, 2]]] },
    ];
    const rt = new Runtime({ mtp: 1, objects, functions: {}, names: {}, depends: {} });
    const anim = new Animator(rt, () => {}, () => {});
    expect(rt.holds(1)).toBe(false);
    anim.go(1, 2, "linear");
    anim.tick(1);
    expect([rt.value(0, "x"), rt.value(0, "y")]).toEqual([2, 1]);
    anim.tick(1);
    expect(rt.value(0, "pos")).toEqual([4, 2]);
    expect(rt.holds(1)).toBe(true);
  });
});
