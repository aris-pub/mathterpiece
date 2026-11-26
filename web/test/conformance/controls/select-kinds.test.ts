// Conformance tests of the rule select-kinds (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import { control, hasInput, input, key, mtpc, page, str, valueOf, variable } from "./shared.ts";

const OPTIONS = [{ value: str("circle") }, { value: str("ellipse") }, { value: str("parabola") }];

function select(as: string) {
  const obj = control("select", "pick", { target: [0, null], as, options: OPTIONS, attrs: { label: str("curve") } });
  return page(`<mtp-select model="m" name="pick"></mtp-select>`, mtpc(variable("curve", "string", "ellipse"), obj));
}

function multi(as: string) {
  const obj = control("multi-select", "pick", { target: [0, null], as, options: OPTIONS, attrs: { label: str("curves") } });
  return page(`<mtp-multi-select model="m" name="pick"></mtp-multi-select>`, mtpc(variable("curves", { list: "string" }, ["circle"]), obj));
}

const listbox = (tag: string) => document.querySelector(`${tag} [role="listbox"]`) as HTMLElement;

describe("rule select-kinds: a select is drawn as a menu, a row of buttons or radio buttons", () => {
  it("'menu' is a button showing the chosen option that opens the list of all of them", () => {
    const model = select("menu");
    const menu = input("mtp-select", "menu");
    expect(menu.textContent).toContain("ellipse");
    expect(menu.getAttribute("aria-haspopup")).toBe("listbox");
    expect(menu.getAttribute("aria-expanded")).toBe("false");
    expect(listbox("mtp-select").hidden).toBe(true);
    menu.click();
    expect(menu.getAttribute("aria-expanded")).toBe("true");
    expect(listbox("mtp-select").hidden).toBe(false);
    const options = listbox("mtp-select").querySelectorAll('[role="option"]');
    expect([...options].map((o) => o.textContent)).toEqual(["circle", "ellipse", "parabola"]);
    expect(options[1]!.getAttribute("aria-selected")).toBe("true");
    input("mtp-select", "option-3").click();
    expect(valueOf(model, "curve")).toBe("parabola");
    expect(listbox("mtp-select").hidden).toBe(true);
    expect(menu.textContent).toContain("parabola");
  });

  it("'menu' opens and chooses from the keyboard", () => {
    const model = select("menu");
    const menu = input("mtp-select", "menu");
    key(menu, "ArrowDown");
    expect(listbox("mtp-select").hidden).toBe(false);
    key(listbox("mtp-select"), "ArrowDown");
    key(listbox("mtp-select"), "Enter");
    expect(valueOf(model, "curve")).toBe("parabola");
    expect(listbox("mtp-select").hidden).toBe(true);
    key(menu, "Enter");
    key(listbox("mtp-select"), "Escape");
    expect(listbox("mtp-select").hidden).toBe(true);
    expect(valueOf(model, "curve")).toBe("parabola");
  });

  it("'buttons' is a row of connected buttons, a radio group", () => {
    const model = select("buttons");
    expect(document.querySelector('mtp-select [role="radiogroup"]')).toBeTruthy();
    expect(input("mtp-select", "option-2").getAttribute("aria-checked")).toBe("true");
    input("mtp-select", "option-1").click();
    expect(valueOf(model, "curve")).toBe("circle");
    key(input("mtp-select", "option-1"), "ArrowRight");
    expect(valueOf(model, "curve")).toBe("ellipse");
    expect(hasInput("mtp-select", "menu")).toBe(false);
  });

  it("'radio' is one option per line with a round mark", () => {
    const model = select("radio");
    const radio = input("mtp-select", "option-3") as HTMLInputElement;
    expect(radio.type).toBe("radio");
    expect((input("mtp-select", "option-2") as HTMLInputElement).checked).toBe(true);
    radio.click();
    expect(valueOf(model, "curve")).toBe("parabola");
  });
});

describe("rule select-kinds: a multi-select is drawn as a menu, a row of buttons or checkboxes", () => {
  it("'menu' opens a list in which several options may be chosen", () => {
    const model = multi("menu");
    const menu = input("mtp-multi-select", "menu");
    expect(menu.textContent).toContain("circle");
    menu.click();
    expect(listbox("mtp-multi-select").getAttribute("aria-multiselectable")).toBe("true");
    input("mtp-multi-select", "option-3").click();
    expect(valueOf(model, "curves")).toEqual(["circle", "parabola"]);
    expect(input("mtp-multi-select", "option-3").getAttribute("aria-selected")).toBe("true");
  });

  it("'buttons' is a row of buttons that each stay pressed", () => {
    const model = multi("buttons");
    const b = input("mtp-multi-select", "option-2");
    expect(b.getAttribute("aria-pressed")).toBe("false");
    b.click();
    expect(valueOf(model, "curves")).toEqual(["circle", "ellipse"]);
    expect(b.getAttribute("aria-pressed")).toBe("true");
  });

  it("'checkbox' is one checkbox per option", () => {
    const model = multi("checkbox");
    const box = input("mtp-multi-select", "option-1") as HTMLInputElement;
    expect(box.type).toBe("checkbox");
    expect(box.checked).toBe(true);
    box.click();
    expect(valueOf(model, "curves")).toEqual([]);
  });
});
