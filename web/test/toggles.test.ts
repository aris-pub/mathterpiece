import { afterEach, describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { define, frames, type MtpModel } from "../src/elements.ts";
import { Runtime } from "../src/runtime.ts";
import { draw } from "../src/svg.ts";

define();
frames.request = () => {};

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, x: 0, y: 0, fill: "#000000ff", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };

// base (1) holds c (2); extra (3) holds d (4); the scene (0) holds both. more (5) is a self
// toggle; b (6) a scene bool, and tb (7) a toggle for it. The canvas (8) shows extra while more
// is on, and base while b holds.
function figure(): Doc {
  const objects: Omit<Obj, "id">[] = [
    { kind: "root", name: "w", attrs: { transform: ID, background: "#ffffffff" }, members: [1, 3] },
    { kind: "group", name: "base", parent: 0, attrs: { transform: ID }, members: [2] },
    { kind: "circle", name: "c", parent: 1, attrs: { ...style, r: 1 } },
    { kind: "group", name: "extra", parent: 0, attrs: { transform: ID }, members: [4] },
    { kind: "circle", name: "d", parent: 3, attrs: { ...style, r: 2 } },
    { kind: "toggle", name: "more", attrs: { label: "more", value: false }, target: null },
    { kind: "bool", name: "b", attrs: { value: true } },
    { kind: "toggle", name: "tb", attrs: { label: "b", value: false }, target: [6, "value"] },
    {
      kind: "canvas",
      name: "v",
      attrs: { "view-x": -5, "view-y": -5, "view-width": 10, "view-height": 10, transform: ID },
      shows: [1, 3],
      when: [["read", 6, "value"], ["read", 5, "value"]],
    },
  ];
  return {
    mtp: 1,
    objects: objects.map((o, id) => ({ ...o, id }) as Obj),
    functions: {},
    names: { w: 0, base: 1, c: 2, extra: 3, d: 4, more: 5, b: 6, tb: 7, v: 8 },
    depends: {},
  };
}

const radii = (svg: Element) => [...svg.querySelectorAll("circle")].map((c) => c.getAttribute("r"));

describe("a canvas's conditions", () => {
  it("leave out what they hide", () => {
    const rt = new Runtime(figure());
    expect(radii(draw(rt, 8))).toEqual(["1"]);
    rt.write(5, "value", true);
    expect(radii(draw(rt, 8))).toEqual(["1", "2"]);
    rt.write(6, "value", false);
    expect(radii(draw(rt, 8))).toEqual(["2"]);
  });

  it("still show the scene's background when the canvas lists only parts of it", () => {
    const svg = draw(new Runtime(figure()), 8);
    expect(svg.style.getPropertyValue("background-color")).toBe("#ffffffff");
  });

  it("read a toggle on a scene bool as that bool", () => {
    const rt = new Runtime(figure());
    expect(rt.value(7, "value")).toBe(true);
  });
});

describe("<mtp-toggle>", () => {
  async function page() {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="v"></mtp-canvas>
      <mtp-toggle model="m" name="more"></mtp-toggle><mtp-toggle model="m" name="tb"></mtp-toggle>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = figure();
    await new Promise((r) => setTimeout(r, 0));
    const [more, tb] = [...document.querySelectorAll("mtp-toggle input")] as HTMLInputElement[];
    return { model, more: more!, tb: tb!, canvas: () => radii(document.querySelector("mtp-canvas svg")!) };
  }

  afterEach(() => document.body.replaceChildren());

  it("is a labeled checkbox showing the toggle's value", async () => {
    const { more, tb } = await page();
    expect(more.type).toBe("checkbox");
    expect(document.querySelector("mtp-toggle")?.textContent).toContain("more");
    expect([more.checked, tb.checked]).toEqual([false, true]);
  });

  it("switches its own value, and the canvas follows", async () => {
    const { more, canvas } = await page();
    more.click();
    expect(canvas()).toEqual(["1", "2"]);
    more.click();
    expect(canvas()).toEqual(["1"]);
  });

  it("switches a scene bool", async () => {
    const { model, tb, canvas } = await page();
    tb.click();
    expect(model.runtime!.value(6, "value")).toBe(false);
    expect(canvas()).toEqual([]);
  });
});
