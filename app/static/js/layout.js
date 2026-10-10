import { scrollBehavior } from "./utils.js";
const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 5215;
let showcaseDesktopDelta = 0;
let contactsDesktopDelta = 0;
let priceDesktopDelta = 0;

const DESKTOP_LAYOUT_BASE = {
  showcaseHeight: 949,
  priceTop: 2549,
  productsTop: 3500,
  contactsTop: 4148,
  footerTop: 4799,
  showcaseBottomPadding: 133,
};
let stageScale = 1;
const PRICE_PRODUCTS_GAP = { desktop: 148, mobile: 72 };

function textBounds(element) {
  const range = document.createRange();
  range.selectNodeContents(element);
  return range.getBoundingClientRect?.() || element.getBoundingClientRect();
}

function priceCategoryBottom(price) {
  const categories = price.querySelector("#price-categories");
  const lastBlock = categories?.lastElementChild || categories || price;
  return lastBlock.getBoundingClientRect().bottom;
}

function positionPriceHint() {
  const price = document.querySelector(".price-section");
  const hint = price?.querySelector(".price-hint");
  const arrow = price?.querySelector(".price-hint-arrow");
  const buttons = [
    ...(price?.querySelectorAll("#price-categories .price-pill") || []),
  ];
  const button = buttons[0];
  if (!hint || !arrow) return;

  const hidden = !button || isMobileLayout();
  hint.hidden = hidden;
  arrow.hidden = hidden;
  if (hidden) return;

  // Both rectangles share the section's reveal translation and page scale.
  const priceBounds = price.getBoundingClientRect();
  const buttonBounds = button.getBoundingClientRect();
  const scale = priceBounds.width / price.offsetWidth || 1;
  const buttonRight = (buttonBounds.right - priceBounds.left) / scale;
  const buttonBottom = (buttonBounds.bottom - priceBounds.top) / scale;
  const strawberry = price.querySelector(".price-strawberry");
  const strawberryBottom = strawberry
    ? (strawberry.getBoundingClientRect().bottom - priceBounds.top) / scale
    : buttonBottom;
  const hintTop = Math.max(buttonBottom + 20, strawberryBottom + 22);

  hint.style.left = `${buttonRight + 41}px`;
  hint.style.top = `${hintTop}px`;

  const hintBounds = hint.getBoundingClientRect();
  const hintLeft = (hintBounds.left - priceBounds.left) / scale;
  const hintMiddle =
    (hintBounds.top + hintBounds.height / 2 - priceBounds.top) / scale;
  let nearest = null;
  let shortestDistance = Infinity;
  for (const candidate of buttons) {
    const bounds = candidate.getBoundingClientRect();
    const rect = {
      left: (bounds.left - priceBounds.left) / scale,
      right: (bounds.right - priceBounds.left) / scale,
      top: (bounds.top - priceBounds.top) / scale,
      bottom: (bounds.bottom - priceBounds.top) / scale,
    };
    const closestX = Math.max(rect.left, Math.min(hintLeft, rect.right));
    const closestY = Math.max(rect.top, Math.min(hintMiddle, rect.bottom));
    const distance = Math.hypot(hintLeft - closestX, hintMiddle - closestY);
    if (distance < shortestDistance) {
      shortestDistance = distance;
      nearest = rect;
    }
  }

  // Draw to the nearest price; the curve can turn up or down from the caption.
  const targetX = nearest.right + 6;
  const inset = Math.min(8, (nearest.bottom - nearest.top) / 2);
  const targetY = Math.max(
    nearest.top + inset,
    Math.min(hintMiddle, nearest.bottom - inset),
  );
  const startX = hintLeft - 8;
  const startY = hintMiddle;
  const left = Math.min(startX - 10, targetX) - 8;
  const top = Math.min(startY, targetY) - 12;
  const width = Math.max(startX, targetX + 26) - left + 8;
  const height = Math.abs(startY - targetY) + 24;
  const endX = targetX - left;
  const endY = targetY - top;
  arrow.style.left = `${left}px`;
  arrow.style.top = `${top}px`;
  arrow.style.width = `${width}px`;
  arrow.style.height = `${height}px`;
  const svg = arrow.querySelector("svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  arrow
    .querySelector(".price-hint-curve")
    .setAttribute(
      "d",
      `M ${startX - left} ${startY - top} C ${startX - left - 10} ${startY - top} ${endX + 26} ${endY} ${endX} ${endY}`,
    );
  arrow
    .querySelector(".price-hint-arrowhead")
    .setAttribute(
      "d",
      `M ${endX + 11} ${endY - 6} L ${endX} ${endY} L ${endX + 11} ${endY + 6}`,
    );
}

export function isMobileLayout() {
  return window.innerWidth <= 1024;
}

function updateFixedHeaderScale() {
  const header = document.querySelector(".site-header");
  if (!header) return;

  if (isMobileLayout()) {
    header.style.transform = "none";
    return;
  }

  header.style.transform = `translateX(-50%) scale(${stageScale})`;
}

function fitDesignStage() {
  const shell = document.getElementById("design-shell");
  const stage = document.getElementById("design-stage");

  if (isMobileLayout()) {
    stageScale = 1;
    shell.style.width = "100%";
    shell.style.height = "auto";
    shell.style.overflow = "visible";
    stage.style.width = "100%";
    stage.style.height = "auto";
    stage.style.transform = "none";
    stage.style.overflow = "visible";
    document.documentElement.style.overflowY = "auto";
    if (
      !document.body.classList.contains("mobile-menu-open") &&
      !document.body.classList.contains("modal-open")
    ) {
      document.body.style.overflowY = "auto";
    }
    updateFixedHeaderScale();
    return;
  }

  stageScale = window.innerWidth / DESIGN_WIDTH;
  const currentDesignHeight =
    DESIGN_HEIGHT +
    showcaseDesktopDelta +
    priceDesktopDelta +
    contactsDesktopDelta;

  shell.style.width = `${DESIGN_WIDTH * stageScale}px`;
  shell.style.height = `${currentDesignHeight * stageScale}px`;
  stage.style.width = `${DESIGN_WIDTH}px`;
  stage.style.height = `${currentDesignHeight}px`;
  stage.style.transform = `scale(${stageScale})`;
  updateFixedHeaderScale();
}

let layoutFrame = 0;
window.addEventListener("resize", () => {
  cancelAnimationFrame(layoutFrame);
  layoutFrame = requestAnimationFrame(() => {
    fitDesignStage();
    resizeShowcaseForContent();
    if (!isMobileLayout()) closeMobileMenu();
  });
});
fitDesignStage();

document.querySelectorAll(".js-scroll").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();

    const header = document.querySelector(".site-header");
    const headerHeight = header ? header.getBoundingClientRect().height : 0;
    const scrollGap = 14;

    const selector = link.getAttribute("href");
    const target = selector?.startsWith("#")
      ? document.querySelector(selector)
      : null;
    const targetTop = target
      ? Math.max(
          0,
          window.scrollY +
            target.getBoundingClientRect().top -
            headerHeight -
            scrollGap,
        )
      : 0;
    closeMobileMenu();

    window.scrollTo({
      top: targetTop,
      behavior: scrollBehavior(),
    });
  });
});

