// <dialog> für jsdom (kennt showModal und close nicht), so nah am Browser wie nötig: öffnet,
// fokussiert das erste Bedienelement, schliesst mit Esc und meldet das Schliessen mit "close".

export function installDialog() {
  const proto = HTMLDialogElement.prototype;
  if (typeof proto.showModal === "function") return;

  proto.showModal = function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
    if (!this.dataset.escape) {
      this.dataset.escape = "1";
      this.addEventListener("keydown", (event) => {
        if (event.key === "Escape") this.close();
      });
    }
    this.querySelector<HTMLElement>(
      "button, a[href], input, select, textarea",
    )?.focus();
  };
  proto.close = function (this: HTMLDialogElement) {
    if (!this.hasAttribute("open")) return;
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}
