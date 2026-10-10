import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseURL = process.env.BROWSER_TEST_URL || "http://127.0.0.1:8765";
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BROWSER_EXECUTABLE_PATH || undefined,
});
async function settleLayout(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(requestAnimationFrame);
    await new Promise(requestAnimationFrame);
  });
}
try {
  for (const width of [360, 390, 960, 1440, 1920]) {
    const page = await browser.newPage({
      viewport: { width, height: 720 },
      reducedMotion: "reduce",
    });
    const errors = [];
    let showcaseRowCount = 40;
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) =>
      route.abort(),
    );
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const product = {
        id: "product-1",
        name: "Тестовый десерт",
        slug: "bento-tort-klubnika-plombir",
        price: "100.75",
        image_url: "/static/products/bento-cake.jpg",
        category: {
          id: "category-1",
          name: "Десерты",
          slug: "desserts",
          is_active: true,
        },
        is_available_for_order: true,
      };
      const catalog = [
        product,
        ...Array.from({ length: 48 }, (_, index) => ({
          ...product,
          id: `extra-${index}`,
          name: `Очень длинное название десерта для проверки переноса текста и высоты карточки ${index}`,
          category: {
            id: `category-${2 + (index % 3)}`,
            name: `Категория ${2 + (index % 3)} с дополнительным описанием`,
            slug: `category-${2 + (index % 3)}`,
            is_active: true,
          },
          size: "XL",
          weight_min_grams: 2300,
          weight_max_grams: 2500,
          portions_min: 18,
          portions_max: 28,
        })),
      ];
      const locations = [
        {
          id: "location-1",
          name: "Кафе",
          address: "Ленина, 15",
          phone: "+79227330330",
          weekday_hours: "08:00–21:00",
          weekend_hours: "09:00–21:00",
        },
        {
          id: "location-2",
          name: "Кафе",
          address: "Забабахина, 42",
          phone: "+79227200220",
          weekday_hours: "08:00–21:00",
          weekend_hours: "09:00–21:00",
        },
      ];
      let data = [];
      if (url.pathname === "/api/products/") data = catalog;
      if (url.pathname === "/api/showcase/")
        data = Array.from({ length: showcaseRowCount }, (_, index) => ({
          product: { ...product, name: `Десерт ${index}` },
        }));
      if (url.pathname === "/api/checkout/")
        data = {
          available: true,
          minimum_date: "2099-01-01",
          delivery_price: "150.00",
          locations,
          privacy_policy: {
            id: "policy",
            title: "Только тест",
            text: "Синтетический документ для теста.",
          },
          consent_text: {
            id: "consent",
            text: "Синтетическое согласие для теста.",
          },
        };
      await route.fulfill({ json: data });
    });
    await page.goto(baseURL);
    await page.locator(".showcase-row").first().waitFor();
    await page.locator(".price-pill:not([disabled])").first().waitFor();
    await settleLayout(page);
    assert.equal(
      await page.locator("#price-categories .price-card").count(),
      4,
    );
    assert.equal(
      await page.locator("#price-categories .price-pill").count(),
      49,
    );
    const sections = await page.evaluate(() => {
      const textBounds = (element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        return range.getBoundingClientRect();
      };
      const bounds = (selector) => {
        const rect = document.querySelector(selector).getBoundingClientRect();
        return { top: rect.top, bottom: rect.bottom };
      };
      return {
        price: bounds("#price"),
        categories: bounds("#price-categories"),
        products: bounds("#products-section"),
        contacts: bounds("#contacts"),
        footer: bounds(".site-footer"),
        showcaseCardBottom: bounds(".showcase-card").bottom,
        priceTextTop: textBounds(document.querySelector(".price-title")).top,
        lastCategoryBottom: bounds("#price-categories .price-card:last-child")
          .bottom,
        productsTextTop: textBounds(document.querySelector(".products-title"))
          .top,
      };
    });
    assert(
      sections.categories.bottom <= sections.price.bottom + 1,
      `Price rows escaped their section at ${width}px`,
    );
    assert(
      sections.products.top >= sections.price.bottom - 1,
      `Products overlapped the dynamic price at ${width}px`,
    );
    assert(
      sections.contacts.top >= sections.products.bottom - 1,
      `Contacts overlapped products at ${width}px`,
    );
    const expectedGap = width > 1024 ? (148 * width) / 1920 : 72;
    const expectedShowcaseGap = width > 1024 ? (133 * width) / 1920 : 72;
    assert(
      Math.abs(
        sections.priceTextTop -
          sections.showcaseCardBottom -
          expectedShowcaseGap,
      ) < 2,
      `Showcase-to-price gap must follow the showcase rectangle at ${width}px`,
    );
    assert(
      Math.abs(
        sections.productsTextTop - sections.lastCategoryBottom - expectedGap,
      ) < 2,
      `Price-to-products gap must follow the last category border at ${width}px`,
    );
    assert.deepEqual(errors, []);
    const widthState = await page.evaluate(() => ({
      viewport: innerWidth,
      page: document.documentElement.scrollWidth,
    }));
    assert(
      widthState.page <= widthState.viewport + 1,
      `Horizontal overflow at ${width}px`,
    );
    // The same border gap must hold when a location has a much shorter list.
    showcaseRowCount = 1;
    await page.locator(".showcase-tab").first().click();
    await page.waitForFunction(
      () => document.querySelectorAll(".showcase-row").length === 1,
    );
    await settleLayout(page);
    const shortShowcaseGap = await page.evaluate(() => {
      const title = document.createRange();
      title.selectNodeContents(document.querySelector(".price-title"));
      return (
        title.getBoundingClientRect().top -
        document.querySelector(".showcase-card").getBoundingClientRect().bottom
      );
    });
    assert(
      Math.abs(shortShowcaseGap - expectedShowcaseGap) < 2,
      `Short showcase must retain its rectangle-to-price gap at ${width}px`,
    );
    if (width > 1024) {
      await page.locator('.header-nav a[href="#price"]').click();
      const position = await page.locator("#price").boundingBox();
      const header = await page.locator(".site-header").boundingBox();
      assert(
        Math.abs(position.y - (header.height + 14)) < 3,
        "Navigation must follow expanded showcase height",
      );
    }
    await page
      .locator('#price-categories button[data-product-id="product-1"]')
      .click();
    const selectedProduct = page.locator(
      '#order-product-list input[type="checkbox"][value="product-1"]',
    );
    await selectedProduct.waitFor();
    assert.equal(await selectedProduct.isChecked(), true);
    const panel = await page.locator(".order-modal-panel").boundingBox();
    assert(
      panel.x >= 0 && panel.x + panel.width <= width + 1,
      `Modal overflow at ${width}px`,
    );
    await page.locator("#order-name").fill("Тестовый клиент");
    await page.locator("#order-phone").fill("89227330330");
    await page.locator("#order-time").fill("12:00");
    await page.locator("#order-consent").check();
    const quantity = page.locator(
      '#order-product-list .order-product-quantity-input[data-product-id="product-1"]',
    );
    assert.equal(await quantity.count(), 1);
    assert.equal(await quantity.isEnabled(), true);
    await quantity.fill("2");
    await quantity.blur();
    assert.match(await page.locator("#order-total").textContent(), /201,50/);
    await page.locator(".order-modal-close").focus();
    await page.keyboard.press("Shift+Tab");
    assert.equal(
      await page
        .locator("#order-submit")
        .evaluate((element) => element === document.activeElement),
      true,
      "Focus must remain in the dialog",
    );
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#order-name").inputValue(), "");
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log("Browser checks passed at phone, tablet and desktop widths.");
} finally {
  await browser.close();
}
