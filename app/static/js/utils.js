export function toKopecks(value) {
  const text = String(value);
  if (!/^\d+(\.\d{1,2})?$/.test(text)) throw new Error("Некорректная цена");
  const [whole, fraction = ""] = text.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}
export function formatPrice(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `${new Intl.NumberFormat("ru-RU", { minimumFractionDigits: Number.isInteger(amount) ? 0 : 2, maximumFractionDigits: 2 }).format(amount)} Руб.`;
}
export function scrollBehavior() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
}
export function formatContactPhone(phone) {
  let digits = String(phone || "").replace(/\D/g, "");
  if (digits.length === 10) digits = `7${digits}`;
  if (digits.length === 11 && digits.startsWith("8"))
    digits = `7${digits.slice(1)}`;
  return digits.length === 11 && digits.startsWith("7")
    ? `+7 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7, 9)}-${digits.slice(9, 11)}`
    : String(phone || "");
}
export function phoneHref(phone) {
  let digits = String(phone || "").replace(/\D/g, "");
  if (digits.length === 10) digits = `7${digits}`;
  if (digits.length === 11 && digits.startsWith("8"))
    digits = `7${digits.slice(1)}`;
  return digits ? `tel:+${digits}` : "";
}
export function getSafeHttpUrl(value, { allowSameOrigin = true } = {}) {
  const raw = String(value || "")
    .trim()
    .replaceAll("\\", "/");
  if (!raw) return "";
  try {
    const parsed = new URL(raw, window.location.origin);
    if (
      !["http:", "https:"].includes(parsed.protocol) ||
      (!allowSameOrigin && parsed.origin === window.location.origin)
    )
      return "";
    return parsed.href;
  } catch {
    return "";
  }
}
export function getSafeVkUrl(value) {
  const url = getSafeHttpUrl(value, { allowSameOrigin: false });
  if (!url) return "";
  const host = new URL(url).hostname.toLowerCase();
  return ["vk.ru", "vk.com"].some(
    (domain) => host === domain || host.endsWith(`.${domain}`),
  )
    ? url
    : "";
}
export const normalizeProductImageUrl = getSafeHttpUrl;
