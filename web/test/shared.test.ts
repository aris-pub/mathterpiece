import { describe, expect, it } from "vitest";
import { Runtime } from "../src/runtime.ts";
import { type Case, cases, run } from "./shared-cases.ts";

describe("cases both runtimes agree on", () => {
  const all = cases();

  it("has cases", () => {
    expect(all.length).toBeGreaterThan(0);
  });

  it.each(all.filter((c) => !c.page).map((c) => [c.name, c] as [string, Case]))("%s", (_, c) => {
    expect(run(new Runtime(c.doc), c)).toEqual([]);
  });

  it("catches a wrong expectation", () => {
    const c = all.find((x) => x.name === "bools")!;
    const broken: Case = { ...c, steps: [["expect", "n", 2]] };
    expect(run(new Runtime(c.doc), broken)).toEqual(["n: expected 2, got 1"]);
  });
});
