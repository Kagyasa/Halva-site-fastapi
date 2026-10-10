import { fetchJSON, getCheckout, getProducts } from "./api.js";
import { formatPrice, toKopecks, scrollBehavior } from "./utils.js";
import { focusModal, restoreModalFocus } from "./dialogs.js";
import { renderPriceList } from "./prices.js?v=20261010-category-edge";

let orderProducts = [];
let orderProductsLoaded = false;
let checkout = null;
let pendingProductId = "";
let loadingPromise = null;
let orderGeneration = 0;
let submitting = false;
let lastAttempt = null;
const clampQuantity = (value) =>
  Math.max(1, Math.min(50, Math.floor(Number(value) || 1)));

function setMessage(text) {
  const element = document.getElementById("order-form-message");
  element.className = `order-form-message${text ? " error" : ""}`;
  element.textContent = text;
}
function updateSubmitAvailability() {
  const button = document.getElementById("order-submit");
  button.disabled = submitting || !checkout?.available || !orderProductsLoaded;
  button.textContent = submitting ? "Отправляем…" : "Оставить заявку";
}
async function ensureOrderProductsLoaded() {
  if (!loadingPromise) {
    loadingPromise = Promise.all([
      getProducts({ refresh: true }),
      getCheckout({ refresh: true }),
    ]).finally(() => {
      loadingPromise = null;
    });
  }
  const generation = orderGeneration;
  updateSubmitAvailability();
  try {
    const [products, configuration] = await loadingPromise;
    if (generation !== orderGeneration) return;
    checkout = configuration;
    document.getElementById("order-demo-notice").hidden = !checkout.demo_mode;
    orderProducts = products
      .filter((product) => product.is_available_for_order)
      .map((product) => ({
        id: String(product.id),
        name: product.name,
        price: product.price,
        cents: toKopecks(product.price),
        category: product.category?.name || "",
      }));
    orderProductsLoaded = true;
    renderPriceList(products);
    const select = document.getElementById("order-pickup-location");
    const previous = select.value;
    select.replaceChildren(
      ...checkout.locations.map(
        (location) =>
          new Option(location.address || location.name, location.id),
      ),
    );
    if (checkout.locations.some((location) => location.id === previous))
      select.value = previous;
    document.getElementById("order-delivery-label").textContent =
      `Доставка +${formatPrice(checkout.delivery_price)}`;
    const date = document.getElementById("order-date");
    date.min = checkout.minimum_date;
    if (!date.value || date.value < date.min) date.value = date.min;
    renderOrderProductOptions();
    if (!checkout.available)
      setMessage(checkout.reason || "Приём заявок временно недоступен.");
  } catch (error) {
    if (generation !== orderGeneration) return;
    orderProductsLoaded = false;
    setMessage(
      "Не удалось загрузить форму. Закройте её и попробуйте открыть снова.",
    );
  } finally {
    if (generation === orderGeneration) updateSubmitAvailability();
  }
}
function getCheckedOrderProductIds() {
  return new Set(
    Array.from(
      document.querySelectorAll(
        '#order-product-list input[type="checkbox"]:checked',
      ),
    ).map((input) => input.value),
  );
}

function getOrderProductQuantityMap() {
  const quantities = new Map();

  document
    .querySelectorAll("#order-product-list .order-product-quantity-input")
    .forEach((input) => {
      const productId = input.dataset.productId;
      const quantity = clampQuantity(input.value);
      if (productId) quantities.set(productId, quantity);
    });

  return quantities;
}

function setOrderProductQuantity(row, quantity) {
  const input = row?.querySelector(".order-product-quantity-input");
  if (!input) return;

  const safeQuantity = clampQuantity(quantity);
  input.value = String(safeQuantity);
  updateOrderTotal();
}

function syncOrderProductRowState(row) {
  const checkbox = row?.querySelector('input[type="checkbox"]');
  const quantityInput = row?.querySelector(".order-product-quantity-input");

  if (!checkbox || !quantityInput) return;

  row.classList.toggle("is-selected", checkbox.checked);
  quantityInput.disabled = !checkbox.checked;

  row.querySelectorAll(".order-quantity-button").forEach((button) => {
    button.disabled = !checkbox.checked;
  });
}