export function toggleMobileMenu() {
  const menu = document.getElementById("mobile-menu");
  const toggle = document.getElementById("mobile-menu-toggle");
  if (!menu || !toggle) return;

  const shouldOpen = !menu.classList.contains("is-open");
  menu.classList.toggle("is-open", shouldOpen);
  toggle.classList.toggle("is-open", shouldOpen);
  toggle.setAttribute("aria-expanded", String(shouldOpen));
  toggle.setAttribute(
    "aria-label",
    shouldOpen ? "Закрыть меню" : "Открыть меню",
  );
  menu.setAttribute("aria-hidden", String(!shouldOpen));
  document.body.classList.toggle("mobile-menu-open", shouldOpen);
}

export function closeMobileMenu() {
  const menu = document.getElementById("mobile-menu");
  const toggle = document.getElementById("mobile-menu-toggle");
  if (!menu || !toggle) return;

  menu.classList.remove("is-open");
  toggle.classList.remove("is-open");
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-label", "Открыть меню");
  menu.setAttribute("aria-hidden", "true");
  document.body.classList.remove("mobile-menu-open");
}

export function resizeShowcaseForContent() {
  const section = document.querySelector(".showcases");
  const card = document.querySelector(".showcase-card");
  const price = document.querySelector(".price-section");
  const products = document.querySelector(".products-section");
  const contacts = document.querySelector(".contacts-section");
  const footer = document.querySelector(".site-footer");

  if (!section || !card || !price || !products || !contacts || !footer) {
    return;
  }

  if (isMobileLayout()) {
    showcaseDesktopDelta = 0;
    contactsDesktopDelta = 0;
    priceDesktopDelta = 0;

    section.style.removeProperty("height");
    price.style.removeProperty("top");
    price.style.removeProperty("height");
    products.style.removeProperty("top");
    contacts.style.removeProperty("top");
    footer.style.removeProperty("top");

    fitDesignStage();
    // Mobile sections stay in document flow; adjust only the space before the title.
    products.style.paddingTop = "0px";
    const title = products.querySelector(".products-title");
    const currentGap = textBounds(title).top - priceCategoryBottom(price);
    products.style.paddingTop = `${Math.max(0, PRICE_PRODUCTS_GAP.mobile - currentGap)}px`;
    positionPriceHint();
    return;
  }

  // The beige card grows naturally with its contents.
  // Only when it becomes taller than the original Figma space do we
  // push all following desktop sections down by the same amount.
  const requiredSectionHeight = Math.max(
    DESKTOP_LAYOUT_BASE.showcaseHeight,
    card.offsetTop +
      card.scrollHeight +
      DESKTOP_LAYOUT_BASE.showcaseBottomPadding,
  );

  showcaseDesktopDelta =
    requiredSectionHeight - DESKTOP_LAYOUT_BASE.showcaseHeight;

  section.style.height = `${requiredSectionHeight}px`;
  products.style.removeProperty("padding-top");
  const priceTop = DESKTOP_LAYOUT_BASE.priceTop + showcaseDesktopDelta;
  price.style.top = `${priceTop}px`;
  const categories = document.getElementById("price-categories");
  const priceBounds = price.getBoundingClientRect();
  const productsBounds = products.getBoundingClientRect();
  const categoryBottom =
    (priceCategoryBottom(price) - priceBounds.top) / stageScale;
  const titleOffset =
    (textBounds(products.querySelector(".products-title")).top -
      productsBounds.top) /
    stageScale;
  // Relative measurements cancel reveal translations and retain each section's scale.
  const productsTop =
    priceTop + categoryBottom + PRICE_PRODUCTS_GAP.desktop - titleOffset;
  const priceScale = priceBounds.width / price.offsetWidth / stageScale || 1;
  const priceHeight = Math.max(
    (categories?.offsetTop || 60) + (categories?.scrollHeight || 0),
    (productsTop - priceTop) / priceScale,
  );
  priceDesktopDelta =
    productsTop - DESKTOP_LAYOUT_BASE.productsTop - showcaseDesktopDelta;
  price.style.height = `${priceHeight}px`;
  products.style.top = `${productsTop}px`;
  contacts.style.top = `${DESKTOP_LAYOUT_BASE.contactsTop + showcaseDesktopDelta + priceDesktopDelta}px`;
  const contactsGrid = contacts.querySelector(".contacts-grid");
  contactsDesktopDelta = Math.max(
    0,
    (contactsGrid?.offsetTop || 0) +
      (contactsGrid?.scrollHeight || 0) +
      70 -
      (DESKTOP_LAYOUT_BASE.footerTop - DESKTOP_LAYOUT_BASE.contactsTop),
  );
  footer.style.top = `${DESKTOP_LAYOUT_BASE.footerTop + showcaseDesktopDelta + priceDesktopDelta + contactsDesktopDelta}px`;

  fitDesignStage();
  positionPriceHint();
}

export function initRevealAnimations() {
  const blocks = document.querySelectorAll(".reveal-block");

  if (isMobileLayout()) {
    blocks.forEach((block) => block.classList.add("is-visible"));
    document
      .querySelector(".contacts-section")
      ?.classList.add("contacts-footer-visible");
    document
      .querySelector(".site-footer")
      ?.classList.add("contacts-footer-visible");
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.08,
      rootMargin: "0px 0px -4% 0px",
    },
  );

  blocks.forEach((block) => {
    observer.observe(block);
  });

  const contacts = document.querySelector(".contacts-section");
  const footer = document.querySelector(".site-footer");
  if (contacts && footer) {
    const contactsObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            contacts.classList.add("contacts-footer-visible");
            footer.classList.add("contacts-footer-visible");
            contactsObserver.unobserve(contacts);
          }
        });
      },
      {
        threshold: 0.08,
        rootMargin: "0px 0px -4% 0px",
      },
    );
    contactsObserver.observe(contacts);
  }
}

if (document.fonts?.ready) document.fonts.ready.then(resizeShowcaseForContent);
