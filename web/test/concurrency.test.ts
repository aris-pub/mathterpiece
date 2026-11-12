// Writers moving the same targets at the same time (docs/reference.md, "Concurrency"; the author,
// 2026-11-11, mtp-vs5d, mtp-s7z9, mtp-wjtd): whatever the reader is doing now, or did last, wins.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Scheduler } from "../src/animate.ts";
import { HURRY, type MtpModel, define, frames } from "../src/elements.ts";
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
    // A press waits for the on-views of the page to have played (mtp-wjtd), so v's on-view plays
    // before the autoplay starts here, and cannot start after the press.
    const [model, rt, v] = page(
      `<mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play><mtp-canvas model="m" name="v"></mtp-canvas>`,
    );
    model.markSeen(rt.id("v"));
    pass(1.5);
    model.markSeen(rt.id("z"));
    pass(0.3);
    // Paused and played again by the reader.
    playButton("auto").click();
    playButton("auto").click();
    expect(v("auto", "playing")).toBe(true);
    pass(1.5);
    expect(v("k")).toBe(3);
  });

  // Open (mtp-wjtd): an autoplay running when the reader presses it before the on-views have
  // played. The hurried on-view cancels the autoplay, which is not put in explore mode since the
  // on-view's writes are part of state 0, and the press then neither resumes nor restarts it.
  it.todo("started by autoplay and cancelled by an on-view a press hurries, plays on the reader's press");
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

describe("a shape whose position is worked out from other attributes", () => {
  // mtp-gzs9: writing its x, y or pos writes those attributes, so the writers meet.
  it("a polyline's exclusive writer of x refuses a writer of its points", () => {
    const [, , v] = page(buttons("pl-x", "pl-points"));
    press("pl-x");
    pass(0.5);
    press("pl-points");
    pass(1.5);
    expect(v("pl", "points")).toEqual([
      [5, 0],
      [5, 2],
    ]);
  });

  it("a polyline's exclusive writer of points refuses a writer of its x", () => {
    const [, , v] = page(buttons("pl-points", "pl-x"));
    press("pl-points");
    pass(0.5);
    press("pl-x");
    pass(1.5);
    expect(v("pl", "points")).toEqual([
      [0, 0],
      [2, 0],
    ]);
  });

  const meets = (rt: Runtime, a: string, b: string) => {
    const s = new Scheduler(
      () => {},
      () => {},
      (t) => rt.reached(t),
    );
    const held = {};
    s.grip([a], held, { reader: true, exclusive: true }, () => {});
    return !s.claim([b], {}, { reader: true, exclusive: false });
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
      const [, rt] = page("");
      const id = rt.id(name);
      for (const pos of ["x", "y", "pos"]) {
        for (const attr of attrs) {
          expect(meets(rt, `${id}:${pos}`, `${id}:${attr}`), `${pos} then ${attr}`).toBe(true);
          expect(meets(rt, `${id}:${attr}`, `${id}:${pos}`), `${attr} then ${pos}`).toBe(true);
        }
      }
    });
  }

  it("a writer of x does not meet a writer of y, and a line's from does not meet its to", () => {
    const [, rt] = page("");
    const pl = rt.id("pl");
    const ln = rt.id("ln");
    expect(meets(rt, `${pl}:x`, `${pl}:y`)).toBe(false);
    expect(meets(rt, `${ln}:from`, `${ln}:to`)).toBe(false);
    expect(meets(rt, `${pl}:pos`, `${pl}:y`)).toBe(true);
  });
});

