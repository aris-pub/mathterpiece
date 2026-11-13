// Writers moving the same targets at the same time (docs/reference.md, "Concurrency"; the author,
// 2026-11-11, mtp-vs5d, mtp-s7z9, mtp-wjtd): whatever the reader is doing now, or did last, wins.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Scheduler } from "../src/animate.ts";
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

describe("a writer set off by the reader, while it runs", () => {
  it("is cancelled by a newcomer the reader sets off", () => {
    const [, , v] = page(buttons("go", "back"));
    press("go");
    pass(0.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });

  it("rejects the writes of a newcomer the reader did not set off: an on-view", () => {
    const [model, rt, v] = page(buttons("go") + `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    press("go");
    pass(0.5);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(10);
  });
});

describe("a writer of a higher priority, while it runs", () => {
  it("rejects the writes of a newcomer the reader sets off", () => {
    const [, , v] = page(buttons("lock", "back"));
    press("lock");
    pass(0.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(10);
  });

  it("rejects the writes of a newcomer the reader did not set off", () => {
    const [model, rt, v] = page(buttons("lock") + `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    press("lock");
    pass(0.5);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(10);
  });

  // Each value is decided on its own: the newcomer's move of j goes on (the author, 2026-11-13).
  it("rejects a newcomer's writes of its values only, and accepts its others", () => {
    const [, , v] = page(buttons("lock", "both"));
    press("lock");
    pass(0.5);
    press("both");
    pass(1.5);
    expect([v("k"), v("j")]).toEqual([10, 5]);
  });

  it("allows a newcomer on a different target", () => {
    const [, , v] = page(buttons("lock", "other"));
    press("lock");
    pass(0.5);
    press("other");
    pass(1.5);
    expect([v("k"), v("j")]).toEqual([10, 5]);
  });

  it("rejects the writes of newcomers only until it ends", () => {
    const [, , v] = page(buttons("lock", "back"));
    press("lock");
    pass(1.5);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(0);
  });
});

describe("a writer the reader did not set off, while it runs", () => {
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
    const [model, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="late"></mtp-canvas>`);
    model.markSeen(rt.id("v"));
    pass(0.5);
    model.markSeen(rt.id("late"));
    pass(1.5);
    expect(v("k")).toBe(3);
  });
});

describe("a play the reader started", () => {
  it("is not cancelled by an on-view while it runs", () => {
    const [model, rt, v] = page(`<mtp-play model="m" name="tour"></mtp-play><mtp-canvas model="m" name="v"></mtp-canvas>`);
    playButton("tour").click();
    pass(0.5);
    model.markSeen(rt.id("v"));
    pass(2);
    expect(v("k")).toBe(10);
  });
});

describe("a drag", () => {
  const svg = () => document.querySelector("mtp-canvas svg")!;
  const shape = (rt: Runtime, name: string) => document.querySelector(`mtp-canvas [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0, y = 0) =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));

  // The author, 2026-11-12: a drag is a running writer from its first change of value, not
  // from the grab.
  it("held and moved, refuses an on-view on the dragged shape", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    at(svg(), "pointermove", 30, 0);
    const moved = v("d", "x");
    expect(moved).not.toBe(0);
    model.markSeen(rt.id("w"));
    pass(1.5);
    expect(v("d", "x")).toBe(moved);
    at(svg(), "pointerup", 30, 0);
  });

  it("grabbed and not yet moved, writes nothing, so an on-view plays", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    model.markSeen(rt.id("w"));
    pass(1.5);
    expect(v("d", "x")).toBe(8);
    at(svg(), "pointerup", 0, 0);
  });

  it("grabbed and not moved, leaves a play running", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas><mtp-play model="m" name="roll"></mtp-play>`);
    playButton("roll").click();
    pass(0.5);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    pass(0.5);
    expect(v("roll", "playing")).toBe(true);
    at(svg(), "pointerup", 0, 0);
    pass(1.2);
    expect(v("d", "x")).toBe(8);
  });

  it("moved, stops a play, which is then in explore mode", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas><mtp-play model="m" name="roll"></mtp-play>`);
    playButton("roll").click();
    pass(0.5);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    pass(0.5);
    at(svg(), "pointermove", 30, 0);
    expect(v("roll", "playing")).toBe(false);
    expect(document.querySelector("mtp-play")!.hasAttribute("data-mtp-exploring")).toBe(true);
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

  // The author, 2026-11-13: a held drag is a gesture, which no on-enter can cancel; the
  // on-enter's writes of the dragged shape are rejected.
  it("held, rejects the writes an on-enter the pointer sets off makes of the dragged shape", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    at(svg(), "pointermove", 10, 0);
    at(shape(rt, "e"), "pointermove", 30, 0);
    const moved = v("d", "x");
    pass(1.5);
    expect(v("d", "x")).toBe(moved);
    at(svg(), "pointermove", 60, 0);
    expect(v("d", "x")).not.toBe(moved);
    at(svg(), "pointerup", 60, 0);
  });

  // The move that starts a drag sets off its on-enter first and writes last, so the drag, a
  // writer from that first write, cancels the on-enter it set off.
  it("at its first move, cancels an on-enter that move sets off", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="w"></mtp-canvas>`);
    at(shape(rt, "d"), "pointerdown", 0, 0);
    at(shape(rt, "e"), "pointermove", 30, 0);
    const moved = v("d", "x");
    expect(moved).not.toBe(0);
    pass(1.5);
    expect(v("d", "x")).toBe(moved);
    at(svg(), "pointerup", 30, 0);
  });

  it("of a higher priority, rejects the writes of both an on-view and an on-enter", () => {
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

  // Each member's value is decided on its own (the author, 2026-11-13).
  it("a writer of it is rejected on a member a writer of a higher priority owns, and writes the others", () => {
    const [, , v] = page(buttons("hold-one", "grow"));
    press("hold-one");
    pass(0.5);
    press("grow");
    pass(1.5);
    expect([v("c1", "r"), v("c2", "r")]).toEqual([2, 3]);
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

  // The author, 2026-11-13: a press on the track or the knob through the release is one gesture,
  // triggered by the press, so a gesture of the same priority triggered after the press but
  // before the first move is the newer one.
  it("is triggered by the press, not by its first move", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const k = rt.id("k");
    knob("pointerdown");
    const later = { targets: [`${k}:`], done: false, time: 0, release() {}, seek: () => rt.write(k, null, 7) };
    model.scheduler!.start(later as never, {}, { reader: true, held: true });
    slide(200);
    expect(v("k")).toBe(7);
    knob("pointerup");
  });

  it("held, is a running writer that refuses an on-view", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-canvas model="m" name="v"></mtp-canvas>`);
    knob("pointerdown");
    slide(200);
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(2);
    knob("pointerup");
  });

  // The author, 2026-11-12: a held slider is a running writer from its first change of value.
  it("grabbed and not moved, leaves a play running", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-play model="m" name="tour"></mtp-play>`);
    playButton("tour").click();
    pass(0.5);
    knob("pointerdown");
    pass(0.5);
    expect(v("tour", "playing")).toBe(true);
    knob("pointerup");
    pass(1.2);
    expect(v("k")).toBe(10);
  });

  it("grabbed and moved, stops a play, which is then in explore mode", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-play model="m" name="tour"></mtp-play>`);
    playButton("tour").click();
    pass(0.5);
    knob("pointerdown");
    pass(0.5);
    slide(200);
    expect(v("tour", "playing")).toBe(false);
    expect(document.querySelector("mtp-play")!.hasAttribute("data-mtp-exploring")).toBe(true);
    pass(1);
    expect(v("k")).toBe(2);
    knob("pointerup");
  });

  it("grabbed and not moved, writes nothing, so an on-view plays", () => {
    const [model, rt, v] = page(`<mtp-slider model="m" name="sl"></mtp-slider><mtp-canvas model="m" name="v"></mtp-canvas>`);
    knob("pointerdown");
    model.markSeen(rt.id("v"));
    pass(1.5);
    expect(v("k")).toBe(4);
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

  // The author, 2026-11-13: a held knob is a gesture, so a newcomer the reader sets off is
  // rejected on its value.
  it("held, rejects the writes of a newcomer the reader sets off, and writes on", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider>` + buttons("back"));
    knob("pointerdown");
    slide(500);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(5);
    slide(800);
    expect(v("k")).toBe(8);
    knob("pointerup");
  });

  it("of a higher priority and held, rejects the writes of a newcomer the reader sets off", () => {
    const [, , v] = page(`<mtp-slider model="m" name="locked"></mtp-slider>` + buttons("back"));
    knob("pointerdown");
    slide(500);
    press("back");
    pass(1.5);
    expect(v("k")).toBe(5);
    knob("pointerup");
  });

  it("of a higher priority, owns its value during a step from a key, which takes no time", () => {
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

describe("an on-pointermove, a gesture", () => {
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

describe("a shape whose position is worked out from other attributes", () => {
  // mtp-gzs9: writing its x, y or pos writes those attributes, so the writers meet.
  // The author, 2026-11-13: a polyline's x is neither free nor bound: a write of it writes each
  // point's x. Writers meet only on those values.
  it("a polyline's writer of points, pressed later, cancels a writer of its x", () => {
    const [, , v] = page(buttons("pl-x", "pl-points"));
    press("pl-x");
    pass(0.5);
    press("pl-points");
    pass(1.5);
    expect(v("pl", "points")).toEqual([
      [0, 0],
      [2, 0],
    ]);
  });

  it("a polyline's writer of x, pressed later, cancels a writer of its points", () => {
    const [, , v] = page(buttons("pl-points", "pl-x"));
    press("pl-points");
    pass(0.5);
    press("pl-x");
    pass(1.5);
    // A list of points jumps at the end of its move, so the points had not moved yet.
    expect(v("pl", "points")).toEqual([
      [5, 0],
      [5, 2],
    ]);
  });

  it("a polyline's writer of x and a writer of its y never meet", () => {
    const [, , v] = page(buttons("pl-x", "pl-y"));
    press("pl-x");
    pass(0.5);
    press("pl-y");
    pass(1.5);
    expect(v("pl", "points")).toEqual([
      [5, 4],
      [5, 6],
    ]);
  });

  // Two writers meet when a write of each writes a free value in common (docs/concurrency-model.md):
  // a writer of a high priority writes a, each value as it is, and the newcomer's write of b is
  // then rejected on some value.
  const meets = (model: MtpModel, rt: Runtime, a: string, b: string) => {
    const s = model.scheduler!;
    const target = (t: string): [number, string | null] => {
      const at = t.indexOf(":");
      return [Number(t.slice(0, at)), t.slice(at + 1) || null];
    };
    const same = (t: string) => {
      const [id, attr] = target(t);
      rt.write(id, attr, rt.value(id, attr));
    };
    const high = {};
    let met = false;
    s.instant(high, { reader: true, priority: 900 }, () => {
      same(a);
      met = !s.instant({}, { reader: true }, () => same(b));
    });
    return met;
  };
  const cases: [string, string[]][] = [
    ["pl", ["points"]],
    ["pg", ["points"]],
    ["cv", ["from", "to", "controls"]],
    ["ln", ["from", "to"]],
    ["tr", ["a", "b", "c"]],
  ];
  for (const [name, attrs] of cases) {
    it(`${name}: a writer of x, y or pos meets a writer of ${attrs.join(", ")}, both ways`, () => {
      const [model, rt] = page("");
      const id = rt.id(name);
      for (const pos of ["x", "y", "pos"]) {
        for (const attr of attrs) {
          expect(meets(model, rt, `${id}:${pos}`, `${id}:${attr}`), `${pos} then ${attr}`).toBe(true);
          expect(meets(model, rt, `${id}:${attr}`, `${id}:${pos}`), `${attr} then ${pos}`).toBe(true);
        }
      }
    });
  }

  // The free values are whole: a polyline's x and its y are both written into its points, so a
  // writer of x now meets a writer of y (docs/concurrency-model.md). A circle's x and y are two
  // free values, and a line's from and its to.
  it("a writer of x does not meet a writer of y, and a line's from does not meet its to", () => {
    const [model, rt] = page("");
    const pl = rt.id("pl");
    const ln = rt.id("ln");
    const d = rt.id("d");
    expect(meets(model, rt, `${pl}:x`, `${pl}:y`)).toBe(false);
    expect(meets(model, rt, `${ln}:from`, `${ln}:to`)).toBe(false);
    expect(meets(model, rt, `${pl}:pos`, `${pl}:y`)).toBe(true);
    expect(meets(model, rt, `${d}:x`, `${d}:y`)).toBe(false);
  });
});
