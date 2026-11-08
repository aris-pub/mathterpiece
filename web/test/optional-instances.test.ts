// Motif instances that may not exist, each given a parameter that is never none (mtp-3f9l).
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";
import { draw } from "../src/svg.ts";

describe("an optional motif instance", () => {
  it("is drawn while its exists-when holds, with its parameters", () => {
    const rt = load("optional-instances");
    const radii = () => [...draw(rt, rt.id("v")).querySelectorAll("circle")].map((c) => c.getAttribute("r"));
    expect(radii()).toEqual(["2", "2", "1"]);
    rt.write(rt.id("n"), null, 5);
    expect(radii()).toEqual(["2", "2", "1", "1", "1"]);
    rt.write(rt.id("n"), null, 1);
    expect(radii()).toEqual(["2"]);
  });
});
