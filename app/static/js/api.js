let checkout = null;
let checkoutPromise = null;
let catalogPromise = null;
export function currentCheckout() {
  return checkout;
}
export async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { Accept: "application/json", ...options.headers },
    signal: options.signal || AbortSignal.timeout(20000),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join("; ")
      : data.detail;
    const retry = response.headers.get("Retry-After");
    const error = new Error(
      detail || `Не удалось выполнить запрос (${response.status}).`,
    );
    if (response.status === 429 && retry)
      error.message += ` Повторите через ${Math.ceil(Number(retry) / 60)} мин.`;
    error.legalChanged = response.headers.get("X-Legal-Changed") === "true";
    error.catalogChanged = response.headers.get("X-Catalog-Changed") === "true";
    throw error;
  }
  return data;
}
export async function getCheckout({ refresh = false } = {}) {
  if (checkout && !refresh) return checkout;
  if (!checkoutPromise) {
    checkoutPromise = fetchJSON("/api/checkout/")
      .then((data) => {
        checkout = data;
        return data;
      })
      .finally(() => {
        checkoutPromise = null;
      });
  }
  return checkoutPromise;
}
export async function getProducts({ refresh = false } = {}) {
  if (refresh) return fetchJSON("/api/products/");
  if (!catalogPromise)
    catalogPromise = fetchJSON("/api/products/").catch((error) => {
      catalogPromise = null;
      throw error;
    });
  return catalogPromise;
}
