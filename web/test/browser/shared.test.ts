// The shared cases, run in a real browser through <mtp-model>.
import { describe, expect, it } from "vitest";
import { type MtpModel, define } from "../../src/elements.ts";
import { type Case, cases, run } from "../shared-cases.ts";

define();

describe("the shared cases, on a page", () => {
  it.each(cases().map((c) => [c.name, c] as [string, Case]))("%s", (_, c) => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = c.doc;
    expect(run(model.runtime!, c)).toEqual([]);
  });
});
