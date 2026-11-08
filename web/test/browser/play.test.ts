// A play's bar with a real pointer and real layout (docs/reference.md, "Controls"; mtp-33xt).
import { describe, expect, it } from "vitest";
import { cdp, userEvent } from "vitest/browser";
import { type MtpModel, define } from "../../src/elements.ts";
import type { Runtime } from "../../src/runtime.ts";
import { doc } from "../helpers.ts";

define();

const session = cdp();

const frames = (n = 2) =>
  new Promise<void>((r) => {
    const step = (k: number) => (k <= 0 ? r() : requestAnimationFrame(() => step(k - 1)));
    step(n);
  });

async function open(body = `<mtp-play model="m" name="tour" style="width: 420px"></mtp-play>`): Promise<{ rt: Runtime; v: (n: string, a?: string) => unknown }> {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("bar");
  const rt = model.runtime!;
  await frames();
  return { rt, v: (n, a) => rt.value(rt.id(n), a ?? null) };
}

const bars = () => [...document.querySelectorAll("mtp-play .mtp-bar")] as HTMLElement[];

// A point along bar k, u of the way across it, on the screen.
function along(k: number, u: number): [number, number] {
  const r = bars()[k]!.getBoundingClientRect();
  return [r.left + u * r.width, r.top + r.height / 2];
}

async function mouse(type: "mousePressed" | "mouseMoved" | "mouseReleased", [x, y]: [number, number]): Promise<void> {
  await session.send("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mouseReleased" ? 0 : 1, clickCount: 1 });
}

describe("a play's bar", () => {
  it("draws each step's bar as wide as its duration", async () => {
    await open();
    const [a, b] = bars().map((bar) => bar.getBoundingClientRect().width);
    expect(b! / a!).toBeCloseTo(3, 1);
  });

  it("jumps to the start of a step the mouse taps", async () => {
    const { v } = await open();
    await mouse("mousePressed", along(1, 0.6));
    await mouse("mouseReleased", along(1, 0.6));
    expect(v("k")).toBe(2);
    expect(document.querySelector("mtp-play .mtp-now")!.textContent).toBe("2 / 2");
  });

  it("scrubs as the mouse drags along the bars", async () => {
    const { v } = await open();
    await mouse("mousePressed", along(0, 0.1));
    await mouse("mouseMoved", along(0, 0.3));
    await mouse("mouseMoved", along(0, 0.5));
    expect(v("k")).toBeCloseTo(1, 1);
    await mouse("mouseMoved", along(1, 0.5));
    expect(v("k")).toBeCloseTo(3, 1);
    await mouse("mouseReleased", along(1, 0.5));
    expect(v("k")).toBeCloseTo(3, 1);
  });

  it("takes a press a little above the thin bars", async () => {
    const { v } = await open();
    const [x, y] = along(1, 0.5);
    await mouse("mousePressed", [x, y - 12]);
    await mouse("mouseReleased", [x, y - 12]);
    expect(v("k")).toBe(2);
  });

  it("shows a focus ring on the button and the bars when reached by the keyboard", async () => {
    await open(`<button id="before">before</button><mtp-play model="m" name="tour" style="width: 420px"></mtp-play>`);
    (document.getElementById("before") as HTMLButtonElement).focus();
    const ring = (el: Element) => getComputedStyle(el).outlineStyle;
    await userEvent.tab();
    const button = document.querySelector("mtp-play .mtp-play-button")!;
    expect(document.activeElement).toBe(button);
    expect(ring(button)).toBe("solid");
    await userEvent.tab();
    const track = document.querySelector("mtp-play .mtp-bars")!;
    expect(document.activeElement).toBe(track);
    expect(ring(track)).toBe("solid");
  });

  it("plays and steps with real keys, on the bars and from anywhere on a page with one play", async () => {
    const { v } = await open();
    (document.querySelector("mtp-play .mtp-bars") as HTMLElement).focus();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(v("k")).toBe(2);
    (document.activeElement as HTMLElement).blur();
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(v("k")).toBe(0);
    await userEvent.keyboard(" ");
    expect(v("tour", "playing")).toBe(true);
    await userEvent.keyboard(" ");
    expect(v("tour", "playing")).toBe(false);
  });

  it("presses the play button once on Space when it has focus", async () => {
    const { v } = await open();
    (document.querySelector("mtp-play .mtp-play-button") as HTMLElement).focus();
    await userEvent.keyboard(" ");
    expect(v("tour", "playing")).toBe(true);
  });

  it("gives the play button and the bars touch targets at least 44 pixels tall", async () => {
    await open();
    const button = document.querySelector("mtp-play .mtp-play-button")!;
    const track = document.querySelector("mtp-play .mtp-bars")!;
    for (const el of [button, track]) {
      const r = el.getBoundingClientRect();
      const reach = getComputedStyle(el, "::after");
      const above = -parseFloat(reach.top);
      expect(r.height + 2 * above).toBeGreaterThanOrEqual(44);
    }
  });
});
