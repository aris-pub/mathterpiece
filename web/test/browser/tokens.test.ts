import { afterEach, describe, expect, it } from "vitest";
import type { Doc, Obj } from "../../src/doc.ts";
import { define, frames, type MtpModel } from "../../src/elements.ts";

define();
frames.request = () => {};

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, x: 0, y: 0, stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };

// ink (2) is a color token; circle c (3) is filled with it; d (4) with a mix of ink and white.
const objects: Omit<Obj, "id">[] = [
  { kind: "canvas", name: "view", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [1] },
  { kind: "root", name: "s", attrs: { transform: ID }, members: [3, 4] },
  { kind: "color", name: "ink", attrs: { value: "#1f2a44ff" } },
  { kind: "circle", name: "c", parent: 1, attrs: { ...style, r: 1, fill: ["read", 2, "value"] } },
  { kind: "circle", name: "d", parent: 1, attrs: { ...style, r: 1, fill: ["call", "lighten", ["read", 2, "value"], 0.5] } },
  { kind: "readout", name: "r", attrs: { value: ["str", ["show", ["read", 2, "value"], "color"]] } },
  { kind: "readout", name: "lighter", attrs: { value: ["str", ["show", ["call", "lighten", ["read", 2, "value"], 0.5], "paint"]] } },
  { kind: "state", name: "red", attrs: {}, conditions: [["color=", ["read", 2, "value"], "#ff0000ff"]], moves: [[2, "value", "#ff0000ff"]] },
];
const doc: Doc = {
  mtp: 1,
  objects: objects.map((o, id) => ({ ...o, id }) as Obj),
  functions: {},
  names: { ink: 2, c: 3, d: 4, r: 5, lighter: 6, red: 7 },
  depends: {},
};

async function page(css = "") {
  document.head.querySelector("#page-css")?.remove();
  const sheet = document.createElement("style");
  sheet.id = "page-css";
  sheet.textContent = css;
  document.head.append(sheet);
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas><p>ink is <mtp-readout model="m" name="r"></mtp-readout></p>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  await new Promise((r) => setTimeout(r, 0));
  const drawn = (id: number) => getComputedStyle(document.querySelector(`[data-mtp-id="${id}"]`)!).fill;
  const readout = () => document.querySelector("mtp-readout")!.textContent;
  return { model, drawn, readout };
}

afterEach(() => {
  document.body.replaceChildren();
  document.documentElement.className = "";
});

describe("color tokens in a real page", () => {
  it("use the figure's default when the page says nothing", async () => {
    const { drawn, readout } = await page();
    expect(drawn(3)).toBe("rgb(31, 42, 68)");
    expect(readout()).toBe("#1f2a44ff");
  });

  it("follow the page's CSS, set on any ancestor", async () => {
    const { drawn, readout } = await page(":root { --mtp-ink: #e8e4d8; }");
    expect(drawn(3)).toBe("rgb(232, 228, 216)");
    expect(readout()).toBe("#e8e4d8ff");
  });

  it("follow the page's own variables", async () => {
    const { drawn } = await page(":root { --fg: tomato; } mtp-canvas, mtp-model { --mtp-ink: var(--fg); }");
    expect(drawn(3)).toBe("rgb(255, 99, 71)");
  });

  it("follow a theme switched by a class on the page's root", async () => {
    const { readout } = await page(":root.dark { --mtp-ink: #e8e4d8; }");
    expect(readout()).toBe("#1f2a44ff");
    document.documentElement.className = "dark";
    await new Promise((r) => setTimeout(r, 0));
    expect(readout()).toBe("#e8e4d8ff");
  });

  it("are mixed by CSS while animating", async () => {
    const { model, drawn } = await page(":root { --mtp-ink: #000000; }");
    model.animator!.go(7, 2, "linear");
    model.animator!.tick(1);
    expect(drawn(3)).toBe("color(srgb 0.5 0 0)");
  });

  it("are mixed by CSS, and a readout shows the result", async () => {
    const { drawn } = await page(":root { --mtp-ink: #000000; }");
    expect(drawn(4)).toBe("color(srgb 0.5 0.5 0.5)");
    document.body.insertAdjacentHTML("beforeend", `<mtp-readout model="m" name="lighter"></mtp-readout>`);
    expect(document.querySelectorAll("mtp-readout")[1]!.textContent).toBe("#808080ff");
  });

  it("compare with strings by their color on the page", async () => {
    const { model } = await page(":root { --mtp-ink: red; }");
    expect(model.runtime!.holds(7)).toBe(true);
  });
});
