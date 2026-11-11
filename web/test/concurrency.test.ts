// Writers moving the same targets at the same time (docs/reference.md, "Concurrency"; the author,
// 2026-11-11, mtp-vs5d, mtp-s7z9, mtp-ddi1): whatever the reader is doing now, or did last, wins.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string): [MtpModel, Runtime, (name: string, attr?: string) => unknown] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("concurrency");
  const rt = model.runtime!;
  return [model, rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

const buttons = (...names: string[]) => names.map((n) => `<mtp-button model="m" name="${n}"></mtp-button>`).join("");
const press = (name: string) => (document.querySelector(`mtp-button[name="${name}"] button`) as HTMLButtonElement).click();
const playButton = (name: string) => document.querySelector(`mtp-play[name="${name}"] .mtp-play-button`) as HTMLButtonElement;

beforeEach(() => {
  queued = [];
  clock = 0;
  vi.spyOn(performance, "now").mockImplementation(() => clock);
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("a writer set off by the reader, not exclusive, while it runs", () => {
  it("is cancelled by a newcomer the reader sets off", () => {
    const [, , v] = page(buttons("go", "back"));
    press("go");
    pass(0.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });

  it("refuses a newcomer the reader did not set off: an on-view", () => {
    const [model, rt, v] = page(buttons("go") + `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    press("go");
    pass(0.5);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(10);
  });

  it("refuses a newcomer the reader did not set off: an autoplay", () => {
    const [model, rt, v] = page(buttons("go") + `<mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play>`);
    press("go");
    pass(0.5);
    model.markSeen(rt.id("z"));
    expect(v("auto", "playing")).toBe(false);
    pass(1.5);
    expect(v("k")).toBe(10);
  });
});

describe("an exclusive writer, while it runs", () => {
  it("refuses a newcomer the reader sets off", () => {
    const [, , v] = page(buttons("lock", "back"));
    press("lock");
    pass(0.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(10);
  });

  it("refuses a newcomer the reader did not set off", () => {
    const [model, rt, v] = page(buttons("lock") + `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    press("lock");
    pass(0.5);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(10);
  });

  it("refuses the whole newcomer, so none of its moves happen, even on other targets", () => {
    const [, , v] = page(buttons("lock", "both"));
    press("lock");
    pass(0.5);
    press("both");
    pass(1.5);
    expect([v("k"), v("j")]).toEqual([10, 0]);
  });

  it("allows a newcomer on a different target", () => {
    const [, , v] = page(buttons("lock", "other"));
    press("lock");
    pass(0.5);
    press("other");
    pass(1.5);
    expect([v("k"), v("j")]).toEqual([10, 5]);
  });

  it("refuses newcomers only until it ends", () => {
    const [, , v] = page(buttons("lock", "back"));
    press("lock");
    pass(1.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });
});

describe("a writer the reader did not set off, not exclusive, while it runs", () => {
  it("is cancelled by a newcomer the reader sets off", () => {
    const [model, rt, v] = page(buttons("back") + `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    rt.write(rt.id("k"), null, 2);
    model.markSeen(rt.id("v"));
    pass(0.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });

  it("is cancelled by a newcomer the reader did not set off", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play>`);
    model.markSeen(rt.id("v"));
    pass(0.5);
    model.markSeen(rt.id("z"));
    pass(1.5);
    expect(v("k")).toBe(3);
  });
});

describe("a play the reader started", () => {
  it("is not cancelled by an on-view or an autoplay while it runs", () => {
    const [model, rt, v] = page(
      `<mtp-play model="m" name="tour"></mtp-play><mtp-canvas model="m" name="v"></mtp-canvas>` +
        `<mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play>`,
    );
    playButton("tour").click();
    pass(0.5);
    model.markSeen(rt.id("v"));
    model.markSeen(rt.id("z"));
    pass(2);
    expect(v("k")).toBe(10);
    expect(v("auto", "playing")).toBe(false);
  });

  it("started by autoplay becomes the reader's once the reader presses it", () => {
    const [model, rt, v] = page(
      `<mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play><mtp-canvas model="m" name="v"></mtp-canvas>`,
    );
    model.markSeen(rt.id("z"));
    pass(0.3);
    // Paused and played again by the reader.
    playButton("auto").click();
    playButton("auto").click();
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(3);
  });

  it("cancelled, goes on from where it stopped, its move starting again from the value the slider left", () => {
    const [, , v] = page(`<mtp-play model="m" name="tour"></mtp-play><mtp-slider model="m" name="sl"></mtp-slider>`);
    playButton("tour").click();
    pass(1);
    expect(v("k")).toBeCloseTo(5);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "200";
    input.dispatchEvent(new Event("input"));
    pass(0.5);
    expect(v("k")).toBe(2);
    expect(v("tour", "playing")).toBe(false);
    playButton("tour").click();
    expect(v("tour", "playing")).toBe(true);
    // From 2 at the press to 10 over the second the move had left.
    expect(v("k")).toBeCloseTo(2);
    pass(0.5);
    expect(v("k")).toBeCloseTo(6);
    pass(0.6);
    expect(v("k")).toBe(10);
    expect(v("tour", "playing")).toBe(false);
  });
});

describe("a drag", () => {
  const svg = () => document.querySelector("mtp-canvas svg")!;
  const shape = (rt: Runtime, name: string) => document.querySelector(`mtp-canvas [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0, y = 0) =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));

  it("held, refuses an on-view on the dragged shape", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    model.markSeen(rt.id("w"));
    pass(1.5);
    expect(v("d", "x")).toBe(0);
    at(svg(), "pointermove", 30, 0);
    const moved = v("d", "x");
    expect(moved).not.toBe(0);
    pass(1.5);
    expect(v("d", "x")).toBe(moved);
    at(svg(), "pointerup", 30, 0);
  });

  it("is a running writer only until the release", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    at(svg(), "pointermove", 30, 0);
    at(svg(), "pointerup", 30, 0);
    model.markSeen(rt.id("w"));
    pass(1.5);
    expect(v("d", "x")).toBe(8);
  });

  it("held, is cancelled by an on-enter the pointer sets off", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    at(shape(rt, "e"), "pointermove", 30, 0);
    pass(1.5);
    expect(v("d", "x")).toBe(3);
    at(svg(), "pointermove", 60, 0);
    expect(v("d", "x")).toBe(3);
    at(svg(), "pointerup", 60, 0);
  });

  it("exclusive, refuses both an on-view and an on-enter", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="held"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    model.markSeen(rt.id("held"));
    at(shape(rt, "e"), "pointermove", 30, 0);
    const moved = v("d", "x");
    expect(moved).not.toBe(0);
    pass(1.5);
    expect(v("d", "x")).toBe(moved);
    at(svg(), "pointermove", 60, 0);
    expect(v("d", "x")).not.toBe(moved);
    at(svg(), "pointerup", 60, 0);
  });
});

describe("a group's attribute", () => {
  // mtp-s7z9: a writer of g.r is one writer of each member's r.
  it("a writer of it is cancelled by a writer of a member's", () => {
    const [, , v] = page(buttons("grow", "grow-one"));
    press("grow");
    pass(0.5);
    press("grow-one");
    pass(1.5);
    expect([v("c1", "r"), v("c2", "r")]).toEqual([2, 2]);
  });

  it("a writer of it cancels a writer of a member's", () => {
    const [, , v] = page(buttons("grow", "grow-one"));
    press("grow-one");
    pass(0.5);
    press("grow");
    pass(1.5);
    expect([v("c1", "r"), v("c2", "r")]).toEqual([3, 3]);
  });

  it("a writer of it is refused by an exclusive writer of a member's, on every member", () => {
    const [, , v] = page(buttons("hold-one", "grow"));
    press("hold-one");
    pass(0.5);
    press("grow");
    pass(1.5);
    expect([v("c1", "r"), v("c2", "r")]).toEqual([2, 1]);
  });
});

describe("a slider", () => {
  // The author, 2026-11-11: a slider is a running writer while the reader holds its knob, as a
  // drag is.
  const input = () => document.querySelector("mtp-slider input") as HTMLInputElement;
  const slide = (to: number) => {
    input().value = String(to);
    input().dispatchEvent(new Event("input"));
  };
  const knob = (type: string) => input().dispatchEvent(new PointerEvent(type, { bubbles: true }));

  it("held, is a running writer that refuses an on-view", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-canvas model="m" name="v"></mtp-canvas>`);
    knob("pointerdown");
    slide(200);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(2);
    knob("pointerup");
  });

  it("released, no longer refuses an on-view", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-canvas model="m" name="v"></mtp-canvas>`);
    knob("pointerdown");
    slide(200);
    knob("pointerup");
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(4);
  });

  it("is released by a pointercancel too", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-canvas model="m" name="v"></mtp-canvas>`);
    knob("pointerdown");
    slide(200);
    knob("pointercancel");
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(4);
  });

  it("held and cancelled by a newcomer the reader sets off, writes nothing more until its release", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider>` + buttons("back"));
    knob("pointerdown");
    slide(500);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
    slide(800);
    expect(v("k")).toBe(0);
    knob("pointerup");
    slide(800);
    expect(v("k")).toBe(8);
  });

  it("exclusive and held, refuses a newcomer the reader sets off", () => {
    const [, , v] = page(`<mtp-slider model="m" name="locked"></mtp-slider>` + buttons("back"));
    knob("pointerdown");
    slide(500);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(5);
    knob("pointerup");
  });

  it("exclusive, holds the lock during a step from a key, which takes no time", () => {
    const [, rt, v] = page(`<mtp-slider model="m" name="locked"></mtp-slider>` + buttons("back"));
    const write = rt.write.bind(rt);
    let pressed = false;
    rt.write = (...args: Parameters<typeof rt.write>) => {
      if (!pressed) {
        pressed = true;
        press("back");
      }
      return write(...args);
    };
    slide(500);
    pass(1.5);
    expect(v("k")).toBe(5);
    rt.write = write;
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });
});

describe("an exclusive on-pointermove", () => {
  it("holds the lock on its target during each write, which takes no time", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="pm"></mtp-canvas>` + buttons("jump"));
    const write = rt.write.bind(rt);
    let pressed = false;
    rt.write = (...args: Parameters<typeof rt.write>) => {
      if (!pressed && args[0] === rt.id("p")) {
        pressed = true;
        press("jump");
      }
      return write(...args);
    };
    const svg = document.querySelector("mtp-canvas svg")!;
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 0, clientY: 0, pointerId: 1 }));
    expect(pressed).toBe(true);
    const written = v("p");
    pass(1.5);
    expect(v("p")).toEqual(written);
    rt.write = write;
    press("jump");
    pass(1.5);
    expect(v("p")).toEqual([1, 1]);
  });
});
