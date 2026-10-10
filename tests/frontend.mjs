import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";
import { JSDOM } from "jsdom";

const root = path.resolve("app/static/js");
const html = await fs.readFile("app/templates/index.html", "utf8");
const dom = new JSDOM(html, {
  url: "https://halva.test/",
  runScripts: "outside-only",
  pretendToBeVisual: true,
});
const window = dom.window;
Object.defineProperty(window, "crypto", { value: webcrypto });
window.TextEncoder = TextEncoder;
window.AbortSignal = AbortSignal;
window.AbortController = AbortController;
window.matchMedia = () => ({ matches: false });
window.scrollTo = () => {};
window.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.HTMLElement.prototype.scrollIntoView = () => {};
const document = window.document;
const products = [
  {
    id: "product-1",
    slug: "bento-tort-klubnika-plombir",
    name: "Десерт <b>",
    price: "100.75",
    category: {
      id: "category-1",
      name: "Десерты <i>",
      slug: "desserts",
      is_active: true,
    },
    size: "S",
    diameter_cm: "18.00",
    height_min_cm: "5.00",
    height_max_cm: "6.00",
    weight_min_grams: 800,
    weight_max_grams: 1000,
    portions_min: 8,
    portions_max: 12,
    is_available_for_order: true,
  },
];
products.push(
  ...Array.from({ length: 48 }, (_, index) => ({
    ...products[0],
    id: `extra-${index}`,
    slug: `extra-${index}`,
    name: `Дополнительный десерт ${index}`,
    category: {
      id: `category-${2 + (index % 3)}`,
      name: `Категория ${2 + (index % 3)}`,
      slug: `category-${2 + (index % 3)}`,
      is_active: true,
    },
  })),
);
const locations = [
  {
    id: "location-1",
    name: "Кафе 1",
    address: "Ленина, 15",
    phone: "+79227330330",
    weekday_hours: "08:00–21:00",
    weekend_hours: "09:00–21:00",
  },
  {
    id: "location-2",
    name: "Кафе 2",
    address: "Забабахина, 42",
    phone: "+79227200220",
    weekday_hours: "08:00–21:00",
    weekend_hours: "09:00–21:00",
  },
];
const policy = {
  id: "policy-test",
  title: "Только тест",
  text: "Синтетический документ для теста.",
  version: "test",
};
const consent = {
  id: "consent-test",
  text: "Синтетическое согласие для теста.",
  version: "test",
};
const checkout = {
  available: true,
  demo_mode: true,
  reason: null,
  minimum_date: "2099-01-01",
  delivery_price: "150.00",
  locations,
  privacy_policy: policy,
  consent_text: consent,
};
const submissions = [];
let failSubmission = true;
let stalledShowcase = null;
let stallShowcase = false;
window.fetch = async (url, options = {}) => {
  const response = (data) =>
    new Response(JSON.stringify(data), {
      headers: { "Content-Type": "application/json" },
    });
  if (url === "/api/checkout/") return response(checkout);
  if (url === "/api/products/") return response(products);
  if (url === "/api/contacts/")
    return response([
      { type: "telegram", title: "TG", value: "https://vk.ru/halva_tort_snz" },
    ]);
  if (url.startsWith("/api/showcase/")) {
    const id = new URL(url, window.location.origin).searchParams.get(
      "pickup_location_id",
    );
    const data = [
      {
        product: {
          ...products[0],
          name: id === "location-1" ? "Первая витрина" : "Вторая витрина",
        },
      },
    ];
    if (stallShowcase && id === "location-1")
      return new Promise((resolve) => {
        stalledShowcase = () => resolve(response(data));
      });
    return response(data);
  }
  if (url === "/api/orders/") {
    submissions.push(JSON.parse(options.body));
    if (failSubmission)
      return new Response(
        JSON.stringify({ detail: "Почти готово, повторите отправку." }),
        { status: 503 },
      );
    return response({
      success: true,
      message: "Заявка принята!",
      order_id: "1234567890abcdef",
      total: "201.50",
    });
  }
  throw new Error(`Unexpected request: ${url}`);
};
const context = dom.getInternalVMContext();
const modules = new Map();
const pendingModules = new Map();
async function loadModule(filename) {
  if (!pendingModules.has(filename)) {
    pendingModules.set(
      filename,
      fs.readFile(filename, "utf8").then((source) => {
        const module = new vm.SourceTextModule(source, {
          context,
          identifier: filename,
        });
        modules.set(filename, module);
        return module;
      }),
    );
  }
  return pendingModules.get(filename);
}
async function until(predicate) {
  for (let i = 0; i < 200; i++) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error("UI condition timed out");
}
const main = await loadModule(path.join(root, "site.js"));
await main.link((specifier, referencing) =>
  loadModule(
    path.resolve(
      path.dirname(referencing.identifier),
      specifier.split(/[?#]/, 1)[0],
    ),
  ),
);
await main.evaluate();
await until(() => document.querySelectorAll(".showcase-tab").length === 2);
await until(() => document.querySelector("#price-categories .price-pill"));
assert.match(
  document.querySelector("#price-categories .price-pill").textContent,
  /100,75/,
);
assert.equal(
  document.querySelector(".price-card-title").textContent,
  products[0].category.name,
);
assert.equal(
  document.querySelector(".price-product-name").textContent,
  products[0].name,
);
assert.equal(
  document.querySelector("#price-categories i, #price-categories b"),
  null,
);
assert.match(
  document.querySelector(".price-product-details").textContent,
  /0,8–1 кг/,
);
assert.match(
  document.querySelector(".price-product-details").textContent,
  /8–12 порций/,
);
assert.equal(
  document.querySelector('[data-contact-type="telegram"]').href,
  "https://vk.ru/halva_tort_snz",
);
document
  .querySelector('#price-categories button[data-product-id="product-1"]')
  .click();
await until(() =>
  document.querySelector(
    '#order-product-list input[type="checkbox"][value="product-1"]',
  ),
);
assert(
  document.querySelector(
    '#order-product-list input[type="checkbox"][value="product-1"]',
  ).checked,
);
assert.equal(
  document.querySelectorAll("#order-product-list .order-product-quantity-input")
    .length,
  49,
);
assert.equal(
  document.querySelectorAll(
    "#order-product-list .order-product-quantity-input:disabled",
  ).length,
  48,
);
assert.equal(
  document.getElementById("order-pickup-location").value,
  "location-1",
);
assert.equal(document.getElementById("order-date").min, checkout.minimum_date);
assert.equal(document.getElementById("order-demo-notice").hidden, false);
assert.equal(document.getElementById("order-submit").disabled, false);
document.getElementById("order-name").value = "Тестовый клиент";
document.getElementById("order-phone").value = "89227330330";
document.getElementById("order-time").value = "12:00";
document.getElementById("order-consent").checked = true;
const quantity = document.querySelector(
  '#order-product-list .order-product-quantity-input[data-product-id="product-1"]',
);
assert.equal(quantity.disabled, false);
quantity.value = "2";
quantity.dispatchEvent(new window.Event("change"));
assert.match(document.getElementById("order-total").textContent, /201,50/);
const orderForm = document.getElementById("order-form");
const submitButton = document.getElementById("order-submit");
assert.equal(submitButton.type, "button");
for (const id of ["order-name", "order-phone", "order-submit"]) {
  const enter = new window.KeyboardEvent("keydown", {
    key: "Enter",
    bubbles: true,
    cancelable: true,
  });
  document.getElementById(id).dispatchEvent(enter);
  if (id === "order-submit") assert.equal(enter.defaultPrevented, true);
}
const implicitSubmit = new window.Event("submit", {
  bubbles: true,
  cancelable: true,
});
orderForm.dispatchEvent(implicitSubmit);
assert.equal(implicitSubmit.defaultPrevented, true);
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(submissions.length, 0);
const submit = () => submitButton.click();
submit();
await until(() =>
  document
    .getElementById("order-result-overlay")
    .classList.contains("is-error"),
);
assert.match(
  document.getElementById("order-result-text").textContent,
  /повторите отправку/,
);
window.closeOrderResultModal();
assert.equal(document.getElementById("order-name").value, "Тестовый клиент");
assert.equal(quantity.value, "2");
assert.equal(document.getElementById("order-submit").disabled, false);
failSubmission = false;
submit();
await until(() =>
  document
    .getElementById("order-result-overlay")
    .classList.contains("is-success"),
);
assert.equal(submissions[0].idempotency_key, submissions[1].idempotency_key);
assert.equal(submissions[0].expected_total, "201.50");
assert.equal(submissions[0].privacy_policy_version_id, policy.id);
assert.match(
  document.getElementById("order-result-text").textContent,
  /201,50/,
);
assert.doesNotMatch(
  document.getElementById("order-result-text").textContent,
  /№|12345678/,
);
window.closeOrderResultModal();
assert.equal(document.getElementById("order-name").value, "");
assert(!document.getElementById("order-modal").classList.contains("is-open"));

checkout.demo_mode = false;
window.openOrderModal("product-1");
await until(() => document.getElementById("order-demo-notice").hidden);
window.closeOrderModal();

const showcase = modules.get(path.join(root, "showcase.js")).namespace;
stallShowcase = true;
const oldRequest = showcase.loadShowcase(
  "location-1",
  document.querySelectorAll(".showcase-tab")[0],
);
await until(() => stalledShowcase);
await showcase.loadShowcase(
  "location-2",
  document.querySelectorAll(".showcase-tab")[1],
);
stalledShowcase();
await oldRequest;
assert.equal(
  document.getElementById("showcase-desserts").querySelectorAll(".showcase-row")
    .length,
  1,
);
assert.match(
  document.getElementById("showcase-desserts").textContent,
  /Вторая витрина/,
);

const prices = modules.get(path.join(root, "prices.js")).namespace;
const added = {
  ...products[0],
  id: "product-new",
  slug: "new",
  name: "Новый товар",
  category: { id: "category-2", name: "Новая категория", is_active: true },
};
prices.renderPriceList([
  products[0],
  added,
  { ...added, id: "disabled", is_available_for_order: false },
  { ...added, id: "inactive", is_active: false },
  {
    ...added,
    id: "inactive-category",
    category: { ...added.category, is_active: false },
  },
]);
assert.equal(
  document.querySelectorAll("#price-categories .price-card").length,
  2,
);
assert.equal(
  document.querySelectorAll("#price-categories .price-pill").length,
  2,
);
assert(document.querySelector('[data-product-id="product-new"]'));
prices.renderPriceList([
  {
    ...added,
    name: "Переименованный товар",
    price: "250.25",
    category: { ...added.category, name: "Переименованная категория" },
    size: null,
    diameter_cm: null,
    height_min_cm: null,
    height_max_cm: null,
    weight_min_grams: null,
    weight_max_grams: null,
    portions_min: null,
    portions_max: null,
  },
]);
assert.equal(
  document.querySelector(".price-card-title").textContent,
  "Переименованная категория",
);
assert.equal(
  document.querySelector(".price-product-name").textContent,
  "Переименованный товар",
);
assert.match(document.querySelector(".price-pill").textContent, /250,25/);
assert.equal(document.querySelector(".price-product-details"), null);
assert.equal(
  prices.productCharacteristics({
    weight_min_grams: 600,
    weight_max_grams: 600,
  }),
  "600 г",
);
assert.equal(prices.productCharacteristics({ portions_min: 2 }), "от 2 порций");
assert.equal(
  prices.productCharacteristics({ weight_max_grams: 900 }),
  "до 900 г",
);
prices.renderPriceList([]);
assert.equal(
  document.querySelectorAll("#price-categories .price-card").length,
  0,
);
assert.match(
  document.getElementById("price-categories").textContent,
  /нет товаров/,
);
assert.equal(document.querySelector(".price-hint").hidden, true);
prices.showPriceMessage("Не удалось загрузить прайс.");
assert.match(
  document.getElementById("price-categories").textContent,
  /Не удалось/,
);
prices.renderPriceList(products);
assert.equal(
  document.getElementById("price-categories").getAttribute("aria-busy"),
  "false",
);
console.log(
  "Frontend integration checks passed: database price categories, characteristics, availability, price-to-order selection, locations, consent versions, preserved form, idempotency, showcase race.",
);
dom.window.close();
