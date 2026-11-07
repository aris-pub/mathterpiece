// The inventory page (mtp-4he1): every component live with the HTML that places it, the
// listeners, and the tokens with controls that restyle the components on the page.
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { define, type MtpModel } from "../src/elements.ts";
import { inventory } from "../src/inventory.ts";
import { source } from "./helpers.ts";

define();

function show(): HTMLElement {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><div id="inv"></div>`;
  const text = source("inventory");
  (document.getElementById("m") as MtpModel).doc = JSON.parse(text) as Doc;
  const root = document.getElementById("inv")!;
  inventory(root, text, { model: "m", id: "dial", file: "dial.mtpc" });
  return root;
}

const snippets = (root: HTMLElement) => [...root.querySelectorAll(".mtp-inv-snippet pre")].map((p) => p.textContent);
const heads = (root: HTMLElement) => [...root.querySelectorAll(".mtp-inv-entry h3")].map((h) => h.textContent);

beforeEach(() => document.documentElement.removeAttribute("style"));

describe("the inventory", () => {
  it("starts with the lines that load the runtime and the model, in both forms", () => {
    const [script, file, block] = snippets(show());
    expect(script).toBe('<script type="module" src="mathterpiece.js"></script>');
    expect(file).toBe('<mtp-model id="dial" src="dial.mtpc"></mtp-model>');
    expect(block).toContain('<mtp-model id="dial" src="#dial-data"></mtp-model>');
    expect(block).toContain('<script type="application/json" id="dial-data">');
  });

  it("lists every component and listener in the order the source declares them", () => {
    expect(heads(show())).toEqual(["canvas v", "slider size", "on-drag c", "on-click c", "readout says", "on-view v"]);
  });

  it("gives each component the line that places it, with the id the author sees", () => {
    const lines = snippets(show()).slice(3);
    expect(lines).toEqual([
      '<mtp-canvas model="dial" name="v"></mtp-canvas>',
      '<mtp-slider model="dial" name="size"></mtp-slider>',
      '<mtp-readout model="dial" name="says"></mtp-readout>',
    ]);
  });

  it("shows each component live, reading the page's own model", () => {
    const root = show();
    expect(root.querySelector('mtp-canvas[model="m"][name="v"] svg')).not.toBeNull();
    expect(root.querySelector('mtp-readout[model="m"][name="says"]')!.textContent).toBe("k = 1.0");
  });

  it("says what each listener does, and gives it no line to place", () => {
    const texts = [...show().querySelectorAll(".mtp-inv-entry")]
      .filter((e) => e.querySelector("h3")!.textContent!.startsWith("on-"))
      .map((e) => [e.querySelector("p:not(.mtp-inv-doc)")!.textContent, e.querySelector(".mtp-inv-snippet")]);
    expect(texts).toEqual([
      ["The reader drags c, which moves c.pos.", null],
      ["When the reader clicks c, it plays an animation that moves k.", null],
      ["When the canvas v first comes into view, it plays an animation that moves k.", null],
    ]);
  });

  it("copies the block with the compiled model as written, so nothing in it ends the script", () => {
    const root = show();
    let copied = "";
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: (t: string) => ((copied = t), Promise.resolve()) },
      configurable: true,
    });
    (root.querySelectorAll(".mtp-inv-snippet button")[2] as HTMLButtonElement).click();
    const json = copied.split('id="dial-data">')[1]!.replace(/<\/script>$/, "");
    expect(json).toBe(source("inventory").trim().replace(/<\//g, "<\\/"));
  });
});

describe("its tokens", () => {
  const row = (root: HTMLElement, name: string) =>
    [...root.querySelectorAll(".mtp-inv-tokens tr")].find((r) => r.firstElementChild!.firstChild!.textContent === name)!;

  it("restyles a color on the page from its control, and resets it", () => {
    const root = show();
    const input = row(root, "ink").querySelector('input[type="color"]') as HTMLInputElement;
    expect(input.value).toBe("#204060");
    input.value = "#ff0000";
    input.dispatchEvent(new Event("input"));
    expect(document.documentElement.style.getPropertyValue("--mtp-ink")).toBe("#ff0000");
    (row(root, "ink").querySelector("button") as HTMLButtonElement).click();
    expect(document.documentElement.style.getPropertyValue("--mtp-ink")).toBe("");
  });

  it("gives a color with a dark value a control for each mode", () => {
    const root = show();
    const [lit, dim] = [...row(root, "glow").querySelectorAll('input[type="color"]')] as HTMLInputElement[];
    expect([lit!.value, dim!.value]).toEqual(["#204060", "#e0d0c0"]);
    dim!.value = "#ff0000";
    dim!.dispatchEvent(new Event("input"));
    expect(document.documentElement.style.getPropertyValue("--mtp-glow")).toBe("light-dark(#204060, #ff0000)");
    (row(root, "glow").querySelector("button") as HTMLButtonElement).click();
    expect(dim!.value).toBe("#e0d0c0");
  });

  it("restyles each part of a font", () => {
    const root = show();
    const [family, style, weight] = row(root, "note").querySelectorAll("input, select") as unknown as HTMLInputElement[];
    expect([family!.value, style!.value, weight!.value]).toEqual(["Georgia, serif", "italic", "400"]);
    family!.value = "Courier";
    family!.dispatchEvent(new Event("input"));
    expect(document.documentElement.style.getPropertyValue("--mtp-note-family")).toBe("Courier");
  });
});

describe("docstrings", () => {
  const docOf = (root: HTMLElement, head: string) =>
    [...root.querySelectorAll(".mtp-inv-entry")]
      .find((e) => e.querySelector("h3")!.textContent === head)
      ?.querySelector(".mtp-inv-doc")?.textContent ?? null;

  it("shows each component's and listener's doc under its name, and none where there is none", () => {
    const root = show();
    expect(docOf(root, "slider size")).toBe("Sets the radius.");
    expect(docOf(root, "on-drag c")).toBe("Moves the circle.");
    expect(docOf(root, "canvas v")).toBeNull();
  });

  it("shows a token's doc with its name", () => {
    const row = [...show().querySelectorAll(".mtp-inv-tokens tr")].find(
      (r) => r.firstElementChild!.firstChild!.textContent === "ink",
    )!;
    expect(row.querySelector(".mtp-inv-doc")!.textContent).toBe("The color of the circle.");
  });
});

describe("a formula in the inventory", () => {
  it("lists its displays and the listeners on its terms", () => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><div id="inv"></div>`;
    const text = source("formula");
    (document.getElementById("m") as MtpModel).doc = JSON.parse(text) as Doc;
    const root = document.getElementById("inv")!;
    inventory(root, text, { model: "m", id: "f", file: "f.mtpc" });
    expect(heads(root)).toEqual(["display d", "display di", "on-click f.a", "on-enter f.a", "on-leave f.a"]);
    expect(snippets(root)).toContain('<mtp-display model="f" name="d"></mtp-display>');
    expect(root.textContent).toContain("it acts on f.a in every display that shows its formula");
  });
});
