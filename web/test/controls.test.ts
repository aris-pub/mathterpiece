import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { define, frames, type MtpModel } from "../src/elements.ts";

define();
// Time moves only when a test says so.
frames.request = () => {};

function example(name: string): Doc {
  return JSON.parse(readFileSync(join(process.cwd(), "test", "data", "examples", `${name}.json`), "utf8")) as Doc;
}

// Puts the given HTML in the page, gives model "m" the example, and returns its runtime.
async function page(name: string, html: string) {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>${html}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  const doc = example(name);
  model.doc = doc;
  await new Promise((r) => setTimeout(r, 0));
  const rt = model.runtime!;
  const read = (path: string) => {
    const [obj, attr] = path.split(".") as [string, string];
    return rt.value(doc.names[obj]!, attr);
  };
  return { model, rt, read, anim: model.animator! };
}

const text = (name: string) =>
  [...document.querySelectorAll("mtp-canvas text")].find((t) => t.textContent?.includes(name))?.textContent;

afterEach(() => document.body.replaceChildren());

describe("<mtp-slider>", () => {
  it("scrubs its animation: the knob's place is the progress", async () => {
    const { read } = await page("golden-tour", `<mtp-slider model="m" name="angle"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(document.querySelector("mtp-slider")?.textContent).toContain("angle");
    expect([input.min, input.max, input.step]).toEqual(["0", "1", "any"]);
    input.value = "0.4";
    input.dispatchEvent(new Event("input"));
    expect(read("sunflower.angle")).toBeCloseTo(120);
    expect(text("°")).toBe("120.0°");
  });

  it("keeps an int target whole", async () => {
    const { read } = await page("interactive", `<mtp-slider model="m" name="multiplier"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "0.1";
    input.dispatchEvent(new Event("input"));
    expect(read("table.m")).toBe(6);
  });

  it("follows its one target when something else moves it", async () => {
    const { anim } = await page(
      "golden-tour",
      `<mtp-slider model="m" name="angle"></mtp-slider><mtp-play model="m" name="tour"></mtp-play>`,
    );
    const steps = [...document.querySelectorAll("mtp-play button")] as HTMLButtonElement[];
    steps[3]!.click();
    anim.tick(5);
    expect(Number((document.querySelector("mtp-slider input") as HTMLInputElement).value)).toBeCloseTo(0.64, 3);
  });
});

describe("<mtp-button>", () => {
  it("sets off its animation", async () => {
    const { read } = await page(
      "interactive",
      `<mtp-slider model="m" name="multiplier"></mtp-slider><mtp-button model="m" name="reset"></mtp-button>`,
    );
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "0.5";
    input.dispatchEvent(new Event("input"));
    expect(read("table.m")).toBe(21);
    const button = document.querySelector("mtp-button button") as HTMLButtonElement;
    expect(button.textContent).toBe("back to 2");
    button.click();
    expect(read("table.m")).toBe(2);
  });
});

describe("<mtp-play>", () => {
  async function tour() {
    const w = await page("golden-tour", `<mtp-play model="m" name="tour"></mtp-play><mtp-slider model="m" name="angle"></mtp-slider>`);
    const [play, ...steps] = [...document.querySelectorAll("mtp-play button")] as HTMLButtonElement[];
    return { ...w, play: play!, steps };
  }

  it("has a play button and one button per step, named after the step", async () => {
    const { play, steps } = await tour();
    expect(play.textContent).toBe("tour");
    expect(steps.map((b) => b.textContent)).toEqual(["quarter", "third", "two-fifths", "golden"]);
  });

  it("plays the tour step after step, waiting in between", async () => {
    const { play, anim, read } = await tour();
    play.click();
    expect(play.textContent).toBe("pause");
    anim.tick(1.5 + 1.5 + 2.5);
    expect(read("sunflower.angle")).toBeCloseTo(120);
  });

  it("pauses where it is, and goes on from there", async () => {
    const { play, anim, read } = await tour();
    play.click();
    anim.tick(1.5 + 1.5 + 1);
    play.click();
    const paused = read("sunflower.angle");
    anim.tick(5);
    expect(read("sunflower.angle")).toBe(paused);
    play.click();
    anim.tick(1.5);
    expect(read("sunflower.angle")).toBeCloseTo(120);
  });

  it("lights the step whose values hold", async () => {
    const { play, steps, anim } = await tour();
    play.click();
    anim.tick(1.5);
    expect(steps.map((b) => b.getAttribute("aria-pressed"))).toEqual(["true", "false", "false", "false"]);
  });

  it("jumps to a step clicked while playing, and keeps playing", async () => {
    const { play, steps, anim, read } = await tour();
    play.click();
    anim.tick(1);
    steps[3]!.click();
    anim.tick(3);
    expect(read("sunflower.angle")).toBeCloseTo(137.5077640500378);
    expect(read("name.value")).toBe("the golden angle");
  });

  it("runs a step clicked while stopped on its own", async () => {
    const { steps, anim, read } = await tour();
    steps[2]!.click();
    anim.tick(2.5);
    expect(read("sunflower.angle")).toBeCloseTo(144);
    expect(anim.busy()).toBe(false);
  });

  it("is cancelled by any other input that writes what it writes", async () => {
    const { play, anim, read } = await tour();
    play.click();
    anim.tick(4);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "0.2";
    input.dispatchEvent(new Event("input"));
    anim.tick(10);
    expect(read("sunflower.angle")).toBeCloseTo(100);
    expect(play.textContent).toBe("tour");
  });
});

describe("errors", () => {
  it("says when a control is missing or of another kind", async () => {
    await page("golden-tour", `<mtp-slider model="m" name="nope"></mtp-slider><mtp-button model="m" name="angle"></mtp-button>`);
    expect(document.querySelector("mtp-slider")?.textContent).toMatch(/no slider named nope/);
    expect(document.querySelector("mtp-button")?.textContent).toMatch(/angle is a slider, not a button/);
  });
});

describe("dragging on a canvas", () => {
  const ID = [1, 0, 0, 0, 1, 0];
  const style = { transform: ID, fill: "red", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };
  // A 10 by 10 view drawn 100 pixels wide: 10 pixels a unit, with y pointing up.
  const doc: Doc = {
    mtp: 1,
    objects: [
      { id: 0, kind: "canvas", name: "view", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [1] },
      { id: 1, kind: "root", name: "s", attrs: { transform: ID }, members: [2, 3] },
      { id: 2, kind: "circle", name: "u", parent: 1, attrs: { ...style, x: 1, y: 1, r: 0.5 } },
      { id: 3, kind: "circle", name: "still", parent: 1, attrs: { ...style, x: 5, y: 5, r: 0.5 } },
      { id: 4, kind: "on-drag", name: null, attrs: {}, node: 2, target: [2, "pos"], conditions: [], when: null },
    ],
    functions: {},
    names: { u: 2, still: 3 },
    depends: {},
  };

  async function canvas() {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = doc;
    await new Promise((r) => setTimeout(r, 0));
    const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
    svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) });
    const shape = (name: string) => svg.querySelector(`[data-mtp-id="${doc.names[name]}"]`) as SVGElement;
    const pointer = (type: string, el: Element, x: number, y: number) =>
      el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, pointerId: 1 }));
    return { rt: model.runtime!, svg, shape, pointer };
  }

  it("drags a shape with the pointer", async () => {
    const { rt, svg, shape, pointer } = await canvas();
    pointer("pointerdown", shape("u"), 10, 90);
    pointer("pointermove", svg, 30, 70);
    expect([rt.value(2, "x"), rt.value(2, "y")]).toEqual([3, 3]);
    pointer("pointerup", svg, 30, 70);
    pointer("pointermove", svg, 50, 50);
    expect([rt.value(2, "x"), rt.value(2, "y")]).toEqual([3, 3]);
  });

  it("redraws while dragging", async () => {
    const { svg, shape, pointer } = await canvas();
    pointer("pointerdown", shape("u"), 10, 90);
    pointer("pointermove", svg, 30, 90);
    expect(shape("u").getAttribute("transform")).toContain(" 3 ");
  });

  it("marks what can be dragged, so the page does not scroll instead", async () => {
    const { shape } = await canvas();
    expect(shape("u").style.touchAction).toBe("none");
    expect(shape("u").style.cursor).toBe("grab");
    expect(shape("still").style.touchAction).toBe("");
  });

  it("ignores presses on shapes that cannot be dragged", async () => {
    const { rt, svg, shape, pointer } = await canvas();
    pointer("pointerdown", shape("still"), 50, 50);
    pointer("pointermove", svg, 60, 50);
    expect(rt.value(3, "x")).toBe(5);
  });
});

