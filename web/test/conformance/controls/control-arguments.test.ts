// Conformance tests of the rule control-arguments (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import {
  ANGLE,
  REAL_0_1,
  bool,
  control,
  guard,
  input,
  mtpc,
  none,
  num,
  page,
  place,
  press,
  str,
  typeInto,
  valueOf,
  variable,
} from "./shared.ts";

// The variables that the controls below write, at these positions.
const VARS = [
  variable("k", REAL_0_1, 0.5),
  variable("theta", ANGLE, 0),
  variable("word", "string", "a"),
  variable("curves", { list: "string" }, []),
  variable("b", "bool", false),
  variable("hi", REAL_0_1, 0.8),
];
const [K, THETA, WORD, CURVES, B, HI] = [0, 1, 2, 3, 4, 5];

// Each new kind of control, with the given label and further keys, and the input that the reader
// uses first.
const KINDS: [string, (label: string, more?: object) => object, string][] = [
  [
    "slider",
    (label, more = {}) =>
      control("slider", "c", { target: [K, null], attrs: { label: str(label), from: num(0), to: num(1), step: none(), ticks: none() }, ...more }),
    "thumb",
  ],
  [
    "range-slider",
    (label, more = {}) =>
      control("range-slider", "c", {
        low: [K, null],
        high: [HI, null],
        attrs: { label: str(label), from: num(0), to: num(1), step: none(), ticks: none() },
        ...more,
      }),
    "low",
  ],
  ["dial", (label, more = {}) => control("dial", "c", { target: [THETA, null], attrs: { label: str(label), step: none(), ticks: none() }, ...more }), "thumb"],
  [
    "number-field",
    (label, more = {}) =>
      control("number-field", "c", { target: [K, null], attrs: { label: str(label), step: num(0.1), buttons: bool(true), typing: bool(true) }, ...more }),
    "box",
  ],
  ["text-field", (label, more = {}) => control("text-field", "c", { target: [WORD, null], attrs: { label: str(label) }, ...more }), "box"],
  [
    "toggle",
    (label, more = {}) =>
      control("toggle", "c", {
        target: [B, null],
        animation: null,
        attrs: { label: str(label), value: { type: "bool", bound: ["read", "bool", B, null, null], deps: [[B, null]] } },
        ...more,
      }),
    "box",
  ],
  [
    "select",
    (label, more = {}) =>
      control("select", "c", { target: [WORD, null], as: "menu", options: [{ value: str("a") }, { value: str("b") }], attrs: { label: str(label) }, ...more }),
    "menu",
  ],
  [
    "multi-select",
    (label, more = {}) =>
      control("multi-select", "c", { target: [CURVES, null], as: "menu", options: [{ value: str("a") }], attrs: { label: str(label) }, ...more }),
    "menu",
  ],
];

const disabled = (el: HTMLElement) => (el as HTMLInputElement).disabled === true || el.getAttribute("aria-disabled") === "true";

describe("rule control-arguments: every control takes a label, active, in, priority, doc and conditions", () => {
  for (const [kind, make, first] of KINDS) {
    const tag = `mtp-${kind}`;

    it(`a ${kind} shows its label`, () => {
      page(`<${tag} model="m" name="c"></${tag}>`, mtpc(...VARS, make("the label")));
      expect(document.querySelector(tag)!.textContent).toContain("the label");
      expect(document.querySelector(`${tag} .mtp-error`)).toBe(null);
    });

    it(`a ${kind} typesets a label given as a TeX string`, () => {
      page(`<${tag} model="m" name="c"></${tag}>`, mtpc(...VARS, make("x^2", { "label-tex": true })));
      expect(document.querySelector(`${tag} [role="img"][aria-label="x^2"]`)).toBeTruthy();
    });

    it(`a ${kind} whose active is false takes no input`, () => {
      page(`<${tag} model="m" name="c"></${tag}>`, mtpc(...VARS, make("l", { active: bool(false) })));
      expect(document.querySelector(tag)!.hasAttribute("data-mtp-inactive")).toBe(true);
      expect(disabled(input(tag, first))).toBe(true);
    });

    it(`a ${kind} that belongs only to a quiet view is folded away`, () => {
      const transform = { type: "transform", free: [1, 0, 0, 1, 0, 0] };
      const scene = {
        kind: "scene",
        type: "scene",
        access: "scene",
        name: "s",
        members: [],
        attrs: { background: { type: { union: ["color", "none"] }, free: null }, transform },
      };
      const canvas = {
        kind: "canvas",
        type: { component: "canvas" },
        access: "page",
        name: "v",
        shows: [VARS.length + 1],
        transition: null,
        fit: true,
        attrs: { pan: bool(true), zoom: bool(true), "zoom-max": num(10), "zoom-min": num(1), transform },
      };
      const live = { kind: "on-live", type: { component: "on-live" }, access: "page", name: null, view: VARS.length + 2, animation: null, conditions: [], active: null };
      page(`<${tag} model="m" name="c"></${tag}>`, mtpc(...VARS, make("l", { in: [VARS.length + 2] }), scene, canvas, live));
      expect(document.querySelector(tag)!.hasAttribute("data-mtp-folded")).toBe(true);
    });
  }

  it("a slider's guard clamps what it writes", () => {
    const slider = control("slider", "c", {
      target: [K, null],
      conditions: [guard([K, null], "<=", 0.6)],
      attrs: { label: str(""), from: num(0), to: num(1), step: none(), ticks: none() },
    });
    const model = page(`<mtp-slider model="m" name="c"></mtp-slider>`, mtpc(...VARS, slider));
    const track = input("mtp-slider", "track");
    place(track, 0, 0, 116, 24);
    press(track, 98);
    expect(valueOf(model, "k")).toBe(0.6);
  });

  it("a number field's guard clamps a typed value", () => {
    const field = control("number-field", "c", {
      target: [K, null],
      conditions: [guard([K, null], ">=", 0.25)],
      attrs: { label: str(""), step: num(0.1), buttons: bool(true), typing: bool(true) },
    });
    const model = page(`<mtp-number-field model="m" name="c"></mtp-number-field>`, mtpc(...VARS, field));
    const box = input("mtp-number-field", "box") as HTMLInputElement;
    typeInto(box, "0.1");
    box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(valueOf(model, "k")).toBe(0.25);
  });
});
