import { afterEach, describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { define, frames, type MtpModel } from "../src/elements.ts";

define();
frames.request = () => {};

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, fill: "#000000ff", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };
const grow = (to: number) => ["pair", [[0, "value"]], "number", ["transition", { to, duration: 0 }]];

// k (0) is a real. The scene (2) holds group g (3) with circles a (4) and b (5), and circle c (6).
function figure(listeners: Omit<Obj, "id" | "name" | "attrs">[]): Doc {
  const objects: Omit<Obj, "id">[] = [
    { kind: "real", name: "k", attrs: { value: 0 } },
    { kind: "canvas", name: "v", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [2] },
    { kind: "root", name: "s", attrs: { transform: ID }, members: [3, 6] },
    { kind: "group", name: "g", parent: 2, attrs: { transform: ID }, members: [4, 5] },
    { kind: "circle", name: "a", parent: 3, attrs: { ...style, x: 1, y: 1, r: 0.5 } },
    { kind: "circle", name: "b", parent: 3, attrs: { ...style, x: 3, y: 1, r: 0.5 } },
    { kind: "circle", name: "c", parent: 2, attrs: { ...style, x: 5, y: 1, r: 0.5 } },
    { kind: "animation", name: "to-1", attrs: {}, body: grow(1) },
    { kind: "animation", name: "to-2", attrs: {}, body: grow(2) },
    ...listeners.map((l) => ({ name: null, attrs: {}, ...l })),
  ];
  return { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
}

const on = (node: number, animation: number, when: unknown = null) => ({ kind: "on-click", node, animation, when });

async function page(doc: Doc) {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  await new Promise((r) => setTimeout(r, 0));
  const shape = (id: number) => document.querySelector(`mtp-canvas [data-mtp-id="${id}"]`) as SVGElement;
  const send = (type: string, el: Element) => el.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 1 }));
  const click = (down: number, up = down) => {
    send("pointerdown", shape(down));
    send("pointerup", shape(up));
  };
  return { rt: model.runtime!, shape, click, k: () => model.runtime!.value(0, "value") };
}

afterEach(() => document.body.replaceChildren());

describe("on-click", () => {
  it("runs its animation when the shape is pressed and released", async () => {
    const { click, k } = await page(figure([on(6, 7)]));
    click(6);
    expect(k()).toBe(1);
  });

  it("does nothing when the release is on another shape", async () => {
    const { click, k } = await page(figure([on(6, 7)]));
    click(6, 4);
    expect(k()).toBe(0);
  });

  it("goes up the tree to the nearest listener", async () => {
    const { click, k } = await page(figure([on(3, 7), on(5, 8)]));
    click(4);
    expect(k()).toBe(1);
    click(5);
    expect(k()).toBe(2);
  });

  it("is detached while its when does not hold", async () => {
    const { click, k } = await page(figure([on(6, 8, [">", ["read", 0, "value"], 0])]));
    click(6);
    expect(k()).toBe(0);
  });

  it("shows a pointer over what can be clicked", async () => {
    const { shape } = await page(figure([on(3, 7)]));
    expect(shape(4).style.cursor).toBe("pointer");
    expect(shape(6).style.cursor).toBe("");
  });
});
