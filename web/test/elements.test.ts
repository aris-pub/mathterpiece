import { afterEach, describe, expect, it, vi } from "vitest";
import type { Doc } from "../src/doc.ts";
import { define } from "../src/elements.ts";

define();

const doc: Doc = {
  mtp: 1,
  objects: [
    { id: 0, kind: "canvas", name: "a", attrs: { "view-x": 0, "view-y": 0, "view-width": 4, "view-height": 4, transform: [1, 0, 0, 0, 1, 0] }, shows: [2] },
    { id: 1, kind: "canvas", name: "b", attrs: { "view-x": 0, "view-y": 0, "view-width": 8, "view-height": 8, transform: [1, 0, 0, 0, 1, 0] }, shows: [2] },
    { id: 2, kind: "root", name: "s", attrs: { transform: [1, 0, 0, 0, 1, 0] }, members: [3] },
    {
      id: 3, kind: "circle", name: "c", parent: 2,
      attrs: { transform: [1, 0, 0, 0, 1, 0], x: 1, y: 1, r: 1, fill: "red", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 },
    },
  ],
  functions: {},
  names: { a: 0, b: 1, s: 2, c: 3 },
  depends: {},
};

const settle = () => new Promise((r) => setTimeout(r, 0));

afterEach(() => {
  document.body.replaceChildren();
  vi.unstubAllGlobals();
});

describe("<mtp-model> and <mtp-canvas>", () => {
  it("loads the JSON from src and draws the named canvas", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(doc))));
    document.body.innerHTML = `<mtp-canvas model="m" name="b"></mtp-canvas><mtp-model id="m" src="fig.json"></mtp-model>`;
    await settle();
    expect(fetch).toHaveBeenCalledWith("fig.json");
    const svg = document.querySelector("mtp-canvas svg");
    expect(svg?.getAttribute("viewBox")).toBe("0 -8 8 8");
    expect(svg?.querySelectorAll("circle").length).toBe(1);
  });

  it("draws the first canvas when none is named", async () => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>`;
    (document.querySelector("mtp-model") as HTMLElement & { doc: Doc }).doc = doc;
    await settle();
    expect(document.querySelector("mtp-canvas svg")?.getAttribute("viewBox")).toBe("0 -4 4 4");
  });

  it("puts each canvas anywhere in the page", async () => {
    document.body.innerHTML = `<p><mtp-canvas model="m" name="a"></mtp-canvas></p><mtp-model id="m"></mtp-model><div><mtp-canvas model="m" name="b"></mtp-canvas></div>`;
    (document.querySelector("mtp-model") as HTMLElement & { doc: Doc }).doc = doc;
    await settle();
    expect(document.querySelectorAll("mtp-canvas svg").length).toBe(2);
  });

  it("says what went wrong inside the canvas", async () => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="nope"></mtp-canvas>`;
    (document.querySelector("mtp-model") as HTMLElement & { doc: Doc }).doc = doc;
    await settle();
    expect(document.querySelector("mtp-canvas")?.textContent).toMatch(/no canvas named nope/);
  });

  it("refuses other format versions", async () => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>`;
    (document.querySelector("mtp-model") as HTMLElement & { doc: Doc }).doc = { ...doc, mtp: 2 };
    await settle();
    expect(document.querySelector("mtp-canvas")?.textContent).toMatch(/version 2/);
  });
});
