// Recording mode (mtp-mvje.1): one canvas and a play's bars on a 9:16 page, nothing else.
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { define, type MtpModel } from "../src/elements.ts";
import { fill } from "../src/inventory-page.ts";
import { record, recordingOf } from "../src/record.ts";
import { doc, source } from "./helpers.ts";

define();

beforeEach(() => {
  document.documentElement.className = "";
  document.body.innerHTML = "";
});

describe("recording mode", () => {
  it("is asked for with ?record, the first canvas and play by default", () => {
    const d = doc("record");
    expect(recordingOf("", d)).toBe(null);
    expect(recordingOf("?example=x", d)).toBe(null);
    expect(recordingOf("?record", d)).toEqual({ canvas: "first", play: "one" });
    expect(recordingOf("?record&canvas=second&play=two", d)).toEqual({ canvas: "second", play: "two" });
    expect(recordingOf("?record&canvas=nothing", d)).toBe(null);
  });

  it("shows the canvas and the play, and marks the page as recording", () => {
    document.body.innerHTML = `<h1>title</h1><mtp-model id="m"></mtp-model>`;
    const d = doc("record");
    (document.getElementById("m") as MtpModel).doc = d;
    const stage = record("m", d, { canvas: "first", play: "one" });
    expect(document.documentElement.classList.contains("mtp-recording")).toBe(true);
    expect([...stage.querySelectorAll("mtp-canvas, mtp-play")].map((e) => `${e.tagName} ${e.getAttribute("name")}`)).toEqual([
      "MTP-CANVAS first",
      "MTP-PLAY one",
    ]);
    expect(stage.querySelector("mtp-canvas svg")).not.toBe(null);
    expect(stage.querySelector("mtp-play .mtp-now")!.textContent).toBe("2 steps");
  });

  it("takes the place of the inventory on the page mtp build writes", () => {
    const text = source("record");
    document.body.innerHTML = `<h1>record</h1><mtp-model id="record" src="#record-data"></mtp-model>
      <div data-mtp-inventory="record" data-file="record.mtpc"></div>
      <script type="application/json" id="record-data">${text}</script>`;
    (document.getElementById("record") as MtpModel).doc = JSON.parse(text) as Doc;
    fill("?record&play=two");
    expect(document.querySelector("[data-mtp-inventory]")!.children.length).toBe(0);
    expect(document.querySelectorAll("mtp-play").length).toBe(1);
    expect(document.querySelector(".mtp-record mtp-play")!.getAttribute("name")).toBe("two");
  });
});
