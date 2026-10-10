import { scrollBehavior } from "./utils.js";
const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 5215;
let showcaseDesktopDelta = 0;
let contactsDesktopDelta = 0;
let priceDesktopDelta = 0;

const DESKTOP_LAYOUT_BASE = {
  priceTop: 2549,
  productsTop: 3500,
  contactsTop: 4148,
  footerTop: 4799,
};
let stageScale = 1;
const SHOWCASE_PRICE_GAP = { desktop: 133, mobile: 72 };
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
  if (!hint || !arrow) return;

  if (!buttons.length || isMobileLayout()) {
    hint.hidden = true;
    arrow.hidden = true;
    return;
  }

  // Both rectangles share the section's reveal translation and page scale.
  const priceBounds = price.getBoundingClientRect();
  const scale = priceBounds.width / price.offsetWidth || 1;
  const strawberry = price.querySelector(".price-strawberry");
  const strawberryBottom = strawberry
    ? (strawberry.getBoundingClientRect().bottom - priceBounds.top) / scale
    : -Infinity;

  let nearest = null;
  for (const candidate of buttons) {
    const bounds = candidate.getBoundingClientRect();
    const rect = {
      right: (bounds.right - priceBounds.left) / scale,
      top: (bounds.top - priceBounds.top) / scale,
      bottom: (bounds.bottom - priceBounds.top) / scale,
    };
    // Select the first complete button below the rotated berry's lower edge.
    if (rect.top >= strawberryBottom && (!nearest || rect.top < nearest.top)) {
      nearest = rect;
    }
  }

  hint.hidden = !nearest;
  arrow.hidden = !nearest;
  if (!nearest) return;

  const targetY = (nearest.top + nearest.bottom) / 2;
  hint.style.left = `${nearest.right + 54}px`;
  hint.style.top = `${targetY - (hint.offsetHeight || 22) / 2}px`;
  // A fixed vector arrow stays straight and centered beside the price.
  arrow.style.left = `${nearest.right + 4}px`;
  arrow.style.top = `${targetY - 12}px`;
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
  const priceTitle = price?.querySelector(".price-title");

  if (
    !section ||
    !card ||
    !price ||
    !priceTitle ||
    !products ||
    !contacts ||
    !footer
  ) {
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
    // Measure from the visible showcase rectangle, including empty/error states.
    price.style.setProperty("padding-top", "0px", "important");
    const showcaseGap =
      textBounds(priceTitle).top - card.getBoundingClientRect().bottom;
    price.style.setProperty(
      "padding-top",
      `${Math.max(0, SHOWCASE_PRICE_GAP.mobile - showcaseGap)}px`,
      "important",
    );
    // Mobile sections stay in document flow; adjust only the space before the title.
    products.style.paddingTop = "0px";
    const title = products.querySelector(".products-title");
    const currentGap = textBounds(title).top - priceCategoryBottom(price);
    products.style.paddingTop = `${Math.max(0, PRICE_PRODUCTS_GAP.mobile - currentGap)}px`;
    positionPriceHint();
    return;
  }

  price.style.removeProperty("padding-top");
  products.style.removeProperty("padding-top");
  const showcaseBounds = section.getBoundingClientRect();
  const previousPriceBounds = price.getBoundingClientRect();
  const cardBottom =
    (card.getBoundingClientRect().bottom - showcaseBounds.top) / stageScale;
  const priceTitleOffset =
    (textBounds(priceTitle).top - previousPriceBounds.top) / stageScale;
  // Relative measurements cancel reveal translations and include the .94 section scale.
  const priceTop =
    section.offsetTop +
    cardBottom +
    SHOWCASE_PRICE_GAP.desktop -
    priceTitleOffset;
  showcaseDesktopDelta = priceTop - DESKTOP_LAYOUT_BASE.priceTop;
  const showcaseScale =
    showcaseBounds.width / section.offsetWidth / stageScale || 1;
  section.style.height = `${Math.max(0, (priceTop - section.offsetTop) / showcaseScale)}px`;
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
