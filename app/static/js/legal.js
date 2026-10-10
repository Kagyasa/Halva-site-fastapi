import { fetchJSON, currentCheckout } from "./api.js";
import { focusModal, restoreModalFocus } from "./dialogs.js";
let legalRequest = 0;

function formatLegalPublishedAt(value) {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

async function openLegalDocument({
  url,
  fallbackTitle,
  documentLabel,
  cachedDocument = null,
}) {
  const modal = document.getElementById("legal-modal");
  const title = document.getElementById("legal-modal-title");
  const meta = document.getElementById("legal-modal-meta");
  const text = document.getElementById("legal-modal-text");

  if (!modal || !title || !meta || !text) return;

  const generation = ++legalRequest;
  title.textContent = fallbackTitle;
  meta.textContent = "";
  text.className = "legal-modal-text";
  text.textContent = "Загрузка документа…";

  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  focusModal("legal-modal");

  try {
    const data = cachedDocument || (await fetchJSON(url));
    if (generation !== legalRequest || !modal.classList.contains("is-open"))
      return;

    title.textContent = String(data.title || fallbackTitle);
    text.textContent = String(
      data.text || "Текст документа пока не опубликован.",
    );

    const metaParts = [];

    if (data.version) {
      metaParts.push(`Версия ${String(data.version)}`);
    }

    const publishedAt = formatLegalPublishedAt(data.published_at);
    if (publishedAt) {
      metaParts.push(`опубликовано ${publishedAt}`);
    }

    meta.textContent = metaParts.join(" · ");
  } catch (error) {
    if (generation !== legalRequest) return;
    console.error(`Не удалось загрузить ${documentLabel}:`, error);
    meta.textContent = "";
    text.className = "legal-modal-text is-error";
    text.textContent =
      "Не удалось загрузить документ. Попробуйте ещё раз позже.";
  }
}

export function openPrivacyPolicy() {
  return openLegalDocument({
    url: "/api/legal/privacy-policy/",
    fallbackTitle: "Политика обработки персональных данных",
    documentLabel: "политику обработки персональных данных",
    cachedDocument: document
      .getElementById("order-modal")
      ?.classList.contains("is-open")
      ? currentCheckout()?.privacy_policy
      : null,
  });
}

export function openConsentText() {
  return openLegalDocument({
    url: "/api/legal/consent/",
    fallbackTitle: "Согласие на обработку персональных данных",
    documentLabel: "текст согласия",
    cachedDocument: document
      .getElementById("order-modal")
      ?.classList.contains("is-open")
      ? currentCheckout()?.consent_text
      : null,
  });
}

export function closeLegalModal() {
  const modal = document.getElementById("legal-modal");
  if (!modal) return;

  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");

  const orderModalOpen = document
    .getElementById("order-modal")
    ?.classList.contains("is-open");

  if (!orderModalOpen) {
    document.body.classList.remove("modal-open");
  }

  legalRequest += 1;
  restoreModalFocus("legal-modal");
}

document.getElementById("legal-modal")?.addEventListener("click", (event) => {
  if (event.target.id === "legal-modal") {
    closeLegalModal();
  }
});
