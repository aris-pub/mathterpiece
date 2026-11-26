// What the conformance tests of docs/spec/compiler-runtime.md share.
import { type Doc } from "../../../src/doc.ts";
import { type MtpModel, define, frames } from "../../../src/elements.ts";

define();

frames.request = () => {};

export const FIGURE = `(real k 1 (>= 0) (<= 10))
(scene s (circle c (r k)))
(canvas v s)
(readout r f'k = {k:.1f}')
`;

/** A page with one model and the given elements, loaded from a .mtpc. */

export function page(body: string, doc: Doc): MtpModel {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  return model;
}

export const errorIn = (selector: string) => document.querySelector(`${selector} .mtp-error`)?.textContent ?? null;
