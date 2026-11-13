// Plays and steppers whose step is read from the scene, and the listeners on their inputs
// (mtp-wjtd; docs/reference.md, "Controls"; docs/page-interface.md).
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

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

function page(body: string, file: Doc = doc("plays")): [MtpModel, Runtime, (name: string, attr?: string) => unknown] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = file;
  const rt = model.runtime!;
  return [model, rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

beforeEach(() => {
  queued = [];
  clock = 0;
});

const input = (el: Element, name: string) => el.querySelector(`[data-mtp-input="${name}"]`) as HTMLElement;
const click = (name: string) => (document.querySelector(`mtp-button[name="${name}"] button`) as HTMLButtonElement).click();
const key = (target: EventTarget, k: string) => {
  const event = new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event.defaultPrevented;
};
const BUTTONS = ["go", "set-two", "set-three", "set-four"].map((b) => `<mtp-button model="m" name="${b}"></mtp-button>`).join("");

describe("a play", () => {
  const tour = (extra = "") => page(`<mtp-play model="m" name="tour"></mtp-play>${BUTTONS}${extra}`);
  const el = () => document.querySelector("mtp-play") as HTMLElement;
  const button = () => input(el(), "button") as HTMLButtonElement;
  const bars = () => [...el().querySelectorAll(".mtp-bar")] as HTMLElement[];
  const fills = () => bars().map((b) => Number(b.style.getPropertyValue("--u")));
  const track = () => el().querySelector(".mtp-bars") as HTMLElement;
  const count = () => el().querySelector(".mtp-count")?.textContent ?? null;

  // happy-dom lays nothing out: the first bar takes 100 pixels and the second, three times as
  // long, 300, after a 4 pixel gap.
  function lay(): void {
    const rect = (left: number, width: number) => () => ({ left, width, right: left + width, top: 0, bottom: 4, height: 4, x: left, y: 0, toJSON: () => ({}) }) as DOMRect;
    const [a, b] = bars();
    a!.getBoundingClientRect = rect(0, 100);
    b!.getBoundingClientRect = rect(104, 300);
    track().getBoundingClientRect = rect(0, 404);
  }
  const pointer = (type: string, x: number) => track().dispatchEvent(new PointerEvent(type, { clientX: x, clientY: 2, bubbles: true, pointerId: 1, button: 0 }));
  const tap = (x: number) => {
    pointer("pointerdown", x);
    pointer("pointerup", x);
  };

  describe("reads its step from the scene", () => {
    it("is at step 0, in explore mode, when the scene is in none of its states", () => {
      const [, , v] = tour();
      expect(v("tour", "step")).toBe(0);
      expect(el().getAttribute("data-mtp-step")).toBe("0");
      expect(el().hasAttribute("data-mtp-exploring")).toBe(true);
    });

    it("is at the highest step whose state the scene is in, whoever wrote it", () => {
      const [, , v] = tour();
      click("set-two");
      expect(v("tour", "step")).toBe(1);
      expect(el().getAttribute("data-mtp-step")).toBe("1");
      expect(el().hasAttribute("data-mtp-exploring")).toBe(false);
      click("set-four");
      expect(v("tour", "step")).toBe(2);
      click("set-three");
      expect(v("tour", "step")).toBe(0);
      expect(el().hasAttribute("data-mtp-exploring")).toBe(true);
    });

    it("matches a real within about a millionth of its size", () => {
      const [, rt, v] = tour();
      rt.write(rt.id("k"), null, 4 * (1 + 1e-8));
      expect(v("tour", "step")).toBe(2);
      rt.write(rt.id("k"), null, 4.001);
      expect(v("tour", "step")).toBe(0);
    });

    it("is the step playing while it plays, and the step paused in while paused", () => {
      const [, , v] = tour();
      button().click();
      pass(0.1);
      pass(0.5);
      expect(v("tour", "step")).toBe(1);
      expect(el().hasAttribute("data-mtp-playing")).toBe(true);
      pass(1);
      expect(v("tour", "step")).toBe(2);
      button().click();
      expect(el().hasAttribute("data-mtp-playing")).toBe(false);
      expect(v("tour", "playing")).toBe(false);
      expect(v("tour", "step")).toBe(2);
      expect(el().hasAttribute("data-mtp-exploring")).toBe(false);
    });
  });

  describe("its button", () => {
    it("in explore mode sets state 0 and plays every step", () => {
      const [, , v] = tour();
      button().click();
      expect(v("tour", "playing")).toBe(true);
      pass(0.1);
      pass(0.5);
      expect(v("k")).toBeCloseTo(1);
      expect(fills()[0]).toBeCloseTo(0.5);
      pass(4);
      expect(v("k")).toBe(4);
      expect(v("tour", "playing")).toBe(false);
      expect(fills()).toEqual([1, 1]);
    });

    it("pauses a running play, and resumes it", () => {
      const [, , v] = tour();
      button().click();
      pass(0.1);
      pass(0.5);
      button().click();
      const paused = v("k");
      pass(1);
      expect(v("k")).toBe(paused);
      button().click();
      expect(v("tour", "playing")).toBe(true);
      pass(4);
      expect(v("k")).toBe(4);
    });

    it("at step k sets state k and plays the steps after it", () => {
      const [, , v] = tour();
      click("set-two");
      button().click();
      pass(0.1);
      // Step 2 moves k from 2 to 4 in 3 seconds.
      pass(1.5);
      expect(v("k")).toBeCloseTo(3);
    });

    it("at the last step shows a replay icon, and plays every step again from state 0", () => {
      const [, , v] = tour();
      click("set-four");
      expect(button().classList.contains("mtp-replay")).toBe(true);
      button().click();
      expect(button().classList.contains("mtp-replay")).toBe(false);
      pass(0.1);
      pass(0.5);
      // Step 1 moves k from where it is, 4, to 2.
      expect(v("k")).toBeCloseTo(3);
      expect(v("tour", "step")).toBe(1);
    });

    it("sets the from of a move of step 1 at once in state 0", () => {
      const [, , v] = page(`<mtp-play model="m" name="froms"></mtp-play>`);
      input(document.querySelector("mtp-play")!, "button").click();
      expect(v("j")).toBe(5);
      pass(0.1);
      pass(0.5);
      expect(v("j")).toBeCloseTo(5.5);
    });

    it("plays across a rest between steps, and stays at the step before during it", () => {
      const [, , v] = page(`<mtp-play model="m" name="rested"></mtp-play>`);
      input(document.querySelector("mtp-play")!, "button").click();
      pass(0.1);
      pass(1.5);
      expect(v("k")).toBe(2);
      expect(v("rested", "step")).toBe(1);
      expect(v("rested", "playing")).toBe(true);
      pass(1);
      expect(v("k")).toBeCloseTo(2 + 2 * (0.5 / 3));
      expect(v("rested", "step")).toBe(2);
    });
  });

  describe("its bars", () => {
    it("a tap on step i's bar sets state i - 1 and plays steps i to N", () => {
      const [, , v] = tour();
      lay();
      tap(250);
      expect(v("k")).toBe(2);
      expect(v("tour", "playing")).toBe(true);
      expect(v("tour", "step")).toBe(2);
      pass(0.1);
      pass(1.5);
      expect(v("k")).toBeCloseTo(3);
      pass(2);
      expect(v("k")).toBe(4);
    });

    it("a tap on the first bar sets state 0, whatever came before, and plays from step 1", () => {
      const [, , v] = tour();
      lay();
      click("set-three");
      tap(50);
      pass(0.1);
      pass(0.5);
      // Step 1 moves k from 3 to 2 in a second.
      expect(v("k")).toBeCloseTo(2.5);
    });

    it("a drag along them sets the state at each point, and on release the play is paused there", () => {
      const [, , v] = tour();
      lay();
      pointer("pointerdown", 10);
      pointer("pointermove", 50);
      expect(v("k")).toBeCloseTo(1);
      pointer("pointermove", 254);
      expect(v("k")).toBeCloseTo(3);
      expect(fills()[1]).toBeCloseTo(0.5);
      pointer("pointermove", 50);
      expect(v("k")).toBeCloseTo(1);
      pointer("pointermove", 254);
      pointer("pointerup", 254);
      expect(v("k")).toBeCloseTo(3);
      expect(v("tour", "playing")).toBe(false);
      expect(v("tour", "step")).toBe(2);
      // The button resumes it.
      button().click();
      pass(0.1);
      pass(2);
      expect(v("k")).toBe(4);
    });

    it("a drag is a gesture: a button pressed while it is held writes none of what it drags", () => {
      const [, , v] = tour();
      lay();
      pointer("pointerdown", 10);
      pointer("pointermove", 50);
      click("go");
      pass(0.5);
      expect(v("k")).toBeCloseTo(1);
      pointer("pointerup", 50);
    });

    it("show a knob, an empty ring at the left end in explore mode", () => {
      tour();
      const knob = el().querySelector(".mtp-knob") as HTMLElement;
      expect(knob).not.toBeNull();
      expect(knob.classList.contains("mtp-empty")).toBe(true);
      click("set-two");
      expect(knob.classList.contains("mtp-empty")).toBe(false);
    });

    it("are dimmed under a pill reading Exploring in explore mode, and nothing under them", () => {
      tour();
      const pill = el().querySelector(".mtp-exploring") as HTMLElement;
      expect(pill.textContent).toBe("Exploring");
      expect(pill.hidden).toBe(false);
      click("set-two");
      expect(pill.hidden).toBe(true);
      expect(el().querySelector(".mtp-now")).toBeNull();
    });
  });

  describe("its count", () => {
    it("with (buttons true) sits after the bars, and reads – / N in explore mode", () => {
      tour();
      expect(count()).toBe("– / 2");
      click("set-two");
      expect(count()).toBe("1 / 2");
    });

    it("without (buttons true) is not there", () => {
      page(`<mtp-play model="m" name="whole"></mtp-play>`);
      expect(document.querySelector("mtp-play .mtp-count")).toBeNull();
      expect(document.querySelectorAll("mtp-play .mtp-bar").length).toBe(1);
    });
  });

  describe("keys", () => {
    it("Space is the button", () => {
      const [, , v] = tour();
      expect(key(track(), " ")).toBe(true);
      expect(v("tour", "playing")).toBe(true);
      key(track(), " ");
      expect(v("tour", "playing")).toBe(false);
    });

    it("at step k the right arrow is a tap on bar k + 1, and the left arrow one on bar k", () => {
      const [, , v] = tour();
      key(track(), "ArrowRight");
      // From explore mode, step 0: a tap on bar 1.
      expect(v("tour", "playing")).toBe(true);
      expect(v("tour", "step")).toBe(1);
      key(track(), "ArrowRight");
      expect(v("k")).toBe(2);
      expect(v("tour", "step")).toBe(2);
      pass(0.1);
      pass(0.6);
      key(track(), "ArrowLeft");
      // Step 2 again, from state 1.
      expect(v("k")).toBe(2);
      expect(v("tour", "playing")).toBe(true);
    });

    it("are turned off where they would name a step that does not exist", () => {
      const [, , v] = tour();
      key(track(), "ArrowLeft");
      expect(v("tour", "playing")).toBe(false);
      expect(v("k")).toBe(0);
      click("set-four");
      key(track(), "ArrowRight");
      expect(v("tour", "playing")).toBe(false);
    });

    it("without (buttons true) there are no arrow keys", () => {
      const [, , v] = page(`<mtp-play model="m" name="whole"></mtp-play>`);
      const bar = document.querySelector("mtp-play .mtp-bars")!;
      expect(key(bar, "ArrowRight")).toBe(false);
      expect(v("whole", "playing")).toBe(false);
      expect(key(bar, " ")).toBe(true);
      expect(v("whole", "playing")).toBe(true);
    });

    it("work from anywhere on a page with one play, but not from a text field", () => {
      const [, , v] = page(`<input id="t"><mtp-play model="m" name="tour"></mtp-play>`);
      key(document.body, " ");
      expect(v("tour", "playing")).toBe(true);
      const field = document.getElementById("t") as HTMLInputElement;
      field.focus();
      expect(key(field, " ")).toBe(false);
      expect(v("tour", "playing")).toBe(true);
    });
  });

  describe("on the page", () => {
    it("names its inputs: the button and one bar per step", () => {
      tour();
      expect(button().tagName).toBe("BUTTON");
      expect(input(el(), "bar-1")).toBe(bars()[0]);
      expect(input(el(), "bar-2")).toBe(bars()[1]);
    });

    it("fires mtp-state on each change of its page state, and only then", () => {
      tour();
      let told = 0;
      el().addEventListener("mtp-state", () => told++);
      click("set-two");
      expect(told).toBe(1);
      click("set-two");
      expect(told).toBe(1);
      button().click();
      expect(told).toBe(2);
    });

    it("marks itself inactive while its (active bool) does not hold", () => {
      const [, rt] = page(`<mtp-play model="m" name="off"></mtp-play>`);
      const off = document.querySelector("mtp-play") as HTMLElement;
      expect(off.hasAttribute("data-mtp-inactive")).toBe(true);
      rt.write(rt.id("on"), null, true);
      expect(off.hasAttribute("data-mtp-inactive")).toBe(false);
    });
  });

  describe("copies", () => {
    it("each copy has its own page state, and the step read from the scene is the same", () => {
      const [, , v] = page(`<mtp-play model="m" name="tour"></mtp-play><mtp-play model="m" name="tour"></mtp-play>${BUTTONS}`);
      const [a, b] = [...document.querySelectorAll("mtp-play")] as HTMLElement[];
      input(a!, "button").click();
      pass(0.1);
      pass(0.3);
      expect(a!.hasAttribute("data-mtp-playing")).toBe(true);
      expect(b!.hasAttribute("data-mtp-playing")).toBe(false);
      expect(v("tour", "playing")).toBe(true);
      pass(5);
      expect([a!.getAttribute("data-mtp-step"), b!.getAttribute("data-mtp-step")]).toEqual(["2", "2"]);
    });
  });

  it("a paused play stays at its step until another writer writes what it moves", () => {
    const [, , v] = tour();
    button().click();
    pass(0.1);
    pass(0.5);
    button().click();
    expect(v("tour", "step")).toBe(1);
    click("go");
    pass(0.1);
    expect(v("tour", "step")).toBe(0);
    button().click();
    expect(v("tour", "playing")).toBe(true);
    pass(0.1);
    pass(0.5);
    expect(v("tour", "step")).toBe(1);
  });
});

describe("a stepper", () => {
  const hints = () => page(`<mtp-stepper model="m" name="hints"></mtp-stepper>${BUTTONS}`);
  const el = () => document.querySelector("mtp-stepper") as HTMLElement;
  const back = () => input(el(), "back") as HTMLButtonElement;
  const next = () => input(el(), "next") as HTMLButtonElement;
  const dot = (i: number) => input(el(), `dot-${i}`) as HTMLButtonElement;
  const count = () => el().querySelector(".mtp-count")!.textContent;

  it("dot i sets state i - 1, plays step i and stops at its end", () => {
    const [, , v] = hints();
    dot(2).click();
    expect(v("k")).toBe(2);
    expect(v("hints", "playing")).toBe(true);
    expect(v("hints", "step")).toBe(2);
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(3);
    pass(1);
    expect(v("k")).toBe(4);
    expect(v("hints", "playing")).toBe(false);
    expect(v("hints", "step")).toBe(2);
    expect(v("j")).toBe(0);
  });

  it("› at step k is dot k + 1, and ‹ is dot k, which plays step k again", () => {
    const [, , v] = hints();
    next().click();
    pass(0.1);
    pass(1.1);
    expect([v("k"), v("hints", "step")]).toEqual([2, 1]);
    next().click();
    pass(0.1);
    pass(1.1);
    expect([v("k"), v("hints", "step")]).toEqual([4, 2]);
    back().click();
    expect(v("k")).toBe(2);
    expect(v("hints", "playing")).toBe(true);
    pass(0.1);
    pass(1.1);
    expect(v("k")).toBe(4);
  });

  it("› while a step plays sets the state at its end and plays the next", () => {
    const [, , v] = hints();
    next().click();
    pass(0.1);
    pass(0.3);
    next().click();
    expect(v("k")).toBe(2);
    expect(v("hints", "step")).toBe(2);
  });

  it("turns off › at the last step and ‹ at step 0", () => {
    const [, rt] = hints();
    expect(back().disabled).toBe(true);
    expect(next().disabled).toBe(false);
    rt.write(rt.id("k"), null, 4);
    rt.write(rt.id("j"), null, 1);
    expect(next().disabled).toBe(true);
    expect(back().disabled).toBe(false);
  });

  it("is in explore mode when the scene is in none of its states, its count reading – / N", () => {
    const [, , v] = hints();
    expect(v("hints", "step")).toBe(0);
    expect(el().hasAttribute("data-mtp-exploring")).toBe(true);
    expect(count()).toBe("– / 3");
    click("set-two");
    expect(v("hints", "step")).toBe(1);
    expect(el().hasAttribute("data-mtp-exploring")).toBe(false);
    expect(count()).toBe("1 / 3");
  });

  it("names its inputs: back, next and one dot per step", () => {
    hints();
    expect(back().getAttribute("aria-label")).toBe("previous step");
    expect(next().getAttribute("aria-label")).toBe("next step");
    expect(dot(3).getAttribute("aria-label")).toBe("step 3");
  });

  it("the right and left arrows are › and ‹", () => {
    const [, , v] = hints();
    key(el(), "ArrowRight");
    pass(0.1);
    pass(1.1);
    expect(v("hints", "step")).toBe(1);
    // Step 1 again, from state 0, where k stays.
    key(el(), "ArrowLeft");
    expect(v("k")).toBe(2);
    expect(v("hints", "playing")).toBe(true);
  });
});
