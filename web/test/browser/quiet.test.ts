// Quiet mode in a real browser (docs/reference.md, "Quiet and live views"; mtp-16z): where the
// switch sits, its target, the keyboard, its colors, and the controls folding and unfolding.
import { describe, expect, it } from "vitest";
import { userEvent } from "vitest/browser";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function open(style = ""): { canvas: HTMLElement; hand: HTMLButtonElement; slider: HTMLElement } {
  document.documentElement.setAttribute("style", style);
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="left" style="display: block; width: 300px"></mtp-canvas><mtp-slider model="m" name="sl"></mtp-slider>`;
  (document.querySelector("mtp-model") as MtpModel).doc = doc("quiet");
  const canvas = document.querySelector("mtp-canvas") as HTMLElement;
  return { canvas, hand: canvas.querySelector(".mtp-switch") as HTMLButtonElement, slider: document.querySelector("mtp-slider") as HTMLElement };
}

describe("quiet mode", () => {
  it("puts the switch in the view's top right corner", () => {
    const { canvas, hand } = open();
    const [c, h] = [canvas.getBoundingClientRect(), hand.getBoundingClientRect()];
    expect(c.right - h.right).toBeLessThan(12);
    expect(h.top - c.top).toBeLessThan(12);
  });

  it("gives the switch a target 44 pixels across", () => {
    const { hand } = open();
    const r = hand.getBoundingClientRect();
    const [x, y] = [r.left + r.width / 2, r.top + r.height / 2];
    for (const [dx, dy] of [[-21, 0], [21, 0], [0, -21], [0, 21]] as const) {
      expect(hand.contains(document.elementFromPoint(x + dx, y + dy))).toBe(true);
    }
  });

  it("works by keyboard: Enter makes the view live and keeps the focus, Escape puts it back", async () => {
    const { canvas, hand } = open();
    await userEvent.tab();
    expect(document.activeElement).toBe(hand);
    await userEvent.keyboard("{Enter}");
    expect(canvas.dataset.mtpMode).toBe("live");
    expect(document.activeElement).toBe(hand);
    await userEvent.keyboard("{Escape}");
    expect(canvas.dataset.mtpMode).toBe("quiet");
  });

  it("draws the switch in the controls' rest color, and their in-use color when focused", async () => {
    const { hand } = open("--mtp-control-rest: rgb(138, 143, 152); --mtp-control-active: rgb(31, 42, 68)");
    expect(getComputedStyle(hand).color).toBe("rgb(138, 143, 152)");
    await userEvent.tab();
    // Past the color's transition.
    await wait(200);
    expect(getComputedStyle(hand).color).toBe("rgb(31, 42, 68)");
    document.documentElement.removeAttribute("style");
  });

  it("unfolds the view's controls when it goes live, and folds them when it goes quiet", async () => {
    const { hand, slider } = open();
    expect(getComputedStyle(slider).display).toBe("none");
    hand.click();
    expect(getComputedStyle(slider).display).not.toBe("none");
    await wait(450);
    expect(slider.hasAttribute("data-mtp-folding")).toBe(false);
    expect(slider.getBoundingClientRect().height).toBeGreaterThan(10);
    hand.click();
    expect(getComputedStyle(slider).display).not.toBe("none");
    await wait(450);
    expect(getComputedStyle(slider).display).toBe("none");
  });
});
