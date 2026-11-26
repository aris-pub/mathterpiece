// Conformance tests of the rule select-options (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import type { Attribute, Type } from "../../../src/doc.ts";
import { control, free, input, mtpc, page, str, valueOf, variable } from "./shared.ts";

type Option = { value: Attribute; label?: Attribute; "label-tex"?: true };

function select(type: Type, value: unknown, options: Option[], as = "buttons") {
  const obj = control("select", "pick", { target: [0, null], as, options, attrs: { label: str("mean") } });
  return page(`<mtp-select model="m" name="pick"></mtp-select>`, mtpc(variable("mean", type, value), obj));
}

const MEANS: Option[] = [
  { value: str("arithmetic"), label: str("\\frac{a+b}{2}"), "label-tex": true },
  { value: str("geometric"), label: str("the geometric mean") },
  { value: str("harmonic") },
];

const option = (i: number) => input("mtp-select", `option-${i}`);
const checked = () => [1, 2, 3].map((i) => option(i).getAttribute("aria-checked") === "true");

describe("rule select-options: a select's options, each a value with an optional label", () => {
  it("shows each option's label, or its value when it has none", () => {
    select("string", "arithmetic", MEANS);
    expect(option(1).querySelector('[role="img"]')!.getAttribute("aria-label")).toBe("\\frac{a+b}{2}");
    expect(option(2).textContent).toBe("the geometric mean");
    expect(option(3).textContent).toBe("harmonic");
  });

  it("writes the chosen option to the target at once", () => {
    const model = select("string", "arithmetic", MEANS);
    expect(checked()).toEqual([true, false, false]);
    option(3).click();
    expect(valueOf(model, "mean")).toBe("harmonic");
    expect(checked()).toEqual([false, false, true]);
    expect(model.scheduler!.busy()).toBe(false);
  });

  it("shows no option chosen when the target holds no option's value", () => {
    const model = select("string", "median", MEANS);
    expect(checked()).toEqual([false, false, false]);
    expect(document.querySelector("mtp-select .mtp-error")).toBe(null);
    model.runtime!.write(0, null, "geometric");
    expect(checked()).toEqual([false, true, false]);
  });

  it("takes options of any type, and shows a number's value", () => {
    const model = select("int", 3, [{ value: free("int", 3) }, { value: free("int", 4) }, { value: free("int", 6) }]);
    expect([1, 2, 3].map((i) => option(i).textContent)).toEqual(["3", "4", "6"]);
    option(3).click();
    expect(valueOf(model, "mean")).toBe(6);
  });
});
