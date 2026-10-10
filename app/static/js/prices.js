import { formatPrice } from "./utils.js";
import { resizeShowcaseForContent } from "./layout.js?v=20261010-nearest-price-hint";

const numberFormat = new Intl.NumberFormat("ru-RU", {
  maximumFractionDigits: 2,
});

function rangeLabel(minimum, maximum, unit, divisor = 1) {
  const low = minimum == null ? null : Number(minimum);
  const high = maximum == null ? null : Number(maximum);
  const format = (value) => numberFormat.format(value / divisor);
  if (low == null && high == null) return "";
  if (low != null && high != null)
    return `${low === high ? format(low) : `${format(low)}–${format(high)}`} ${unit}`;
  return `${low == null ? "до" : "от"} ${format(low ?? high)} ${unit}`;
}

export function productCharacteristics(product) {
  const weightInKg =
    Math.max(product.weight_min_grams || 0, product.weight_max_grams || 0) >=
    1000;
  return [
    product.size || "",
    product.diameter_cm == null
      ? ""
      : `Диаметр: ${numberFormat.format(Number(product.diameter_cm))} см`,
    rangeLabel(product.height_min_cm, product.height_max_cm, "см")
      ? `Высота: ${rangeLabel(product.height_min_cm, product.height_max_cm, "см")}`
      : "",
    rangeLabel(
      product.weight_min_grams,
      product.weight_max_grams,
      weightInKg ? "кг" : "г",
      weightInKg ? 1000 : 1,
    ),
    rangeLabel(product.portions_min, product.portions_max, "порций"),
  ]
    .filter(Boolean)
    .join(" · ");
}

export function showPriceMessage(message) {
  const container = document.getElementById("price-categories");
  const text = document.createElement("p");
  text.className = "price-empty";
  text.textContent = message;
  container.replaceChildren(text);
  container.setAttribute("aria-busy", "false");
  document.querySelector(".price-hint").hidden = true;
  document.querySelector(".price-hint-arrow").hidden = true;
  requestAnimationFrame(resizeShowcaseForContent);
}

export function renderPriceList(products) {
  const groups = new Map();
  for (const product of products) {
    if (
      !product.is_available_for_order ||
      product.is_active === false ||
      product.category?.is_active === false
    )
      continue;
    const category = product.category;
    if (!category?.id) continue;
    if (!groups.has(category.id))
      groups.set(category.id, { category, products: [] });
    groups.get(category.id).products.push(product);
  }
  if (!groups.size) {
    showPriceMessage("Сейчас нет товаров, доступных для заказа.");
    return;
  }
  const cards = [...groups.values()]
    .sort(
      (a, b) =>
        a.category.name.localeCompare(b.category.name, "ru") ||
        a.category.id.localeCompare(b.category.id),
    )
    .map(({ category, products: groupProducts }) => {
      const card = document.createElement("article");
      card.className = "price-card";
      card.dataset.categoryId = category.id;
      const heading = document.createElement("h3");
      heading.className = "price-card-title";
      heading.textContent = category.name;
      const list = document.createElement("div");
      list.className = "price-list";
      groupProducts.sort(
        (a, b) =>
          a.name.localeCompare(b.name, "ru") || a.id.localeCompare(b.id),
      );
      for (const product of groupProducts) {
        const row = document.createElement("div");
        row.className = "price-line";
        const label = document.createElement("span");
        label.className = "price-product-label";
        const name = document.createElement("span");
        name.className = "price-product-name";
        name.textContent = product.name;
        label.appendChild(name);
        const characteristics = productCharacteristics(product);
        if (characteristics) {
          const details = document.createElement("small");
          details.className = "price-product-details";
          details.textContent = characteristics;
          label.appendChild(details);
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "price-pill";
        button.dataset.productId = product.id;
        button.textContent = formatPrice(product.price);
        button.setAttribute(
          "aria-label",
          `Заказать ${product.name}, ${formatPrice(product.price)}`,
        );
        row.append(label, button);
        list.appendChild(row);
      }
      card.append(heading, list);
      return card;
    });
  const container = document.getElementById("price-categories");
  container.replaceChildren(...cards);
  container.setAttribute("aria-busy", "false");
  requestAnimationFrame(resizeShowcaseForContent);
}
