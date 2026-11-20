// A canvas inside an element that the page turns or scales with CSS (mtp-fuy1). Safari 26 on iOS
// leaves the CSS transforms of the HTML elements around an SVG out of getScreenCTM (WebKit bug
// 308970), so each test also runs with a getScreenCTM that keeps only the translation.
import { afterEach, describe, expect, it } from "vitest";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

const frames = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

const real = SVGGraphicsElement.prototype.getScreenCTM;

function likeIos26(): void {
  SVGGraphicsElement.prototype.getScreenCTM = function (this: SVGGraphicsElement) {
    const m = real.call(this);
    return m && new DOMMatrix([1, 0, 0, 1, m.e, m.f]);
  };
}

afterEach(() => {
  SVGGraphicsElement.prototype.getScreenCTM = real;
});

const TURNS = [
  { name: "turned a quarter", transform: "translate(500px, 20px) rotate(90deg)" },
  { name: "turned 30 degrees and scaled", transform: "translate(200px, 30px) rotate(30deg) scale(1.5, 0.8)" },
];

async function open(name: string, transform: string): Promise<{ model: MtpModel; svg: SVGSVGElement }> {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><div style="transform-origin: 0 0; transform: ${transform}"><mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas></div>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc(name);
  const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
  svg.style.width = "400px";
  svg.style.height = "400px";
  await frames();
  return { model, svg };
}

const center = (el: Element): [number, number] => {
  const r = el.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2];
};

for (const ios of [false, true]) {
  describe(`a canvas that the page transforms with CSS${ios ? ", with getScreenCTM as on iOS 26" : ""}`, () => {
    for (const { name, transform } of TURNS) {
      it(`drags a shape to stay under the pointer when ${name}`, async () => {
        if (ios) likeIos26();
        const { model, svg } = await open("page", transform);
        const rt = model.runtime!;
        const dot = () => document.querySelector(`[data-mtp-id="${rt.id("dot")}"]`)!;
        const [x, y] = center(dot());
        dot().dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));
        const to: [number, number] = [x + 37, y - 23];
        svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: to[0], clientY: to[1], pointerId: 1 }));
        svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, clientX: to[0], clientY: to[1], pointerId: 1 }));
        await frames();
        const [cx, cy] = center(dot());
        expect(cx).toBeCloseTo(to[0], 0);
        expect(cy).toBeCloseTo(to[1], 0);
      });
    }

    // A quarter turn would swap the canvas's width and height on screen, which changes its fit
    // for another reason, so this turns it a half.
    it("fits a text in a canvas turned a half as in one that is not turned", async () => {
      if (ios) likeIos26();
      document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas><div style="transform: rotate(180deg)"><mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas></div>`;
      const model = document.querySelector("mtp-model") as MtpModel;
      model.doc = doc("fit-text");
      await frames();
      const [plain, turned] = [...document.querySelectorAll("mtp-canvas svg")].map((s) => s.getAttribute("viewBox")!.split(" ").map(Number));
      for (let i = 0; i < 4; i++) expect(turned![i]).toBeCloseTo(plain![i]!, 6);
    });
  });
}
