import { getProducts } from "./api.js";
import {
  formatPrice,
  getSafeVkUrl,
  normalizeProductImageUrl,
  scrollBehavior,
} from "./utils.js";
import { isMobileLayout } from "./layout.js?v=20261010-straight-price-arrow";
import {
  renderPriceList,
  showPriceMessage,
} from "./prices.js?v=20261010-straight-price-arrow";
let productOffset = 0;
function getProductCardTitle(product) {
  return product?.display_name || product?.name || "Десерт";
}

export async function loadProducts() {
  const track = document.getElementById("products");
  track.innerHTML = "";

  try {
    const products = await getProducts();
    renderPriceList(products);

    /* Сохраняем исходный порядок товаров, но всю категорию «Сытная еда»
           переносим в самый конец карусели. sort() в современных браузерах стабилен,
           поэтому порядок внутри каждой из двух групп не меняется. */
    const sortedProducts = [...products].sort((a, b) => {
      const aIsSavory =
        a?.category?.slug === "savory-food" ||
        a?.category?.name === "Сытная еда";
      const bIsSavory =
        b?.category?.slug === "savory-food" ||
        b?.category?.name === "Сытная еда";
      return Number(aIsSavory) - Number(bIsSavory);
    });

    /* В карусели показываем только один товар для каждого отображаемого имени.
           Сравниваем именно то название, которое видит пользователь: display_name,
           а при его отсутствии — обычное name. Регистр и лишние пробелы не учитываем. */
    const seenDisplayNames = new Set();

    sortedProducts
      .filter((product) =>
        Boolean(normalizeProductImageUrl(product?.image_url)),
      )
      .filter((product) => {
        const displayNameKey = getProductCardTitle(product)
          .trim()
          .replace(/\s+/g, " ")
          .toLocaleLowerCase("ru-RU");

        if (seenDisplayNames.has(displayNameKey)) return false;

        seenDisplayNames.add(displayNameKey);
        return true;
      })
      .forEach((product) => {
        const imageUrl = normalizeProductImageUrl(product.image_url);
        const title = String(getProductCardTitle(product));
        const vkUrl = getSafeVkUrl(product.vk_url);

        const card = document.createElement(vkUrl ? "a" : "div");
        card.className = "product-card";

        if (vkUrl) {
          card.href = vkUrl;
          card.target = "_blank";
          card.rel = "noopener noreferrer";
          card.setAttribute(
            "aria-label",
            `${title} — открыть товар во ВКонтакте`,
          );
        }

        const priceText =
          product.price !== null && product.price !== undefined
            ? formatPrice(product.price)
            : "";

        const imageWrap = document.createElement("div");
        imageWrap.className = "product-card-image";

        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = title;
        image.loading = "lazy";
        image.decoding = "async";

        const heading = document.createElement("h3");
        heading.textContent = title;

        const price = document.createElement("p");
        price.textContent = priceText;

        imageWrap.appendChild(image);
        card.append(imageWrap, heading, price);
        track.appendChild(card);
      });

    productOffset = 0;
    track.style.transform = "translateX(0)";
  } catch (error) {
    showPriceMessage(
      "Не удалось загрузить прайс. Попробуйте обновить страницу.",
    );
    console.error("Ошибка загрузки товаров:", error);
  }
}

export function scrollProducts(direction) {
  const track = document.getElementById("products");
  const windowEl = document.querySelector(".products-window");
  if (!track || !windowEl) return;

  if (isMobileLayout()) {
    const firstCard = track.querySelector(".product-card");
    const gap = 14;
    const step = firstCard
      ? firstCard.getBoundingClientRect().width + gap
      : windowEl.clientWidth * 0.8;

    windowEl.scrollBy({
      left: direction * step,
      behavior: scrollBehavior(),
    });
    return;
  }

  const count = track.children.length;
  const visible = 5;
  const step = 330;
  const maxOffset = Math.max(0, (count - visible) * step);
  productOffset = Math.min(
    maxOffset,
    Math.max(0, productOffset + direction * step),
  );
  track.style.transform = `translateX(${-productOffset}px)`;
}