function renderOrderProductOptions() {
  const list = document.getElementById("order-product-list");
  if (!list) return;

  const checkedIds = getCheckedOrderProductIds();
  const savedQuantities = getOrderProductQuantityMap();
  list.innerHTML = "";

  if (!orderProducts.length) {
    list.innerHTML =
      '<p class="order-product-empty">Сейчас нет десертов, доступных для заказа.</p>';
    updateOrderTotal();
    return;
  }

  orderProducts.forEach((product, index) => {
    const row = document.createElement("div");
    row.className = "order-product-option";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "products";
    checkbox.value = product.id;
    checkbox.dataset.index = String(index);
    checkbox.id = `order-product-${index}`;
    checkbox.checked = checkedIds.has(product.id);

    const name = document.createElement("label");
    name.className = "order-product-name";
    name.htmlFor = checkbox.id;
    name.textContent = product.name;

    const price = document.createElement("span");
    price.className = "order-product-option-price";
    price.textContent = formatPrice(product.price);

    const quantity = document.createElement("div");
    quantity.className = "order-product-quantity";
    quantity.setAttribute("aria-label", `Количество: ${product.name}`);

    const minus = document.createElement("button");
    minus.type = "button";
    minus.className = "order-quantity-button";
    minus.textContent = "−";
    minus.setAttribute("aria-label", `Уменьшить количество: ${product.name}`);

    const quantityInput = document.createElement("input");
    quantityInput.type = "number";
    quantityInput.className = "order-product-quantity-input";
    quantityInput.min = "1";
    quantityInput.max = "50";
    quantityInput.step = "1";
    quantityInput.inputMode = "numeric";
    quantityInput.dataset.productId = product.id;
    quantityInput.value = String(savedQuantities.get(product.id) || 1);
    quantityInput.setAttribute(
      "aria-label",
      `Количество товара ${product.name}`,
    );

    const plus = document.createElement("button");
    plus.type = "button";
    plus.className = "order-quantity-button";
    plus.textContent = "+";
    plus.setAttribute("aria-label", `Увеличить количество: ${product.name}`);

    minus.addEventListener("click", () => {
      setOrderProductQuantity(row, Number(quantityInput.value) - 1);
    });

    plus.addEventListener("click", () => {
      setOrderProductQuantity(row, Number(quantityInput.value) + 1);
    });

    quantityInput.addEventListener("change", () => {
      setOrderProductQuantity(row, quantityInput.value);
    });

    quantityInput.addEventListener("input", () => {
      const value = Number(quantityInput.value);
      if (Number.isFinite(value) && value >= 1 && value <= 50) {
        updateOrderTotal();
      }
    });

    checkbox.addEventListener("change", () => {
      if (checkbox.checked && Number(quantityInput.value) < 1) {
        quantityInput.value = "1";
      }
      syncOrderProductRowState(row);
      updateOrderTotal();
    });

    quantity.append(minus, quantityInput, plus);
    row.append(checkbox, name, price, quantity);
    list.appendChild(row);

    syncOrderProductRowState(row);
  });

  if (pendingProductId) {
    selectOrderProduct(pendingProductId);
  }

  updateOrderTotal();
}