describe("the best-embedding example", () => {
  it("shows the distortion while a point is dragged, and the optimum button brings it back", async () => {
    const { rt, anim } = await page("best-embedding", `<mtp-button model="m" name="best"></mtp-button>`);
    const names = example("best-embedding").names;
    expect(text("distortion")).toBe("distortion 1.155");
    const drags = (document.querySelector("mtp-model") as MtpModel).drags!;
    drags.grab(names.u!, [0, 3]);
    drags.move([0, 4.5]);
    (document.querySelector("mtp-model") as MtpModel).changed();
    expect(text("distortion")).toBe("distortion 1.732");
    drags.release();
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    anim.tick(1);
    expect(text("distortion")).toBe("distortion 1.155");
    expect(rt.value(names.u!, "y")).toBeCloseTo(3);
  });
});

describe("<mtp-readout>", () => {
  it("shows a string from the scene inline, and follows changes", async () => {
    const { model, rt } = await page("best-embedding", `<p>The <mtp-readout model="m" name="distortion"></mtp-readout> so far.</p>`);
    const el = document.querySelector("mtp-readout")!;
    expect(el.textContent).toBe("1.155");
    const names = example("best-embedding").names;
    rt.write(names.u!, "y", 4.5);
    model.changed();
    expect(el.textContent).toBe("1.732");
    expect(el.closest("p")?.textContent).toBe("The 1.732 so far.");
  });

  it("says when there is no such readout", async () => {
    await page("best-embedding", `<mtp-readout model="m" name="readout"></mtp-readout>`);
    expect(document.querySelector("mtp-readout")?.textContent).toMatch(/readout is a text, not a readout/);
  });
});