describe("explore mode", () => {
  // mtp-wjtd: a play or stepper is in explore mode at rest, and goes into it again when another
  // writer writes what it moves before it has finished. Then the next play, "›" or right arrow
  // starts from state 0, and every jump is worked out from state 0.
  const both = (more = "") =>
    page(
      `<mtp-play model="m" name="trip"></mtp-play><mtp-stepper model="m" name="walk"></mtp-stepper>` +
        `<mtp-slider model="m" name="sl"></mtp-slider>` +
        buttons("set-j") +
        more,
    );
  // A canvas whose on-view moves k to 4 over a second.
  const viewed = () => both(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
  // An autoplay the reader did not set off, which a play or stepper the reader runs refuses.
  const auto = () => both(`<mtp-canvas model="m" name="z"></mtp-canvas><mtp-play model="m" name="auto"></mtp-play>`);
  const play = () => playButton("trip");
  const exploreOf = (tag: string) => document.querySelector(`${tag} .mtp-explore`) as HTMLButtonElement;
  const exploring = (tag: string) => exploreOf(tag).getAttribute("aria-pressed") === "true";
  const el = (tag: string) => document.querySelector(tag) as HTMLElement;
  const bars = () => [...document.querySelectorAll("mtp-play .mtp-bar")] as HTMLElement[];
  const fills = () => bars().map((b) => Number(b.style.getPropertyValue("--u")));
  const line = () => document.querySelector("mtp-play .mtp-now")!.textContent;
  const step = (which: string) => (document.querySelector(`mtp-stepper .mtp-${which}`) as HTMLButtonElement).click();
  const dots = () => [...document.querySelectorAll("mtp-stepper .mtp-dot")] as HTMLButtonElement[];
  const states = () => dots().map((d) => (d.getAttribute("aria-current") === "step" ? "now" : d.classList.contains("mtp-passed") ? "done" : "later"));
  const count = () => document.querySelector("mtp-stepper .mtp-count")!.textContent;
  const key = (tag: string, k: string) => el(tag).dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const slide = (to: number) => {
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = String(to);
    input.dispatchEvent(new Event("input"));
  };
  // happy-dom lays nothing out: trip's bars are 100, 200 and 100 pixels wide, 4 apart.
  const lay = () => {
    const rect = (left: number, width: number) => () => ({ left, width, right: left + width, top: 0, bottom: 4, height: 4, x: left, y: 0, toJSON: () => ({}) }) as DOMRect;
    const [a, b, c] = bars();
    a!.getBoundingClientRect = rect(0, 100);
    b!.getBoundingClientRect = rect(104, 200);
    c!.getBoundingClientRect = rect(308, 100);
  };
  const track = (type: string, x: number) =>
    document.querySelector("mtp-play .mtp-bars")!.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: 2, bubbles: true, pointerId: 1, button: 0 }));

  describe("a play", () => {
    it("is in explore mode before it is touched, showing no step", () => {
      const [, , v] = both();
      expect(exploring("mtp-play")).toBe(true);
      expect(exploreOf("mtp-play").textContent).toBe("Explore");
      expect(fills()).toEqual([0, 0, 0]);
      expect(line()).toBe("");
      expect(el("mtp-play").hasAttribute("data-step")).toBe(false);
      expect(v("trip", "playing")).toBe(false);
    });

    it("holds the time within its animation in its time, and its rest value in explore mode", () => {
      const [, , v] = both();
      expect(v("trip", "time")).toBe(0);
      play().click();
      pass(0.5);
      expect(v("trip", "time")).toBeCloseTo(0.5);
      press("set-j");
      expect(v("trip", "time")).toBe(0);
      play().click();
      pass(4.2);
      expect(v("trip", "time")).toBe(4);
    });

    it("puts the Explore button after its bars", () => {
      both();
      expect(el("mtp-play").lastElementChild).toBe(exploreOf("mtp-play"));
    });

    it("leaves explore mode when played, and is not in it once it has finished", () => {
      const [, , v] = both();
      play().click();
      expect(exploring("mtp-play")).toBe(false);
      pass(4.2);
      expect([v("j"), v("k")]).toEqual([7, 10]);
      expect(v("trip", "playing")).toBe(false);
      press("set-j");
      expect(exploring("mtp-play")).toBe(false);
      expect(fills()).toEqual([1, 1, 1]);
      expect(line()).toBe("3 / 3");
    });

    it("running, goes into explore mode when a slider writes what it moves, forgetting what it played", () => {
      const [, , v] = both();
      expect(v("trip", "step")).toBe(0);
      play().click();
      pass(2);
      expect(v("trip", "step")).toBe(2);
      slide(200);
      expect(v("k")).toBe(2);
      expect(exploring("mtp-play")).toBe(true);
      expect(fills()).toEqual([0, 0, 0]);
      expect(line()).toBe("");
      expect(el("mtp-play").hasAttribute("data-step")).toBe(false);
      expect(v("trip", "playing")).toBe(false);
      expect(v("trip", "step")).toBe(0);
      pass(1);
      expect(v("k")).toBe(2);
    });

    it("paused, goes into explore mode when a button writes what it moves", () => {
      both();
      play().click();
      pass(0.5);
      play().click();
      expect(exploring("mtp-play")).toBe(false);
      press("set-j");
      expect(exploring("mtp-play")).toBe(true);
    });

    it("does not go into explore mode for a write that is refused", () => {
      const [model, rt, v] = auto();
      play().click();
      pass(1.5);
      model.markSeen(rt.id("z"));
      pass(0.5);
      expect(exploring("mtp-play")).toBe(false);
      expect(v("trip", "playing")).toBe(true);
    });

    it("in explore mode, a press sets state 0 at once and plays from step 1", () => {
      const [, , v] = both();
      play().click();
      pass(2);
      press("set-j");
      expect(v("j")).toBe(1);
      expect(v("k")).toBeCloseTo(5);
      play().click();
      expect([v("j"), v("k")]).toEqual([0, 0]);
      expect(v("trip", "playing")).toBe(true);
      pass(0.5);
      expect(v("j")).toBeCloseTo(2.5);
      pass(3.7);
      expect([v("j"), v("k")]).toEqual([7, 10]);
    });

    it("in explore mode, Space plays as a press does", () => {
      const [, , v] = both();
      play().click();
      pass(2);
      press("set-j");
      key("mtp-play", " ");
      expect([v("j"), v("k")]).toEqual([0, 0]);
      expect(v("trip", "playing")).toBe(true);
    });

    it("in explore mode, the right arrow sets state 0 and stands at step 0", () => {
      const [, , v] = both();
      play().click();
      pass(2);
      press("set-j");
      key("mtp-play", "ArrowRight");
      expect([v("j"), v("k")]).toEqual([0, 0]);
      expect(v("trip", "playing")).toBe(false);
      expect(exploring("mtp-play")).toBe(false);
      expect(line()).toBe("0 / 3");
      key("mtp-play", "ArrowRight");
      expect([v("j"), v("k")]).toEqual([5, 0]);
    });

    // The author, 2026-11-12: a play stands at step 0, out of explore mode, in state 0 exactly,
    // with no move of step 1 done, not even one that takes no time.
    describe("at step 0", () => {
      const hop = () => page(`<mtp-play model="m" name="hop"></mtp-play>` + buttons("set-j"));
      const lay2 = () => {
        const rect = (left: number, width: number) => () => ({ left, width, right: left + width, top: 0, bottom: 4, height: 4, x: left, y: 0, toJSON: () => ({}) }) as DOMRect;
        const [a, b] = bars();
        a!.getBoundingClientRect = rect(0, 100);
        b!.getBoundingClientRect = rect(104, 200);
      };

      it("is where the right arrow goes from explore mode, showing step 0 and nothing played", () => {
        const [, , v] = hop();
        key("mtp-play", "ArrowRight");
        expect([v("j"), v("k")]).toEqual([0, 0]);
        expect(exploring("mtp-play")).toBe(false);
        expect(line()).toBe("0 / 2");
        expect(fills()).toEqual([0, 0]);
        expect(el("mtp-play").hasAttribute("data-step")).toBe(false);
        expect([v("hop", "step"), v("hop", "time"), v("hop", "playing")]).toEqual([0, 0, false]);
      });

      it("goes on with the right arrow to the next stop, and back to step 0 with the left", () => {
        const [, , v] = hop();
        key("mtp-play", "ArrowRight");
        key("mtp-play", "ArrowRight");
        expect([v("j"), v("k")]).toEqual([5, 0]);
        expect(line()).toBe("2 / 2");
        key("mtp-play", "ArrowLeft");
        expect([v("j"), v("k")]).toEqual([0, 0]);
        expect(line()).toBe("0 / 2");
      });

      it("is where a tap on bar 1 goes, whatever came before", () => {
        const [, , v] = hop();
        lay2();
        press("set-j");
        track("pointerdown", 50);
        track("pointerup", 50);
        expect([v("j"), v("k")]).toEqual([0, 0]);
        expect(exploring("mtp-play")).toBe(false);
        expect(line()).toBe("0 / 2");
      });

      it("plays from state 0 through the steps on Space", () => {
        const [, , v] = hop();
        key("mtp-play", "ArrowRight");
        key("mtp-play", " ");
        expect(v("hop", "playing")).toBe(true);
        expect(v("j")).toBe(1);
        pass(0.5);
        expect(v("j")).toBeCloseTo(3);
        pass(2.6);
        expect([v("j"), v("k")]).toEqual([5, 10]);
      });

      it("while playing, the left arrow back to the start plays on from there at once", () => {
        const [, , v] = hop();
        playButton("hop").click();
        pass(0.3);
        key("mtp-play", "ArrowLeft");
        expect(v("hop", "playing")).toBe(true);
        expect(v("j")).toBe(1);
        pass(0.5);
        expect(v("j")).toBeCloseTo(3);
      });
    });

    it("in explore mode, the left arrow does nothing", () => {
      const [, , v] = both();
      play().click();
      pass(2);
      press("set-j");
      key("mtp-play", "ArrowLeft");
      expect(v("j")).toBe(1);
      expect(v("k")).toBeCloseTo(5);
      expect(exploring("mtp-play")).toBe(true);
    });

    it("the Explore button pauses a running play and goes into explore mode; pressed again it does nothing", () => {
      const [, , v] = both();
      play().click();
      pass(0.5);
      exploreOf("mtp-play").click();
      expect(exploring("mtp-play")).toBe(true);
      expect(v("trip", "playing")).toBe(false);
      const j = v("j");
      pass(1);
      expect(v("j")).toBe(j);
      exploreOf("mtp-play").click();
      expect(exploring("mtp-play")).toBe(true);
      expect(v("j")).toBe(j);
    });

    it("a tap on a bar sets the state at that step's start worked out from state 0, whatever came before", () => {
      const [, , v] = both();
      lay();
      play().click();
      pass(2);
      press("set-j");
      slide(200);
      track("pointerdown", 150);
      track("pointerup", 150);
      expect([v("j"), v("k")]).toEqual([5, 0]);
      expect(exploring("mtp-play")).toBe(false);
      expect(el("mtp-play").getAttribute("data-step")).toBe("2");
      expect(line()).toBe("2 / 3");
    });

    it("a drag along the bars and the arrow keys jump to states worked out from state 0", () => {
      const [, , v] = both();
      lay();
      press("set-j");
      track("pointerdown", 150);
      track("pointermove", 204);
      expect(v("j")).toBe(5);
      expect(v("k")).toBeCloseTo(5);
      track("pointerup", 204);
      expect(exploring("mtp-play")).toBe(false);
      key("mtp-play", "ArrowRight");
      expect([v("j"), v("k")]).toEqual([5, 10]);
      key("mtp-play", "ArrowLeft");
      expect([v("j"), v("k")]).toEqual([5, 0]);
      key("mtp-play", "ArrowLeft");
      expect([v("j"), v("k")]).toEqual([0, 0]);
    });
  });

  describe("a stepper", () => {
    it("is in explore mode before it is touched, with no step and an empty count", () => {
      const [, , v] = both();
      expect(exploring("mtp-stepper")).toBe(true);
      expect(states()).toEqual(["later", "later", "later"]);
      expect(count()).toBe("");
      expect(el("mtp-stepper").hasAttribute("data-step")).toBe(false);
      expect([v("walk", "step"), v("walk", "playing")]).toEqual([0, false]);
      expect((document.querySelector("mtp-stepper .mtp-prev") as HTMLButtonElement).disabled).toBe(true);
    });

    it("puts the Explore button after › and the count", () => {
      both();
      const parts = [...el("mtp-stepper").children].map((c) => c.className);
      expect(parts.slice(-3)).toEqual(["mtp-step-button mtp-next", "mtp-count", "mtp-explore"]);
    });

    it("partway through a step, goes into explore mode when a slider writes what it moves", () => {
      const [, , v] = both();
      step("next");
      pass(1.2);
      step("next");
      pass(1);
      slide(200);
      expect(exploring("mtp-stepper")).toBe(true);
      expect(states()).toEqual(["later", "later", "later"]);
      expect(count()).toBe("");
      expect(el("mtp-stepper").hasAttribute("data-step")).toBe(false);
      expect([v("walk", "step"), v("walk", "playing")]).toEqual([0, false]);
      expect((document.querySelector("mtp-stepper .mtp-prev") as HTMLButtonElement).disabled).toBe(true);
      pass(1);
      expect(v("k")).toBe(2);
    });

    it("between two steps, goes into explore mode when a button writes what it moves", () => {
      both();
      step("next");
      pass(1.2);
      expect(count()).toBe("1 / 3");
      press("set-j");
      expect(exploring("mtp-stepper")).toBe(true);
      expect(count()).toBe("");
    });

    it("is not in explore mode once it has finished", () => {
      both();
      for (let k = 0; k < 3; k++) {
        step("next");
        pass(2.2);
      }
      press("set-j");
      expect(exploring("mtp-stepper")).toBe(false);
      expect(count()).toBe("3 / 3");
    });

    it("does not go into explore mode for a write that is refused", () => {
      const [model, rt, v] = auto();
      step("next");
      pass(1.2);
      step("next");
      pass(0.5);
      model.markSeen(rt.id("z"));
      expect(exploring("mtp-stepper")).toBe(false);
      pass(2);
      expect(v("k")).toBe(10);
    });

    it("in explore mode, › sets state 0 at once, plays step 1 and stops", () => {
      const [, , v] = both();
      step("next");
      pass(1.2);
      step("next");
      pass(1);
      slide(200);
      step("next");
      expect([v("j"), v("k")]).toEqual([0, 0]);
      expect(exploring("mtp-stepper")).toBe(false);
      expect(count()).toBe("1 / 3");
      pass(0.5);
      expect(v("j")).toBeCloseTo(2.5);
      pass(1);
      expect([v("j"), v("k")]).toEqual([5, 0]);
      expect([v("walk", "step"), v("walk", "playing")]).toEqual([1, false]);
    });

    it("in explore mode, the right arrow plays step 1 and the left arrow does nothing", () => {
      const [, , v] = both();
      step("next");
      pass(1.2);
      press("set-j");
      key("mtp-stepper", "ArrowLeft");
      expect([v("j"), count()]).toEqual([1, ""]);
      key("mtp-stepper", "ArrowRight");
      expect(v("j")).toBe(0);
      expect(count()).toBe("1 / 3");
    });

    it("a dot sets the state at its step's end worked out from state 0, whatever came before", () => {
      const [, , v] = both();
      step("next");
      pass(1.2);
      press("set-j");
      slide(300);
      dots()[1]!.click();
      expect([v("j"), v("k")]).toEqual([5, 10]);
      expect(exploring("mtp-stepper")).toBe(false);
      expect(count()).toBe("2 / 3");
      expect(states()).toEqual(["done", "now", "later"]);
      press("set-j");
      dots()[0]!.click();
      expect([v("j"), v("k")]).toEqual([5, 0]);
    });

    it("‹ jumps to the end of the step before, worked out from state 0", () => {
      const [, , v] = both();
      dots()[2]!.click();
      expect([v("j"), v("k")]).toEqual([7, 10]);
      step("prev");
      expect([v("j"), v("k")]).toEqual([5, 10]);
      step("prev");
      expect([v("j"), v("k")]).toEqual([5, 0]);
      step("prev");
      expect([v("j"), v("k")]).toEqual([0, 0]);
      expect(count()).toBe("0 / 3");
      expect(exploring("mtp-stepper")).toBe(false);
    });

    it("the Explore button stops a step that plays and goes into explore mode", () => {
      const [, , v] = both();
      step("next");
      pass(0.5);
      exploreOf("mtp-stepper").click();
      expect(exploring("mtp-stepper")).toBe(true);
      expect(v("walk", "playing")).toBe(false);
      const j = v("j");
      pass(1);
      expect(v("j")).toBe(j);
      exploreOf("mtp-stepper").click();
      expect(exploring("mtp-stepper")).toBe(true);
    });

    it("goes into explore mode when another play writes what it moves", () => {
      both();
      step("next");
      pass(1.2);
      play().click();
      expect(exploring("mtp-stepper")).toBe(true);
    });
  });

  // The author, 2026-11-12: state 0, the rest state, which plays and steppers start from and
  // jumps are worked out from, is the state after the on-views have played.
  describe("state 0, the rest state", () => {
    it("takes in what an on-view writes, which puts no control in explore mode", () => {
      const [model, rt, v] = viewed();
      model.markSeen(rt.id("v"));
      pass(1.5);
      expect(v("k")).toBe(4);
      expect(exploring("mtp-stepper")).toBe(true);
      dots()[0]!.click();
      expect([v("j"), v("k")]).toEqual([5, 4]);
      dots()[1]!.click();
      expect([v("j"), v("k")]).toEqual([5, 10]);
      dots()[0]!.click();
      expect([v("j"), v("k")]).toEqual([5, 4]);
    });

    it("is where a play starts from out of explore mode", () => {
      const [model, rt, v] = viewed();
      model.markSeen(rt.id("v"));
      pass(1.5);
      slide(800);
      play().click();
      expect([v("j"), v("k")]).toEqual([0, 4]);
      pass(2.1);
      expect(v("k")).toBeCloseTo(7.3);
    });

    it("is told by the model once every on-view of a view on the page has played", async () => {
      const [model, rt] = viewed();
      await Promise.resolve();
      expect(model.atRest()).toBe(false);
      expect(model.hasAttribute("data-mtp-rest")).toBe(false);
      let told = false;
      void model.whenRest().then(() => (told = true));
      model.markSeen(rt.id("v"));
      pass(0.5);
      await Promise.resolve();
      expect([model.atRest(), told]).toEqual([false, false]);
      pass(1);
      await Promise.resolve();
      expect([model.atRest(), told]).toEqual([true, true]);
      expect(model.hasAttribute("data-mtp-rest")).toBe(true);
    });

    // The author, 2026-11-12: a press before every on-view on the page has played hurries the
    // on-views still to play, so they all end within HURRY seconds, and then does what it does.
    describe("a press before the on-views have played", () => {
      it("plays every on-view not yet started, hurried, and then plays from state 0", () => {
        const [model, , v] = viewed();
        play().click();
        expect(v("trip", "playing")).toBe(false);
        expect(model.hasAttribute("data-mtp-rest")).toBe(false);
        pass(HURRY - 0.1);
        expect(v("k")).toBeGreaterThan(0);
        expect(v("k")).toBeLessThan(4);
        expect(v("trip", "playing")).toBe(false);
        pass(0.1);
        expect(model.hasAttribute("data-mtp-rest")).toBe(true);
        expect(v("trip", "playing")).toBe(true);
        expect([v("j"), v("k")]).toEqual([0, 4]);
        pass(1);
        expect(v("j")).toBeCloseTo(5);
        pass(1);
        expect(v("k")).toBeCloseTo(7);
      });

      it("hurries the rest of an on-view partway through", () => {
        const [model, rt, v] = viewed();
        model.markSeen(rt.id("v"));
        pass(0.5);
        expect(v("k")).toBeCloseTo(2);
        step("next");
        expect(count()).toBe("");
        pass(HURRY);
        expect(v("k")).toBe(4);
        expect(count()).toBe("1 / 3");
        expect(v("walk", "playing")).toBe(true);
      });

      it("does not play a hurried on-view again when its canvas comes into view", () => {
        const [model, rt, v] = viewed();
        dots()[0]!.click();
        pass(HURRY);
        expect([v("j"), v("k")]).toEqual([5, 4]);
        slide(200);
        model.markSeen(rt.id("v"));
        pass(1.5);
        expect(v("k")).toBe(2);
      });

      it("leaves a paused play that the on-views could have cut off to play on", () => {
        const [model, rt, v] = viewed();
        play().click();
        pass(HURRY + 0.5);
        play().click();
        model.markSeen(rt.id("v"));
        pass(0.5);
        expect(exploring("mtp-play")).toBe(false);
        play().click();
        expect(v("trip", "playing")).toBe(true);
      });

      it("does each press in order once the on-views have ended", () => {
        const [, , v] = viewed();
        step("next");
        step("next");
        pass(HURRY);
        expect(count()).toBe("2 / 3");
      });
    });

    // The author, 2026-11-12: step is -1 in state -1, 0 in state 0, and k for step k.
    it("holds every play's and stepper's step at -1 until state 0 is set, and 0 then", () => {
      const [model, rt, v] = viewed();
      expect([v("trip", "step"), v("walk", "step")]).toEqual([-1, -1]);
      model.markSeen(rt.id("v"));
      pass(0.5);
      expect([v("trip", "step"), v("walk", "step")]).toEqual([-1, -1]);
      pass(1);
      expect([v("trip", "step"), v("walk", "step")]).toEqual([0, 0]);
    });

    it("gives a play's step from 1, the step playing or just played, and 0 at step 0", () => {
      const [, , v] = both();
      expect(v("trip", "step")).toBe(0);
      play().click();
      pass(0.5);
      expect(v("trip", "step")).toBe(1);
      pass(1);
      expect(v("trip", "step")).toBe(2);
      pass(3);
      expect(v("trip", "step")).toBe(3);
      key("mtp-play", "ArrowLeft");
      key("mtp-play", "ArrowLeft");
      key("mtp-play", "ArrowLeft");
      key("mtp-play", "ArrowLeft");
      expect(line()).toBe("0 / 3");
      expect(v("trip", "step")).toBe(0);
    });

    it("is there at once on a page whose views have no on-view", async () => {
      const [model] = page(`<mtp-stepper model="m" name="walk"></mtp-stepper>`);
      await Promise.resolve();
      expect(model.atRest()).toBe(true);
      expect(model.hasAttribute("data-mtp-rest")).toBe(true);
    });

    // The author, 2026-11-12: an on-view is another writer, and only the on-views that make up
    // state 0 are exempt.
    it("does not take in an on-view that plays after state 0 is set, which is another writer", async () => {
      const [model, rt, v] = page(`<mtp-stepper model="m" name="walk"></mtp-stepper>`);
      await Promise.resolve();
      expect(model.hasAttribute("data-mtp-rest")).toBe(true);
      dots()[0]!.click();
      expect([v("j"), v("k")]).toEqual([5, 0]);
      document.body.insertAdjacentHTML("beforeend", `<mtp-canvas model="m" name="v"></mtp-canvas>`);
      model.markSeen(rt.id("v"));
      pass(0.5);
      expect(exploring("mtp-stepper")).toBe(true);
      expect(count()).toBe("");
      pass(1);
      expect(v("k")).toBe(4);
      step("next");
      expect([v("j"), v("k")]).toEqual([0, 0]);
    });
  });
});
