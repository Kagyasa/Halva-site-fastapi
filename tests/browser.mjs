import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseURL = process.env.BROWSER_TEST_URL || "http://127.0.0.1:8765";
const browser = await chromium.launch({ headless: true });
try {
  for (const width of [390, 960, 1440]) {
    const page = await browser.newPage({
      viewport: { width, height: 720 },
      reducedMotion: "reduce",
    });
    const errors = [];
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
        category: { name: "Десерты", slug: "desserts" },
        is_available_for_order: true,
      };
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
      if (url.pathname === "/api/products/") data = [product];
      if (url.pathname === "/api/showcase/")
        data = Array.from({ length: 40 }, (_, index) => ({
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
    assert.deepEqual(errors, []);
    const widthState = await page.evaluate(() => ({
      viewport: innerWidth,
      page: document.documentElement.scrollWidth,
    }));
    assert(
      widthState.page <= widthState.viewport + 1,
      `Horizontal overflow at ${width}px`,
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
    await page.evaluate(() => window.openOrderModal("product-1"));
    await page
      .locator('#order-product-list input[type="checkbox"]')
      .first()
      .waitFor();
    const panel = await page.locator(".order-modal-panel").boundingBox();
    assert(
      panel.x >= 0 && panel.x + panel.width <= width + 1,
      `Modal overflow at ${width}px`,
    );
    await page.locator("#order-name").fill("Тестовый клиент");
    await page.locator("#order-phone").fill("89227330330");
    await page.locator("#order-time").fill("12:00");
    await page.locator("#order-consent").check();
    await page.locator(".order-product-quantity-input").fill("2");
    await page.locator(".order-product-quantity-input").blur();
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
