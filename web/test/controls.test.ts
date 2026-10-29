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
  it("shows its label and range, and writes its target while dragged", async () => {
    const { read } = await page("golden-tour", `<mtp-slider model="m" name="angle"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(document.querySelector("mtp-slider")?.textContent).toContain("angle");
    expect([input.min, input.max, input.step]).toEqual(["80", "180", "any"]);
    input.value = "120";
    input.dispatchEvent(new Event("input"));
    expect(read("sunflower.angle")).toBe(120);
    expect(text("°")).toBe("120.0°");
  });

  it("steps by whole numbers for an int target", async () => {
    const { read } = await page("interactive", `<mtp-slider model="m" name="multiplier"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(input.step).toBe("1");
    input.value = "7";
    input.dispatchEvent(new Event("input"));
    expect(read("table.m")).toBe(7);
  });

  it("follows values that something else moved", async () => {
    const { anim } = await page(
      "golden-tour",
      `<mtp-slider model="m" name="angle"></mtp-slider><mtp-steps model="m" name="jump"></mtp-steps>`,
    );
    (document.querySelectorAll("mtp-steps button")[2] as HTMLButtonElement).click();
    anim.tick(5);
    expect((document.querySelector("mtp-slider input") as HTMLInputElement).value).toBe("144");
  });
});

describe("<mtp-button>", () => {
  it("goes to its state", async () => {
    const { read } = await page(
      "interactive",
      `<mtp-slider model="m" name="multiplier"></mtp-slider><mtp-button model="m" name="reset"></mtp-button>`,
    );
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "9";
    input.dispatchEvent(new Event("input"));
    const button = document.querySelector("mtp-button button") as HTMLButtonElement;
    expect(button.textContent).toBe("back to 2");
    button.click();
    expect(read("table.m")).toBe(2);
  });
});

describe("<mtp-steps>", () => {
  it("has a button per state, pressed while its state holds", async () => {
    const { anim } = await page("golden-tour", `<mtp-steps model="m" name="jump"></mtp-steps>`);
    const buttons = [...document.querySelectorAll("mtp-steps button")] as HTMLButtonElement[];
    expect(buttons.map((b) => b.textContent)).toEqual(["quarter", "third", "two-fifths", "golden"]);
    expect(buttons.map((b) => b.getAttribute("aria-pressed"))).toEqual(["true", "false", "false", "false"]);
    buttons[3]!.click();
    anim.tick(0.75);
    expect(buttons.map((b) => b.getAttribute("aria-pressed"))).toEqual(["false", "false", "false", "false"]);
    anim.tick(1);
    expect(buttons.map((b) => b.getAttribute("aria-pressed"))).toEqual(["false", "false", "false", "true"]);
  });
});

describe("<mtp-play>", () => {
  it("plays the tour, and any other input cancels it", async () => {
    const { read, anim } = await page(
      "golden-tour",
      `<mtp-play model="m" name="tour"></mtp-play><mtp-slider model="m" name="angle"></mtp-slider>`,
    );
    const play = document.querySelector("mtp-play button") as HTMLButtonElement;
    expect(play.textContent).toBe("play");
    play.click();
    anim.tick(1.5 + 2.5);
    expect(read("sunflower.angle")).toBeCloseTo(120);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "100";
    input.dispatchEvent(new Event("input"));
    anim.tick(10);
    expect(read("sunflower.angle")).toBe(100);
  });
});

describe("errors", () => {
  it("says when a control is missing or of another kind", async () => {
    await page("golden-tour", `<mtp-slider model="m" name="nope"></mtp-slider><mtp-button model="m" name="angle"></mtp-button>`);
    expect(document.querySelector("mtp-slider")?.textContent).toMatch(/no slider named nope/);
    expect(document.querySelector("mtp-button")?.textContent).toMatch(/angle is a slider, not a button/);
  });
});
