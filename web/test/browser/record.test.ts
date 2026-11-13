// Recording mode in a real browser (mtp-mvje.1): a 9:16 frame fitting the window, the canvas and
// the play's bars without its button, no cursor, and the play's keys from anywhere.
import { afterAll, describe, expect, it } from "vitest";
import { userEvent } from "vitest/browser";
import { type MtpModel, define } from "../../src/elements.ts";
import { record } from "../../src/record.ts";
import { doc } from "../helpers.ts";

define();

const frames = (n = 2) =>
  new Promise<void>((r) => {
    const step = (k: number) => (k <= 0 ? r() : requestAnimationFrame(() => step(k - 1)));
    step(n);
  });

afterAll(() => {
  document.documentElement.classList.remove("mtp-recording");
});

describe("recording mode", () => {
  it("shows a 9:16 frame with the canvas and the bars, no button, no cursor, and takes the keys", async () => {
    document.body.innerHTML = `<h1 id="title">a page</h1><mtp-model id="m"></mtp-model>`;
    const d = doc("record");
    const model = document.getElementById("m") as MtpModel;
    model.doc = d;
    const stage = record("m", d, { canvas: "first", play: "one" });
    await frames(3);
    const frame = stage.querySelector(".mtp-record-frame")!.getBoundingClientRect();
    expect(frame.width / frame.height).toBeCloseTo(9 / 16, 2);
    expect(frame.height).toBeLessThanOrEqual(innerHeight + 0.5);
    expect(frame.width).toBeLessThanOrEqual(innerWidth + 0.5);
    expect(getComputedStyle(document.getElementById("title")!).display).toBe("none");
    expect(getComputedStyle(stage.querySelector("mtp-play .mtp-play-button")!).display).toBe("none");
    expect(getComputedStyle(stage.querySelector("mtp-play .mtp-bars")!).display).toBe("flex");
    for (const el of [document.body, stage, stage.querySelector("mtp-canvas svg")!, stage.querySelector("mtp-play .mtp-bars")!]) {
      expect(getComputedStyle(el).cursor).toBe("none");
    }
    const canvas = stage.querySelector("mtp-canvas")!.getBoundingClientRect();
    expect(canvas.bottom).toBeLessThanOrEqual(frame.bottom);
    const rt = model.runtime!;
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(rt.value(rt.id("k"), null)).toBeCloseTo(2, 1);
    expect(stage.querySelector("mtp-play .mtp-count")!.textContent).toBe("2 / 2");
    await userEvent.keyboard(" ");
    expect(rt.value(rt.id("one"), "playing")).toBe(false);
  });
});
