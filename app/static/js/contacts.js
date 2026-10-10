import { getCheckout } from "./api.js";
import { getSafeHttpUrl, formatContactPhone, phoneHref } from "./utils.js";
function contactDisplayUrl(url) {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/\/$/, "");
    return `${parsed.hostname}${path}`;
  } catch (_) {
    return url;
  }
}

export async function loadFooterContacts() {
  const links = Array.from(document.querySelectorAll("[data-contact-type]"));

  links.forEach((link) => {
    link.dataset.contactReady = "false";
    link.addEventListener("click", (event) => {
      if (link.dataset.contactReady !== "true") {
        event.preventDefault();
      }
    });
  });

  try {
    const response = await fetch("/api/contacts/");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const contacts = await response.json();
    const byType = new Map();
    contacts.forEach((contact) => {
      const type = String(contact.type || "").toLowerCase();
      if (!byType.has(type)) byType.set(type, contact);
    });

    links.forEach((link) => {
      const type = String(link.dataset.contactType || "").toLowerCase();
      const contact = byType.get(type);

      const safeContactUrl = getSafeHttpUrl(contact?.value, {
        allowSameOrigin: false,
      });

      if (!safeContactUrl) {
        link.dataset.contactReady = "false";
        link.removeAttribute("href");
        link.removeAttribute("target");
        link.removeAttribute("rel");
        return;
      }

      link.href = safeContactUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.dataset.contactReady = "true";

      const label =
        contact.title || link.textContent.trim() || type.toUpperCase();
      link.textContent = `${label} · ${contactDisplayUrl(safeContactUrl)}`;
      link.setAttribute("aria-label", `${label} — открыть в новом окне`);
    });
  } catch (error) {
    console.error("Ошибка загрузки контактов футера:", error);
  }
}

let locations = [];
function renderHours(target, location) {
  const weekday = document.createElement("span");
  weekday.textContent = `Будни: ${location.weekday_hours}`;
  const weekend = document.createElement("span");
  weekend.textContent = `Выходные: ${location.weekend_hours}`;
  target.replaceChildren(weekday, document.createElement("br"), weekend);
}
export function switchMobileContact(id, button) {
  const location = locations.find((item) => item.id === id);
  if (!location) return;
  document.getElementById("mobile-contact-title").textContent =
    location.address || location.name;
  renderHours(document.getElementById("mobile-contact-hours"), location);
  const phone = document.getElementById("mobile-contact-phone");
  phone.textContent = formatContactPhone(location.phone);
  phone.href = phoneHref(location.phone);
  document.querySelectorAll(".contact-mobile-tab").forEach((tab) => {
    tab.classList.toggle("active", tab === button);
    tab.setAttribute("aria-selected", String(tab === button));
  });
}
export async function loadLocations(onShowcaseSelect, onLayoutChange) {
  try {
    locations = (await getCheckout()).locations;
    const desktop = document.querySelector(".contacts-grid");
    const mobile = document.querySelector(".contacts-mobile-tabs");
    const showcases = document.querySelector(".showcase-tabs");
    desktop.replaceChildren();
    mobile.replaceChildren();
    showcases.replaceChildren();
    locations.forEach((location, index) => {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = `contact-mobile-tab${index ? "" : " active"}`;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(index === 0));
      const pin = document.createElement("img");
      pin.src = "/static/images/pin.png";
      pin.alt = "";
      const label = document.createElement("span");
      label.textContent = location.address || location.name;
      tab.append(pin, label);
      tab.addEventListener("click", () =>
        switchMobileContact(location.id, tab),
      );
      mobile.appendChild(tab);
      const showcase = tab.cloneNode(true);
      showcase.className = `showcase-tab${index ? "" : " active"}`;
      showcase.removeAttribute("role");
      showcase.removeAttribute("aria-selected");
      showcase.dataset.locationId = location.id;
      showcase.addEventListener("click", () =>
        onShowcaseSelect(location.id, showcase),
      );
      showcases.appendChild(showcase);
      const card = document.createElement("article");
      card.className = "contact-card";
      const title = document.createElement("h3");
      title.textContent = location.address || location.name;
      const divider = document.createElement("div");
      divider.className = "contact-divider";
      const hours = document.createElement("p");
      hours.className = "contact-hours";
      renderHours(hours, location);
      const phone = document.createElement("a");
      phone.className = "contact-phone";
      phone.textContent = formatContactPhone(location.phone);
      phone.href = phoneHref(location.phone);
      const note = document.createElement("p");
      note.className = "contact-note";
      note.textContent = document.getElementById(
        "mobile-contact-note",
      ).textContent;
      card.append(title, divider, hours, phone, note);
      desktop.appendChild(card);
    });
    const first = locations[0];
    if (first) {
      switchMobileContact(first.id, mobile.firstElementChild);
      await onShowcaseSelect(first.id, showcases.firstElementChild);
      document
        .querySelectorAll(".header-phone, .mobile-menu-phone")
        .forEach((link) => {
          link.href = phoneHref(first.phone);
          link.textContent = formatContactPhone(first.phone);
        });
      renderHours(document.querySelector(".footer-hours"), first);
    } else {
      document.querySelector(".contacts-mobile-card").hidden = true;
      document.getElementById("showcase-desserts").textContent =
        "Активные точки пока не опубликованы.";
    }
    const footer = document.querySelector(".footer-contacts-lines");
    footer.replaceChildren(
      ...locations.flatMap((location, index) => {
        const text = document.createTextNode(
          `${location.address || location.name} · ${formatContactPhone(location.phone)}`,
        );
        return index ? [document.createElement("br"), text] : [text];
      }),
    );
    requestAnimationFrame(onLayoutChange);
  } catch {
    document.querySelector(".contacts-grid").textContent =
      "Не удалось загрузить контакты. Попробуйте обновить страницу.";
  }
}
