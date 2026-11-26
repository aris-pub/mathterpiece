// Conformance tests of the rule multi-select (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import { control, input, mtpc, page, str, valueOf, variable } from "./shared.ts";

const OPTIONS = ["circle", "ellipse", "parabola", "hyperbola"].map((v) => ({ value: str(v) }));

function multi(list: string[]) {
  const obj = control("multi-select", "shown", { target: [0, null], as: "buttons", options: OPTIONS, attrs: { label: str("curves") } });
  return page(`<mtp-multi-select model="m" name="shown"></mtp-multi-select>`, mtpc(variable("curves", { list: "string" }, list), obj));
}

const option = (i: number) => input("mtp-multi-select", `option-${i}`);
const pressed = () => [1, 2, 3, 4].map((i) => option(i).getAttribute("aria-pressed") === "true");

describe("rule multi-select: choosing an option adds it to the list, and choosing it again removes it", () => {
  it("adds an option and removes it again", () => {
    const model = multi(["circle"]);
    option(3).click();
    expect(valueOf(model, "curves")).toEqual(["circle", "parabola"]);
    option(1).click();
    expect(valueOf(model, "curves")).toEqual(["parabola"]);
  });

  it("keeps the options' order in the source, whatever order the reader chooses in", () => {
    const model = multi([]);
    option(4).click();
    option(2).click();
    option(1).click();
    expect(valueOf(model, "curves")).toEqual(["circle", "ellipse", "hyperbola"]);
  });

  it("may hold any number of options, none included", () => {
    const model = multi(["ellipse"]);
    option(2).click();
    expect(valueOf(model, "curves")).toEqual([]);
    for (const i of [1, 2, 3, 4]) option(i).click();
    expect(valueOf(model, "curves")).toEqual(["circle", "ellipse", "parabola", "hyperbola"]);
  });

  it("shows a value in the list that is no option as nothing chosen, never as an error", () => {
    multi(["line", "parabola"]);
    expect(pressed()).toEqual([false, false, true, false]);
    expect(document.querySelector("mtp-multi-select .mtp-error")).toBe(null);
  });
});
