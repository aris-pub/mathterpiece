// The standard library's marks (docs/reference.md, "The standard library"). The author,
// 2026-11-06: every mark is visible with no arguments, or it is a bug.
import { describe, expect, it } from "vitest";
import { type MtpModel, define } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

function open(): Runtime {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="v"></mtp-canvas>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("stdlib-marks");
  return model.runtime!;
}

// What an instance draws: the elements of the shapes inside it.
function drawn(rt: Runtime, instance: number): SVGElement[] {
  const inside = (id: number) => {
    for (let i: number | null = id; i !== null; i = rt.parent(i)) if (i === instance) return true;
    return false;
  };
  return [...document.querySelectorAll<SVGElement>("mtp-canvas [data-mtp-id]")].filter((el) =>
    inside(Number(el.getAttribute("data-mtp-id"))),
  );
}

function visible(el: SVGElement): boolean {
  if (el.tagName === "text" && !el.textContent?.trim()) return false;
  const shows = (paint: string, opacity: string | null) => paint !== "" && paint !== "none" && Number(opacity ?? 1) > 0;
  return (
    Number(el.getAttribute("opacity") ?? 1) > 0 &&
    (shows(el.style.stroke, el.getAttribute("stroke-opacity")) || shows(el.style.fill, el.getAttribute("fill-opacity")))
  );
}

describe("marks", () => {
  it("are each visible with no arguments", () => {
    const rt = open();
    const marks = rt.objects.flatMap((o, i) => (o.kind === "instance" && o.name?.startsWith("mark-") ? [i] : []));
    expect(marks.length).toBe(4);
    for (const m of marks) expect(drawn(rt, m).some(visible), rt.objects[m]!.name!).toBe(true);
  });

  it("mark a right angle with a square, and any other with an arc", () => {
    const rt = open();
    const tags = (name: string) => drawn(rt, rt.id(name)).map((el) => el.tagName);
    expect(tags("mark-angle-mark")).toContain("polyline");
    expect(tags("mark-angle-mark")).not.toContain("path");
    expect(tags("sharp")).toContain("path");
    expect(tags("sharp")).not.toContain("polyline");
  });
});
