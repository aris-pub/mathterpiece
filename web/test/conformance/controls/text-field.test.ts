// Conformance tests of the rule text-field (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import type { Type } from "../../../src/doc.ts";
import { control, input, key, mtpc, page, str, typeInto, valueOf, variable } from "./shared.ts";

function field(type: Type = "string") {
  const obj = control("text-field", "t", { target: [0, null], attrs: { label: str("name") } });
  return page(`<mtp-text-field model="m" name="t"></mtp-text-field>`, mtpc(variable("word", type, "circle"), obj));
}

const box = () => input("mtp-text-field", "box") as HTMLInputElement;
const outlined = () => document.querySelector("mtp-text-field .mtp-refused") !== null;

describe("rule text-field: a text field writes its string when committed", () => {
  it("shows its target's string in a text box", () => {
    const model = field();
    expect(box().value).toBe("circle");
    expect(box().type).toBe("text");
    model.runtime!.write(0, null, "ellipse");
    expect(box().value).toBe("ellipse");
  });

  it("writes the typed string only when it is committed: with Enter, or by leaving the field", () => {
    const model = field();
    typeInto(box(), "square");
    expect(valueOf(model, "word")).toBe("circle");
    key(box(), "Enter");
    expect(valueOf(model, "word")).toBe("square");
    typeInto(box(), "line");
    box().dispatchEvent(new Event("blur"));
    expect(valueOf(model, "word")).toBe("line");
    expect(outlined()).toBe(false);
  });

  it("keeps what the reader types while another writer changes the target", () => {
    const model = field();
    typeInto(box(), "squ");
    model.runtime!.write(0, null, "ellipse");
    expect(box().value).toBe("squ");
  });

  it("does not write a string that breaks the target's conditions, and outlines the box in red", () => {
    const model = field({ refine: "string", constraints: [["one-of", ["circle", "square"]]] });
    typeInto(box(), "blob");
    key(box(), "Enter");
    expect(valueOf(model, "word")).toBe("circle");
    expect(box().value).toBe("circle");
    expect(outlined()).toBe(true);
    expect(document.querySelector("mtp-text-field [aria-live]")!.textContent).toContain("blob");
  });
});
