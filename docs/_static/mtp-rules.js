// A click on a rule's number copies the address of the rule: the page's address with the rule's
// anchor. The address bar takes the anchor too, without a jump, and the words Link copied show
// for a moment. Where the clipboard is refused, the address bar still has the anchor to copy.
document.addEventListener("click", (event) => {
  const link = event.target.closest(".mtp-rule-link");
  if (!link) return;
  event.preventDefault();
  const anchor = link.getAttribute("href");
  history.replaceState(null, "", anchor);
  const url = `${location.origin}${location.pathname}${anchor}`;
  const show = () => {
    let note = link.parentElement.querySelector(".mtp-rule-copied");
    if (!note) {
      note = document.createElement("span");
      note.className = "mtp-rule-copied";
      note.setAttribute("role", "status");
      link.after(note);
    }
    note.textContent = "Link copied";
    clearTimeout(note.timer);
    note.timer = setTimeout(() => note.remove(), 1500);
  };
  if (navigator.clipboard) navigator.clipboard.writeText(url).then(show, () => {});
});