function selectOrderProduct(id) {
  const index = orderProducts.findIndex((product) => product.id === String(id));
  if (index < 0) return;
  const checkbox = document.querySelector(
    `#order-product-list input[data-index="${index}"]`,
  );
  if (!checkbox) return;
  checkbox.checked = true;
  const row = checkbox.closest(".order-product-option");
  syncOrderProductRowState(row);
  row.scrollIntoView({ block: "nearest", behavior: scrollBehavior() });
  updateOrderTotal();
}
export function openOrderModal(productId = "") {
  const modal = document.getElementById("order-modal");
  if (modal.classList.contains("is-open")) {
    if (productId) selectOrderProduct(productId);
    return;
  }
  orderGeneration += 1;
  pendingProductId = String(productId || "");
  checkout = null;
  setMessage("");
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  focusModal("order-modal");
  ensureOrderProductsLoaded().then(() => {
    if (modal.classList.contains("is-open"))
      document.getElementById("order-name").focus({ preventScroll: true });
  });
  updateOrderDeliveryFields();
}
function resetOrderForm() {
  document.getElementById("order-form").reset();
  document
    .querySelectorAll("#order-product-list .order-product-option")
    .forEach((row) => {
      row.querySelector('input[type="checkbox"]').checked = false;
      row.querySelector(".order-product-quantity-input").value = "1";
      syncOrderProductRowState(row);
    });
  pendingProductId = "";
  setMessage("");
  updateOrderDeliveryFields();
}
export function closeOrderModal() {
  if (submitting) return;
  orderGeneration += 1;
  const modal = document.getElementById("order-modal");
  const result = document.getElementById("order-result-overlay");
  result.className = "order-result-overlay";
  result.setAttribute("aria-hidden", "true");
  restoreModalFocus("order-result-overlay");
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  resetOrderForm();
  restoreModalFocus("order-modal");
}
function updateOrderDeliveryFields() {
  const delivery = document.getElementById("order-delivery").checked;
  document
    .getElementById("order-pickup-field")
    .classList.toggle("is-visible", !delivery);
  document
    .getElementById("order-address-field")
    .classList.toggle("is-visible", delivery);
  document.getElementById("order-pickup-location").required = !delivery;
  document.getElementById("order-address").required = delivery;
  updateOrderTotal();
}
function getSelectedOrderProducts() {
  return [
    ...document.querySelectorAll(
      '#order-product-list input[type="checkbox"]:checked',
    ),
  ]
    .map((input) => {
      const product = orderProducts[Number(input.dataset.index)];
      if (!product) return null;
      return {
        ...product,
        quantity: clampQuantity(
          input
            .closest(".order-product-option")
            .querySelector(".order-product-quantity-input").value,
        ),
      };
    })
    .filter(Boolean);
}
function orderTotalCents() {
  const subtotal = getSelectedOrderProducts().reduce(
    (sum, product) => sum + product.cents * product.quantity,
    0,
  );
  return (
    subtotal +
    (document.getElementById("order-delivery").checked && checkout
      ? toKopecks(checkout.delivery_price)
      : 0)
  );
}
function updateOrderTotal() {
  const products = getSelectedOrderProducts();
  const subtotal = products.reduce(
    (sum, product) => sum + product.cents * product.quantity,
    0,
  );
  const quantity = products.reduce((sum, product) => sum + product.quantity, 0);
  const fee =
    document.getElementById("order-delivery").checked && checkout
      ? toKopecks(checkout.delivery_price)
      : 0;
  document.getElementById("order-products-summary-label").textContent =
    products.length ? `Десерты (${quantity} шт.)` : "Десерты";
  document.getElementById("order-product-price").textContent = products.length
    ? formatPrice(subtotal / 100)
    : "—";
  document.getElementById("order-delivery-price").textContent = formatPrice(
    fee / 100,
  );
  document.getElementById("order-total").textContent = products.length
    ? formatPrice((subtotal + fee) / 100)
    : "—";
}
function isValidOrderPhone(value) {
  if (!/^[0-9+()\-\s]+$/.test(value)) return false;
  const digits = value.replace(/\D/g, "");
  return digits.length === 10 || (digits.length === 11 && /^[78]/.test(digits));
}
function showResult(state, text) {
  const overlay = document.getElementById("order-result-overlay");
  overlay.className = `order-result-overlay is-open is-${state === "processing" ? "processing" : `complete is-${state}`}`;
  overlay.setAttribute("aria-hidden", "false");
  const icon = document.getElementById("order-result-icon");
  if (state === "processing")
    icon.innerHTML = '<span class="order-result-spinner"></span>';
  else icon.textContent = state === "success" ? "✓" : "!";
  document.getElementById("order-result-title").textContent =
    state === "processing"
      ? "Подождите"
      : state === "success"
        ? "Заявка принята"
        : "Не получилось отправить заявку";
  document.getElementById("order-result-text").textContent = text;
  focusModal("order-result-overlay");
  if (state !== "processing")
    document
      .getElementById("order-result-close")
      .focus({ preventScroll: true });
}
export function closeOrderResultModal() {
  if (submitting) return;
  const overlay = document.getElementById("order-result-overlay");
  if (overlay.classList.contains("is-success")) return closeOrderModal();
  overlay.className = "order-result-overlay";
  overlay.setAttribute("aria-hidden", "true");
  restoreModalFocus("order-result-overlay");
  updateSubmitAvailability();
}
async function attemptKey(payload) {
  // Persist only the random key and a digest, never customer contact data.
  const serialized = JSON.stringify(payload);
  const digest = crypto.subtle
    ? [
        ...new Uint8Array(
          await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(serialized),
          ),
        ),
      ]
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("")
    : serialized;
  let stored = lastAttempt;
  if (crypto.subtle) {
    try {
      stored =
        JSON.parse(sessionStorage.getItem("halva-order-attempt")) || stored;
    } catch {}
  }
  if (stored?.digest !== digest) {
    stored = {
      digest,
      key: [...crypto.getRandomValues(new Uint8Array(24))]
        .map((value) => value.toString(16).padStart(2, "0"))
        .join(""),
    };
  }
  lastAttempt = stored;
  if (crypto.subtle) {
    try {
      sessionStorage.setItem("halva-order-attempt", JSON.stringify(stored));
    } catch {}
  }
  return stored.key;
}
async function handleOrderButtonClick(event) {
  event.preventDefault();
  if (submitting) return;
  const form = document.getElementById("order-form");
  setMessage("");
  if (!checkout?.available || !orderProductsLoaded) {
    setMessage(checkout?.reason || "Дождитесь загрузки формы.");
    return;
  }
  const name = document.getElementById("order-name");
  name.value = name.value.trim().replace(/\s+/g, " ");
  if (!form.reportValidity()) return;
  const phone = document.getElementById("order-phone");
  if (!isValidOrderPhone(phone.value)) {
    setMessage("Укажите российский номер телефона из 10–11 цифр.");
    phone.focus();
    return;
  }
  const products = getSelectedOrderProducts();
  if (!products.length || products.length > 30) {
    setMessage("Выберите от 1 до 30 десертов.");
    return;
  }
  const delivery = document.getElementById("order-delivery").checked;
  const payload = {
    name: name.value,
    phone: phone.value.trim(),
    date: document.getElementById("order-date").value,
    time: document.getElementById("order-time").value,
    items: products
      .map((product) => ({
        product_id: product.id,
        quantity: product.quantity,
      }))
      .sort((a, b) => a.product_id.localeCompare(b.product_id)),
    delivery_type: delivery ? "delivery" : "pickup",
    pickup_location_id: delivery
      ? null
      : document.getElementById("order-pickup-location").value,
    address: delivery
      ? document.getElementById("order-address").value.trim()
      : null,
    website: document.getElementById("order-website").value,
    consent: document.getElementById("order-consent").checked,
    privacy_policy_version_id: checkout.privacy_policy.id,
    consent_text_version_id: checkout.consent_text.id,
    expected_total: (orderTotalCents() / 100).toFixed(2),
  };
  submitting = true;
  updateSubmitAvailability();
  showResult("processing", "Заявка обрабатывается…");
  try {
    payload.idempotency_key = await attemptKey(payload);
    const data = await fetchJSON("/api/orders/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    lastAttempt = null;
    try {
      sessionStorage.removeItem("halva-order-attempt");
    } catch {}
    showResult("success", `${data.message} Итого: ${formatPrice(data.total)}`);
  } catch (error) {
    if (error.legalChanged || error.catalogChanged) {
      if (error.legalChanged)
        document.getElementById("order-consent").checked = false;
      await ensureOrderProductsLoaded();
    }
    const text = ["TimeoutError", "AbortError", "TypeError"].includes(
      error.name,
    )
      ? "Связь с сервером прервалась. Повторите отправку: сохранённая заявка не будет создана повторно."
      : error.message;
    showResult("error", text);
  } finally {
    submitting = false;
    updateSubmitAvailability();
  }
}
document
  .getElementById("order-pickup")
  .addEventListener("change", updateOrderDeliveryFields);
document
  .getElementById("order-delivery")
  .addEventListener("change", updateOrderDeliveryFields);
document
  .getElementById("order-form")
  .addEventListener("submit", (event) => event.preventDefault());
const submitButton = document.getElementById("order-submit");
submitButton.addEventListener("click", handleOrderButtonClick);
submitButton.addEventListener("keydown", (event) => {
  if (event.key === "Enter") event.preventDefault();
});
document.getElementById("order-modal").addEventListener("click", (event) => {
  if (
    event.target.id === "order-modal" &&
    !document
      .getElementById("order-result-overlay")
      .classList.contains("is-open")
  )
    closeOrderModal();
});
document
  .getElementById("order-result-overlay")
  .addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeOrderResultModal();
  });
