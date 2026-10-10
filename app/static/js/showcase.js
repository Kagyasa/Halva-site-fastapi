import { fetchJSON } from "./api.js";
import { formatPrice } from "./utils.js";
import { resizeShowcaseForContent } from "./layout.js?v=20261010-category-edge";

let generation = 0;
let activeRequest = null;
const isSavory = (product) =>
  product?.category?.slug === "savory-food" ||
  product?.category?.name === "Сытная еда";

function moveShowcaseLine(button) {
  const line = document.getElementById("showcase-active-line");
  const section = document.getElementById("showcases");
  if (!line || !button || !section) return;
  const box = section.getBoundingClientRect();
  const label = button.querySelector("span").getBoundingClientRect();
  const scale = box.width / section.offsetWidth || 1;
  line.style.left = `${(label.left - box.left) / scale}px`;
  line.style.width = `${label.width / scale}px`;
  line.style.top = `${(label.bottom - box.top) / scale + 6}px`;
}
function renderRows(target, items) {
  const rows = items.map((item) => {
    const row = document.createElement("div");
    row.className = "showcase-row";
    const name = document.createElement("span");
    name.textContent = item.product.name;
    const price = document.createElement("span");
    price.className = "price";
    price.textContent = formatPrice(item.product.price);
    row.append(name, price);
    return row;
  });
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "showcase-empty";
    empty.textContent = "Актуальный ассортимент появится здесь.";
    rows.push(empty);
  }
  target.replaceChildren(...rows);
}
export async function loadShowcase(locationId, button = null) {
  const requestGeneration = ++generation;
  activeRequest?.abort();
  activeRequest = new AbortController();
  document
    .querySelectorAll(".showcase-tab")
    .forEach((tab) => tab.classList.toggle("active", tab === button));
  moveShowcaseLine(button);
  const dessertBox = document.getElementById("showcase-desserts");
  const foodBox = document.getElementById("showcase-food");
  dessertBox.textContent = "Загрузка…";
  foodBox.textContent = "Загрузка…";
  try {
    const items = await fetchJSON(
      `/api/showcase/?pickup_location_id=${encodeURIComponent(locationId)}`,
      {
        signal: AbortSignal.any([
          activeRequest.signal,
          AbortSignal.timeout(20000),
        ]),
      },
    );
    if (requestGeneration !== generation) return;
    renderRows(
      dessertBox,
      items.filter((item) => !isSavory(item.product)),
    );
    renderRows(
      foodBox,
      items.filter((item) => isSavory(item.product)),
    );
  } catch (error) {
    if (requestGeneration !== generation) return;
    dessertBox.textContent =
      "Не удалось загрузить витрину. Выберите точку ещё раз.";
    foodBox.replaceChildren();
  }
  requestAnimationFrame(resizeShowcaseForContent);
}
window.addEventListener("resize", () =>
  moveShowcaseLine(document.querySelector(".showcase-tab.active")),
);
