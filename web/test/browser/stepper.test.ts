// A stepper with real layout and a real pointer (docs/reference.md, "Controls"; the author,
// 2026-11-10).
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

async function open(body = `<mtp-stepper model="m" name="hints"></mtp-stepper>`): Promise<{ rt: Runtime; v: (n: string, a?: string) => unknown }> {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("plays");
  const rt = model.runtime!;
  await frames();
  return { rt, v: (n, a) => rt.value(rt.id(n), a ?? null) };
}

const dots = () => [...document.querySelectorAll("mtp-stepper .mtp-dot")] as HTMLElement[];
const box = (el: Element) => el.getBoundingClientRect();

async function tap([x, y]: [number, number]): Promise<void> {
  for (const type of ["mousePressed", "mouseReleased"] as const)
    await session.send("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mousePressed" ? 1 : 0, clickCount: 1 });
}

describe("a stepper", () => {
  it("draws round buttons either side of a row of small dots", async () => {
    await open();
    const back = document.querySelector("mtp-stepper .mtp-back")!;
    expect([box(back).width, box(back).height]).toEqual([32, 32]);
    expect(getComputedStyle(back).borderRadius).toBe("50%");
    const [a, b] = dots();
    expect([box(a!).width, box(a!).height]).toEqual([10, 10]);
    expect(box(b!).left - box(a!).right).toBeGreaterThanOrEqual(10);
    expect(getComputedStyle(back).opacity).toBe("0.5");
  });

  // The author, 2026-11-13: the dots are never narrower than the Exploring pill, spread to its
  // width when there are few, the pill sits on them in explore mode, and the stepper is as wide in
  // every state.
  it("spreads few dots to the width of the Exploring pill, which sits on them, at one width in every state", async () => {
    const { rt } = await open();
    const el = document.querySelector("mtp-stepper") as HTMLElement;
    const pill = el.querySelector(".mtp-exploring") as HTMLElement;
    const row = el.querySelector(".mtp-dots") as HTMLElement;
    const [first, , last] = dots();
    const p = box(pill);
    expect(box(row).width).toBeGreaterThanOrEqual(p.width - 0.5);
    expect(Math.abs(box(first!).left - box(row).left)).toBeLessThan(1);
    expect(Math.abs(box(last!).right - box(row).right)).toBeLessThan(1);
    expect(Math.abs((p.left + p.right) / 2 - (box(row).left + box(row).right) / 2)).toBeLessThan(1);
    expect(getComputedStyle(pill).visibility).toBe("visible");
    expect(getComputedStyle(first!).opacity).toBe("0.45");
    const wide = box(el).width;
    rt.write(rt.id("k"), null, 2);
    await frames();
    expect(getComputedStyle(pill).visibility).toBe("hidden");
    expect(box(el).width).toBe(wide);
    rt.write(rt.id("k"), null, 4);
    rt.write(rt.id("j"), null, 1);
    await frames();
    expect(box(el).width).toBe(wide);
  });

  it("takes a tap a little outside a dot", async () => {
    const { v } = await open();
    const r = box(dots()[1]!);
    await tap([r.left + 5, r.top - 6]);
    expect(v("hints", "step")).toBe(2);
  });

  it("rings the current step's dot, and draws passed ones solid and later ones pale", async () => {
    // The page has no BRAIID tokens, so it sets the controls' colors itself.
    await open(`<mtp-stepper model="m" name="hints" style="--mtp-control-rest: #234; --mtp-control-active: #234"></mtp-stepper>`);
    dots()[1]!.click();
    await frames();
    const [done, now, later] = dots().map((d) => getComputedStyle(d));
    expect(now!.boxShadow).not.toBe("none");
    expect(done!.boxShadow).toBe("none");
    expect(done!.backgroundColor).toBe(now!.backgroundColor);
    expect(later!.backgroundColor).not.toBe(now!.backgroundColor);
  });

  it("shows a focus ring when reached by the keyboard", async () => {
    await open(`<button id="before">before</button><mtp-stepper model="m" name="hints"></mtp-stepper>`);
    (document.getElementById("before") as HTMLButtonElement).focus();
    await userEvent.tab();
    expect(document.activeElement).toBe(dots()[0]);
    expect(getComputedStyle(dots()[0]!).outlineStyle).toBe("solid");
  });
});
