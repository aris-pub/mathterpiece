// Shows a glossary term and its definition in a box over each link to it. The definition comes
// from the link's title, which is removed so that the browser shows no tooltip of its own.
(() => {
  const box = document.createElement("div");
  box.className = "mtp-term-tip";
  box.id = "mtp-term-tip";
  box.setAttribute("role", "tooltip");
  box.hidden = true;
  document.body.append(box);

  const links = document.querySelectorAll('a.reference[title] > .std-term');
  for (const span of links) {
    const a = span.parentElement;
    const title = a.getAttribute("title");
    const cut = title.indexOf(": ");
    a.dataset.term = title.slice(0, cut);
    a.dataset.definition = title.slice(cut + 2);
    a.removeAttribute("title");
    a.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") show(a); });
    a.addEventListener("pointerleave", hide);
    a.addEventListener("focus", () => show(a));
    a.addEventListener("blur", hide);
  }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
  window.addEventListener("scroll", hide, { passive: true });

  function show(a) {
    box.replaceChildren();
    const term = document.createElement("strong");
    term.textContent = a.dataset.term;
    box.append(term, " ", a.dataset.definition);
    box.hidden = false;
    a.setAttribute("aria-describedby", box.id);
    const r = a.getBoundingClientRect();
    const w = box.offsetWidth, h = box.offsetHeight, gap = 6, edge = 8;
    const left = Math.min(Math.max(edge, r.left), window.innerWidth - w - edge);
    const below = r.bottom + gap + h <= window.innerHeight - edge;
    const top = below ? r.bottom + gap : r.top - gap - h;
    box.style.left = `${left + window.scrollX}px`;
    box.style.top = `${top + window.scrollY}px`;
  }

  function hide() {
    box.hidden = true;
    for (const a of document.querySelectorAll("[aria-describedby='mtp-term-tip']")) {
      a.removeAttribute("aria-describedby");
    }
  }
})();
