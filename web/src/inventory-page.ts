// The script of the page mtp build writes: it fills each <div data-mtp-inventory> with the
// inventory of the model it names, read from that model's block in the page.
import { inventory } from "./inventory.ts";

for (const root of document.querySelectorAll<HTMLElement>("[data-mtp-inventory]")) {
  const model = root.dataset.mtpInventory!;
  const src = document.getElementById(model)?.getAttribute("src") ?? "";
  const block = src.startsWith("#") ? document.getElementById(src.slice(1)) : null;
  if (!block) continue;
  inventory(root, block.textContent ?? "", { model, id: model, file: root.dataset.file ?? `${model}.mtpc` });
}
