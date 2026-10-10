const previousFocus = new Map();
export function focusModal(id) {
  const modal = document.getElementById(id);
  if (!previousFocus.has(id)) previousFocus.set(id, document.activeElement);
  const panel = modal?.querySelector('[role="dialog"]');
  if (panel) {
    panel.tabIndex = -1;
    panel.focus({ preventScroll: true });
  }
}
export function restoreModalFocus(id) {
  previousFocus.get(id)?.focus?.({ preventScroll: true });
  previousFocus.delete(id);
}
document.addEventListener("keydown", (event) => {
  if (event.key !== "Tab") return;
  const modal = ["legal-modal", "order-result-overlay", "order-modal"]
    .map((id) => document.getElementById(id))
    .find((element) => element?.classList.contains("is-open"));
  if (!modal) return;
  const elements = [
    ...modal.querySelectorAll(
      'button, a[href], input, select, textarea, [tabindex="0"]',
    ),
  ].filter(
    (element) =>
      !element.disabled &&
      element.tabIndex >= 0 &&
      element.offsetParent !== null,
  );
  const first = elements[0],
    last = elements.at(-1);
  if (!first) {
    event.preventDefault();
    return;
  }
  if (
    event.shiftKey &&
    (document.activeElement === first ||
      !elements.includes(document.activeElement))
  ) {
    event.preventDefault();
    last.focus();
  } else if (
    !event.shiftKey &&
    (document.activeElement === last ||
      !elements.includes(document.activeElement))
  ) {
    event.preventDefault();
    first.focus();
  }
});
