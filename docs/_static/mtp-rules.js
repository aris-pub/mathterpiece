// The button in each rule's head copies the address of the rule: the page's address with the
// rule's anchor. Where the clipboard is refused, the address bar takes the anchor instead, so the
// reader can copy it from there.
document.addEventListener("click", (event) => {
  const button = event.target.closest(".mtp-rule-copy");
  if (!button) return;
  const url = `${location.origin}${location.pathname}#${button.dataset.anchor}`;
  const done = () => {
    const text = button.querySelector(".mtp-copy-text");
    button.classList.add("mtp-copied");
    button.setAttribute("aria-label", "Link copied");
    if (text) text.textContent = "Copied";
    setTimeout(() => {
      button.classList.remove("mtp-copied");
      button.setAttribute("aria-label", "Copy the link to this rule");
      if (text) text.textContent = "Copy link";
    }, 1500);
  };
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(done, () => { location.hash = button.dataset.anchor; });
  } else {
    location.hash = button.dataset.anchor;
  }
});
