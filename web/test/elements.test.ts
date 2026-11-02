// The page elements (docs/data-model.md, "On the page"; docs/reference.md, "Components" and
// "Controls").
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";

const docs = import.meta.glob("./data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });
const PAGE = docs["./data/runtime/page.mtpc"] as string;

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

/** Moves time forward by seconds, one animation frame at a time. */
function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string, doc: Doc = JSON.parse(PAGE) as Doc): [MtpModel, Runtime, (name: string, attr?: string) => unknown] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  const rt = model.runtime!;
  return [model, rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

beforeEach(() => {
  queued = [];
  clock = 0;
});

describe("the model", () => {
  it("tells its views when anything changes", () => {
    const [, rt] = page(`<mtp-readout model="m" name="r"></mtp-readout>`);
    const readout = document.querySelector("mtp-readout")!;
    expect(readout.textContent).toBe("k = 0.0");
    rt.write(rt.id("k"), null, 5);
    expect(readout.textContent).toBe("k = 5.0");
  });

  it("refuses a file of another version", () => {
    page(`<mtp-readout model="m" name="r"></mtp-readout>`, { ...(JSON.parse(PAGE) as Doc), mtpc: 1 });
    expect(document.querySelector("mtp-readout .mtp-error")!.textContent).toContain("version 2");
  });
});

describe("controls", () => {
  it("a slider sets how far along its animation is", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(document.querySelector("mtp-slider label")!.textContent).toBe("k");
    input.value = "500";
    input.dispatchEvent(new Event("input"));
    expect(v("k")).toBe(5);
    expect(v("sl", "position")).toBe(0.5);
  });

  it("a button plays its animation over time", () => {
    const [, , v] = page(`<mtp-button model="m" name="go"></mtp-button>`);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    // The first frame starts the clock: the model times frames from when it woke.
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(2.5);
    pass(1);
    expect(v("k")).toBe(5);
  });

  it("play pauses and resumes, and shows a button per step", () => {
    const [, , v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    const buttons = document.querySelectorAll("mtp-play button");
    expect(buttons.length).toBe(3);
    const play = buttons[0] as HTMLButtonElement;
    play.click();
    expect(play.textContent).toBe("pause");
    expect(v("run", "playing")).toBe(true);
    pass(0.5);
    play.click();
    const paused = v("k");
    pass(1);
    expect(v("k")).toBe(paused);
    play.click();
    pass(2);
    expect(v("k")).toBe(4);
  });

  it("a step clicked while stopped runs that step alone", () => {
    const [, rt, v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    rt.write(rt.id("k"), null, 9);
    const second = document.querySelectorAll("mtp-play button")[2] as HTMLButtonElement;
    second.click();
    pass(0.1);
    pass(0.5);
    // The second step moves k from 9, where it is, to 4; the first step does not run.
    expect(v("k")).toBeCloseTo(6.5);
    pass(1);
    expect(v("k")).toBe(4);
    expect(v("run", "playing")).toBe(false);
  });

  it("a step clicked while playing stops the play and animates that step alone", () => {
    const [, , v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    const [play, , second] = document.querySelectorAll("mtp-play button") as NodeListOf<HTMLButtonElement>;
    play!.click();
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(1);
    second!.click();
    // The clock is already running, so no frame is needed to start it.
    pass(0.5);
    // From 1, where k was, towards 4: it does not jump to the second step's start.
    expect(v("k")).toBeCloseTo(2.5);
    pass(1);
    expect(v("k")).toBe(4);
    pass(2);
    expect(v("k")).toBe(4);
    expect(v("run", "playing")).toBe(false);
  });

  it("a step clicked cancels any other writer moving what the play moves", () => {
    const [, , v] = page(`<mtp-button model="m" name="go"></mtp-button><mtp-play model="m" name="run"></mtp-play>`);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(2.5);
    (document.querySelectorAll("mtp-play button")[2] as HTMLButtonElement).click();
    pass(0.1);
    pass(2);
    expect(v("k")).toBe(4);
  });

  it("a slider follows its target when another writer changes it", () => {
    const [, rt] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    rt.write(rt.id("k"), null, 7);
    expect(Number(input.value) / Number(input.max)).toBeCloseTo(0.7, 2);
  });

  it("a toggle holds its own value, or writes its target", () => {
    const [, , v] = page(`<mtp-toggle model="m" name="own"></mtp-toggle><mtp-toggle model="m" name="t"></mtp-toggle>`);
    const [own, t] = [...document.querySelectorAll("mtp-toggle input")] as HTMLInputElement[];
    own!.click();
    expect(v("own", "value")).toBe(true);
    t!.click();
    expect(v("on")).toBe(true);
  });

  it("a toggle on a group's attribute shows a mixed state, and a click sets every member", () => {
    const [, rt] = page(`<mtp-toggle model="m" name="all"></mtp-toggle>`);
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    expect(input.indeterminate).toBe(true);
    input.dispatchEvent(new Event("change"));
    const lamps = rt.objects[rt.id("lamps")]!.members!;
    expect(lamps.map((m) => rt.value(m, "lit"))).toEqual([true, true]);
  });
});

describe("a canvas", () => {
  it("draws its scene and plays an on-click on a click", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    const orbit = document.querySelector(`mtp-canvas [data-mtp-id="${rt.id("orbit")}"]`)!;
    expect(orbit).not.toBeNull();
    orbit.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    orbit.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    pass(0.1);
    expect(v("on")).toBe(true);
  });
});

describe("a canvas's showing and hiding", () => {
  const FADE = docs["./data/runtime/fade.mtpc"] as string;

  function opacityOf(rt: Runtime, name: string, canvas = "v"): number | null {
    const el = document.querySelector(`mtp-canvas[name="${canvas}"] [data-mtp-id="${rt.id(name)}"]`);
    if (!el) return null;
    const g = el.closest("[data-mtp-fade]");
    return g ? Number(g.getAttribute("opacity")) : 1;
  }

  it("fades what a when item shows along the canvas's transition", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, JSON.parse(FADE) as Doc);
    expect(opacityOf(rt, "d")).toBeNull();
    rt.write(rt.id("show"), null, true);
    pass(0.1);
    pass(0.5);
    expect(opacityOf(rt, "d")).toBeCloseTo(0.5);
    pass(1);
    expect(opacityOf(rt, "d")).toBe(1);
  });

  it("shows and hides at once with no transition", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="still"></mtp-canvas>`, JSON.parse(FADE) as Doc);
    rt.write(rt.id("show"), null, true);
    expect(opacityOf(rt, "d", "still")).toBe(1);
  });
});
