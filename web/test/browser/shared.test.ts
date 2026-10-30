// The shared cases that need a page: CSS resolves what the runtime leaves to it (color mixes).
import { describe, expect, it } from "vitest";
import { define, type MtpModel } from "../../src/elements.ts";
import { type Case, cases, run } from "../shared-cases.ts";

define();

describe("cases both runtimes agree on, on a page", () => {
  it.each(cases().filter((c) => c.page).map((c) => [c.name, c] as [string, Case]))("%s", async (_, c) => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = c.doc;
    await new Promise((r) => setTimeout(r, 0));
    expect(run(model.runtime!, c)).toEqual([]);
  });
});
