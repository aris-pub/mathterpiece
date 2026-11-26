// Conformance tests of the rule jumper-signatures (docs/spec/controls.md): the .mtpc of each
// jumper, as docs/mtpc.md writes it, loads, and one that lacks an argument without a default does
// not.
import { describe, expect, it } from "vitest";
import type { Doc } from "../../../src/doc.ts";
import { schemaProblem } from "../../../src/schema.ts";
import { ANGLE, REAL_0_1, bool, control, maybe, mtpc, none, num, page, str, variable } from "./shared.ts";

const VARS = [
  variable("k", REAL_0_1, 0.5),
  variable("theta", ANGLE, 0),
  variable("word", "string", "a"),
  variable("curves", { list: "string" }, []),
  variable("b", "bool", false),
  variable("hi", REAL_0_1, 0.8),
];

const JUMPERS: Record<string, object> = {
  slider: control("slider", "c", { target: [0, null], attrs: { label: str(""), from: num(0), to: num(1), step: maybe(0.1), ticks: none() } }),
  "range-slider": control("range-slider", "c", {
    low: [0, null],
    high: [5, null],
    attrs: { label: str(""), from: num(0), to: num(1), step: none(), ticks: maybe(0.5) },
  }),
  dial: control("dial", "c", { target: [1, null], attrs: { label: str(""), step: maybe(15), ticks: none() } }),
  "number-field": control("number-field", "c", { target: [0, null], attrs: { label: str(""), step: num(1), buttons: bool(true), typing: bool(false) } }),
  "text-field": control("text-field", "c", { target: [2, null], attrs: { label: str("") } }),
  toggle: control("toggle", "c", {
    target: [4, null],
    animation: null,
    attrs: { label: str(""), value: { type: "bool", bound: ["read", "bool", 4, null, null], deps: [[4, null]] } },
  }),
  select: control("select", "c", {
    target: [2, null],
    as: "buttons",
    options: [{ value: str("a"), label: str("\\frac{a+b}{2}"), "label-tex": true }, { value: str("b") }],
    attrs: { label: str("") },
  }),
  "multi-select": control("multi-select", "c", {
    target: [3, null],
    as: "checkbox",
    options: [{ value: str("a") }, { value: str("b"), label: str("bee") }],
    attrs: { label: str("") },
  }),
};

const problem = (doc: Doc) => schemaProblem(structuredClone(doc));

describe("rule jumper-signatures: each jumper has the arguments of its signature", () => {
  for (const [kind, obj] of Object.entries(JUMPERS)) {
    it(`the .mtpc of a ${kind} matches the schema and loads`, () => {
      const doc = mtpc(...VARS, obj);
      expect(problem(doc)).toBe(null);
      const model = page(`<mtp-${kind} model="m" name="c"></mtp-${kind}>`, doc);
      expect(model.error).toBe(null);
      expect(document.querySelector(`mtp-${kind} .mtp-error`)).toBe(null);
    });
  }

  const without = (kind: string, path: string[]) => {
    const obj = structuredClone(JUMPERS[kind]) as Record<string, Record<string, unknown>>;
    if (path.length === 1) delete obj[path[0]!];
    else delete obj[path[0]!]![path[1]!];
    return mtpc(...VARS, obj);
  };

  it("a slider has a target, a from and a to", () => {
    expect(problem(without("slider", ["target"]))).not.toBe(null);
    expect(problem(without("slider", ["attrs", "from"]))).not.toBe(null);
    expect(problem(without("slider", ["attrs", "to"]))).not.toBe(null);
  });

  it("a range slider has a low and a high", () => {
    expect(problem(without("range-slider", ["low"]))).not.toBe(null);
    expect(problem(without("range-slider", ["high"]))).not.toBe(null);
  });

  it("a number field has its step, buttons and typing", () => {
    for (const attr of ["step", "buttons", "typing"]) expect(problem(without("number-field", ["attrs", attr]))).not.toBe(null);
  });

  it("a select has at least one option, and its kind is one of its three", () => {
    const empty = structuredClone(JUMPERS["select"]) as Record<string, unknown>;
    empty["options"] = [];
    expect(problem(mtpc(...VARS, empty))).not.toBe(null);
    const checkbox = structuredClone(JUMPERS["select"]) as Record<string, unknown>;
    checkbox["as"] = "checkbox";
    expect(problem(mtpc(...VARS, checkbox))).not.toBe(null);
    const radio = structuredClone(JUMPERS["multi-select"]) as Record<string, unknown>;
    radio["as"] = "radio";
    expect(problem(mtpc(...VARS, radio))).not.toBe(null);
  });

  it("a slider in today's form, which plays an animation, still loads", () => {
    const transition = { kind: "transition", type: "transition", access: "scene", name: null, from: num(0), to: num(1), duration: null, ease: null, path: null };
    const animation = { kind: "animation", type: "animation", access: "scene", name: null, steps: ["move", [0, null], 1, 1, "linear"] };
    const old = control("slider", "c", {
      animation: 2,
      attrs: { label: str("k"), position: free01(0), stops: { type: { refine: "int", constraints: [[">=", 2]] }, free: 5 } },
    });
    const doc = mtpc(variable("k", REAL_0_1, 0), transition, animation, old);
    expect(problem(doc)).toBe(null);
    page(`<mtp-slider model="m" name="c"></mtp-slider>`, doc);
    expect((document.querySelector("mtp-slider input") as HTMLInputElement).type).toBe("range");
  });
});

function free01(v: number) {
  return { type: REAL_0_1, free: v };
}
