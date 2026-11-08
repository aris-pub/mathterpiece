// The script of the page mtp build writes: it fills each <div data-mtp-inventory> with the
// inventory of the model it names, read from that model's block in the page. With ?record in the
// page's address, it shows the first model's figure in recording mode instead (record.ts).
import type { Doc } from "./doc.ts";
import { inventory } from "./inventory.ts";
import { record, recordingOf } from "./record.ts";

export function fill(search: string): void {
  for (const root of document.querySelectorAll<HTMLElement>("[data-mtp-inventory]")) {
    const model = root.dataset.mtpInventory!;
    const src = document.getElementById(model)?.getAttribute("src") ?? "";
    const block = src.startsWith("#") ? document.getElementById(src.slice(1)) : null;
    if (!block) continue;
    const text = block.textContent ?? "";
    const rec = recordingOf(search, JSON.parse(text) as Doc);
    if (rec) {
      record(model, JSON.parse(text) as Doc, rec);
      return;
    }
    inventory(root, text, { model, id: model, file: root.dataset.file ?? `${model}.mtpc` });
  }
}

fill(location.search);
