import {
  openOrderModal,
  closeOrderModal,
  closeOrderResultModal,
} from "./order.js?v=20261010-nearest-price-hint";
import {
  openPrivacyPolicy,
  openConsentText,
  closeLegalModal,
} from "./legal.js";
import {
  loadProducts,
  scrollProducts,
} from "./catalog.js?v=20261010-nearest-price-hint";
import { loadLocations, loadFooterContacts } from "./contacts.js";
import { loadShowcase } from "./showcase.js?v=20261010-nearest-price-hint";
import {
  toggleMobileMenu,
  closeMobileMenu,
  resizeShowcaseForContent,
  initRevealAnimations,
} from "./layout.js?v=20261010-nearest-price-hint";

// Only template event handlers are exposed; module state stays private.
Object.assign(window, {
  openOrderModal,
  closeOrderModal,
  closeOrderResultModal,
  openPrivacyPolicy,
  openConsentText,
  closeLegalModal,
  scrollProducts,
  toggleMobileMenu,
  closeMobileMenu,
});
document
  .getElementById("price-categories")
  .addEventListener("click", (event) => {
    const button = event.target.closest("button[data-product-id]");
    if (button && !button.disabled) openOrderModal(button.dataset.productId);
  });
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (document.getElementById("legal-modal").classList.contains("is-open"))
    return closeLegalModal();
  if (
    document
      .getElementById("order-result-overlay")
      .classList.contains("is-open")
  )
    return closeOrderResultModal();
  if (document.getElementById("order-modal").classList.contains("is-open"))
    return closeOrderModal();
  closeMobileMenu();
});
loadLocations(loadShowcase, resizeShowcaseForContent);
loadProducts();
loadFooterContacts();
initRevealAnimations();