describe("the unit-circle example", () => {
  it("drags the point along the circle, and the slider and readouts follow", async () => {
    const { model, rt } = await page(
      "unit-circle",
      `<mtp-slider model="m" name="turn"></mtp-slider><p>x is <mtp-readout model="m" name="x-now"></mtp-readout></p>`,
    );
    const names = example("unit-circle").names;
    const drags = model.drags!;
    expect(drags.grab(names.p!, [6 * Math.cos((40 * Math.PI) / 180), 6 * Math.sin((40 * Math.PI) / 180)])).toBe(true);
    drags.move([0, 6]);
    model.changed();
    expect(rt.value(names.theta!, "value")).toBeCloseTo(90, 2);
    expect(Number((document.querySelector("mtp-slider input") as HTMLInputElement).value)).toBeCloseTo(0.25, 3);
    expect(document.querySelector("mtp-readout")?.textContent).toBe("+0.000");
  });
});

describe("the unit-circle toggles", () => {
  it("fade each function's line, name and value in and out", async () => {
    const { anim } = await page(
      "unit-circle",
      `<mtp-toggle model="m" name="show-sec"></mtp-toggle><mtp-toggle model="m" name="show-tan"></mtp-toggle>`,
    );
    const shown = () => [...document.querySelectorAll("mtp-canvas text")].map((t) => t.textContent?.split(" ")[0]);
    expect(shown()).not.toContain("sec");
    expect(shown()).toContain("tan");
    const [sec, tan] = [...document.querySelectorAll("mtp-toggle input")] as HTMLInputElement[];
    sec!.click();
    tan!.click();
    anim.tick(0.2);
    expect(shown()).toContain("sec");
    expect(shown()).toContain("tan");
    expect(document.querySelectorAll("mtp-canvas g[opacity]").length).toBe(2);
    anim.tick(0.2);
    expect(shown()).toContain("sec");
    expect(shown()).not.toContain("tan");
    expect(document.querySelectorAll("mtp-canvas g[opacity]").length).toBe(0);
  });
});

describe("<mtp-play> over an animation that names another", () => {
  it("has the named animation's steps, with their names", async () => {
    const doc = (await import("./data/fixtures/wrapped-play.json")).default as unknown as Doc;
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-play model="m" name="p"></mtp-play>`;
    (document.querySelector("mtp-model") as MtpModel).doc = doc;
    await new Promise((r) => setTimeout(r, 0));
    const [, ...steps] = [...document.querySelectorAll("mtp-play button")];
    expect(steps.map((b) => b.textContent)).toEqual(["small", "big"]);
  });
});

describe("labels", () => {
  it("follow the values they show", async () => {
    const doc = (await import("./data/fixtures/live-labels.json")).default as unknown as Doc;
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-button model="m" name="b"></mtp-button>
      <mtp-slider model="m" name="s2"></mtp-slider><mtp-toggle model="m" name="t"></mtp-toggle>
      <mtp-play model="m" name="p"></mtp-play>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = doc;
    await new Promise((r) => setTimeout(r, 0));
    const texts = () => ["mtp-button", "mtp-slider", "mtp-toggle", "mtp-play"].map((t) => document.querySelector(t)!.textContent!.trim());
    expect(texts()).toEqual(["b1", "s1", "t1", "p1"]);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    model.animator!.tick(0.01);
    expect(texts()).toEqual(["b2", "s2", "t2", "p2"]);
  });
});

describe("<mtp-slider> with steps", () => {
  it("has (step n) places, both ends included", async () => {
    const doc = (await import("./data/fixtures/stepped-slider.json")).default as unknown as Doc;
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-slider model="m" name="four"></mtp-slider>`;
    (document.querySelector("mtp-model") as MtpModel).doc = doc;
    await new Promise((r) => setTimeout(r, 0));
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(Number(input.step)).toBeCloseTo(1 / 3);
  });
});
