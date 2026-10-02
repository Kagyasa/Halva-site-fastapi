const DESIGN_WIDTH = 1920;
    const DESIGN_HEIGHT = 5215;
    let showcaseDesktopDelta = 0;

    const DESKTOP_LAYOUT_BASE = {
      showcaseHeight: 949,
      priceTop: 2549,
      productsTop: 3500,
      contactsTop: 4148,
      footerTop: 4799,
      showcaseBottomPadding: 133
    };
    let stageScale = 1;
    let productOffset = 0;

    function isMobileLayout() {
      return window.innerWidth <= 760;
    }

    function updateFixedHeaderScale() {
      const header = document.querySelector('.site-header');
      if (!header) return;

      if (isMobileLayout()) {
        header.style.transform = 'none';
        return;
      }

      header.style.transform = `translateX(-50%) scale(${stageScale})`;
    }

    function fitDesignStage() {
      const shell = document.getElementById('design-shell');
      const stage = document.getElementById('design-stage');

      if (isMobileLayout()) {
        stageScale = 1;
        shell.style.width = '100%';
        shell.style.height = 'auto';
        shell.style.overflow = 'visible';
        stage.style.width = '100%';
        stage.style.height = 'auto';
        stage.style.transform = 'none';
        stage.style.overflow = 'visible';
        document.documentElement.style.overflowY = 'auto';
        if (!document.body.classList.contains('mobile-menu-open') &&
            !document.body.classList.contains('modal-open')) {
          document.body.style.overflowY = 'auto';
        }
        updateFixedHeaderScale();
        return;
      }

      stageScale = window.innerWidth / DESIGN_WIDTH;
      const currentDesignHeight = DESIGN_HEIGHT + showcaseDesktopDelta;

      shell.style.width = `${DESIGN_WIDTH * stageScale}px`;
      shell.style.height = `${currentDesignHeight * stageScale}px`;
      stage.style.width = `${DESIGN_WIDTH}px`;
      stage.style.height = `${currentDesignHeight}px`;
      stage.style.transform = `scale(${stageScale})`;
      updateFixedHeaderScale();
    }

    window.addEventListener('resize', () => {
      fitDesignStage();
      resizeShowcaseForContent();

      if (!isMobileLayout()) closeMobileMenu();
    });
    fitDesignStage();

    document.querySelectorAll('.js-scroll').forEach(link => {
      link.addEventListener('click', event => {
        event.preventDefault();

        const header = document.querySelector('.site-header');
        const headerHeight = header ? header.getBoundingClientRect().height : 0;
        const scrollGap = 14;

        let targetTop = 0;

        if (isMobileLayout()) {
          const selector = link.getAttribute('href');
          const target = selector && selector.startsWith('#')
            ? document.querySelector(selector)
            : null;

          targetTop = target
            ? Math.max(0, window.scrollY + target.getBoundingClientRect().top - headerHeight - 8)
            : 0;

          closeMobileMenu();
        } else {
          const y = Number(link.dataset.y || 0);
          targetTop = y === 0
            ? 0
            : Math.max(0, y * stageScale - headerHeight - scrollGap);
        }

        window.scrollTo({
          top: targetTop,
          behavior: 'smooth'
        });
      });
    });



    function toggleMobileMenu() {
      const menu = document.getElementById('mobile-menu');
      const toggle = document.getElementById('mobile-menu-toggle');
      if (!menu || !toggle) return;

      const shouldOpen = !menu.classList.contains('is-open');
      menu.classList.toggle('is-open', shouldOpen);
      toggle.classList.toggle('is-open', shouldOpen);
      toggle.setAttribute('aria-expanded', String(shouldOpen));
      toggle.setAttribute('aria-label', shouldOpen ? 'Закрыть меню' : 'Открыть меню');
      menu.setAttribute('aria-hidden', String(!shouldOpen));
      document.body.classList.toggle('mobile-menu-open', shouldOpen);
    }

    function closeMobileMenu() {
      const menu = document.getElementById('mobile-menu');
      const toggle = document.getElementById('mobile-menu-toggle');
      if (!menu || !toggle) return;

      menu.classList.remove('is-open');
      toggle.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Открыть меню');
      menu.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('mobile-menu-open');
    }


    const mobileContactsData = {
      lenina: {
        title: 'Ленина, 15',
        hours: 'Будни: 08:00–21:00<br>Выходные и праздники: 09:00–21:00',
        phoneText: '+7 (922) 733-03-30',
        phoneHref: 'tel:+79227330330',
        note: 'Предзаказ тортов, десертов и актуальное наличие — в сообщениях сообщества VK, TG/MAX или по телефону.'
      },
      zababakhina: {
        title: 'Забабахина, 42',
        hours: 'Будни: 08:00–21:00<br>Выходные и праздники: 09:00–21:00',
        phoneText: '+7 (922) 720-02-20',
        phoneHref: 'tel:+79227200220',
        note: 'Предзаказ тортов, десертов и актуальное наличие — в сообщениях сообщества VK, TG/MAX или по телефону.'
      }
    };

    function switchMobileContact(key, button) {
      const data = mobileContactsData[key];
      if (!data) return;

      const title = document.getElementById('mobile-contact-title');
      const hours = document.getElementById('mobile-contact-hours');
      const phone = document.getElementById('mobile-contact-phone');
      const note = document.getElementById('mobile-contact-note');

      if (title) title.textContent = data.title;
      if (hours) hours.innerHTML = data.hours;
      if (phone) {
        phone.textContent = data.phoneText;
        phone.href = data.phoneHref;
      }
      if (note) note.textContent = data.note;

      document.querySelectorAll('.contact-mobile-tab').forEach(tab => {
        const isActive = tab === button;
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', String(isActive));
      });
    }

    const ORDER_DELIVERY_PRICE = 150;
    let orderProducts = [];
    let orderProductsLoaded = false;
    let pendingOrderQuery = '';

    function getTomorrowISO() {
      const date = new Date();
      date.setDate(date.getDate() + 1);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }

    function normalizeOrderQuery(value) {
      return String(value || '')
        .toLowerCase()
        .replace(/ё/g, 'е')
        .replace(/[«»"']/g, '')
        .trim();
    }

    async function ensureOrderProductsLoaded() {
      if (orderProductsLoaded) {
        renderOrderProductOptions();
        return;
      }

      const list = document.getElementById('order-product-list');

      if (list) {
        list.innerHTML =
          '<p class="order-product-loading">Загрузка товаров...</p>';
      }

      try {
        const response = await fetch(
          '/api/products/available/?format=json'
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const products = await response.json();

        orderProducts = products
          .filter(product =>
            product &&
            product.id &&
            product.name &&
            product.price !== null &&
            product.price !== undefined
          )
          .map(product => ({
            id: String(product.id),
            name: product.name,
            price: Number(product.price),
            category: product.category?.name || '',
          }))
          .filter(product =>
            Number.isFinite(product.price)
          );

        orderProductsLoaded = true;

        renderOrderProductOptions();

      } catch (error) {
        console.error(
          'Не удалось загрузить товары для формы заказа.',
          error
        );

        orderProducts = [];
        orderProductsLoaded = false;

        if (list) {
          list.innerHTML =
            '<p class="order-product-empty">' +
            'Не удалось загрузить товары. ' +
            'Попробуйте закрыть форму и открыть её снова.' +
            '</p>';
        }

        updateOrderTotal();
      }
    }

    function getCheckedOrderProductIds() {
      return new Set(
        Array.from(document.querySelectorAll('#order-product-list input[type="checkbox"]:checked'))
          .map(input => input.value)
      );
    }

    function getOrderProductQuantityMap() {
      const quantities = new Map();

      document
        .querySelectorAll('#order-product-list .order-product-quantity-input')
        .forEach(input => {
          const productId = input.dataset.productId;
          const quantity = Math.max(1, Math.min(50, Number(input.value) || 1));
          if (productId) quantities.set(productId, quantity);
        });

      return quantities;
    }

    function setOrderProductQuantity(row, quantity) {
      const input = row?.querySelector('.order-product-quantity-input');
      if (!input) return;

      const safeQuantity = Math.max(1, Math.min(50, Number(quantity) || 1));
      input.value = String(safeQuantity);
      updateOrderTotal();
    }

    function syncOrderProductRowState(row) {
      const checkbox = row?.querySelector('input[type="checkbox"]');
      const quantityInput = row?.querySelector('.order-product-quantity-input');

      if (!checkbox || !quantityInput) return;

      row.classList.toggle('is-selected', checkbox.checked);
      quantityInput.disabled = !checkbox.checked;

      row
        .querySelectorAll('.order-quantity-button')
        .forEach(button => {
          button.disabled = !checkbox.checked;
        });
    }

    function renderOrderProductOptions() {
      const list = document.getElementById('order-product-list');
      if (!list) return;

      const checkedIds = getCheckedOrderProductIds();
      const savedQuantities = getOrderProductQuantityMap();
      list.innerHTML = '';

      if (!orderProducts.length) {
        list.innerHTML = '<p class="order-product-empty">Сейчас нет десертов, доступных для заказа.</p>';
        updateOrderTotal();
        return;
      }

      orderProducts.forEach((product, index) => {
        const row = document.createElement('div');
        row.className = 'order-product-option';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'products';
        checkbox.value = product.id;
        checkbox.dataset.index = String(index);
        checkbox.id = `order-product-${index}`;
        checkbox.checked = checkedIds.has(product.id);

        const name = document.createElement('label');
        name.className = 'order-product-name';
        name.htmlFor = checkbox.id;
        name.textContent = product.name;

        const price = document.createElement('span');
        price.className = 'order-product-option-price';
        price.textContent = formatPrice(product.price);

        const quantity = document.createElement('div');
        quantity.className = 'order-product-quantity';
        quantity.setAttribute('aria-label', `Количество: ${product.name}`);

        const minus = document.createElement('button');
        minus.type = 'button';
        minus.className = 'order-quantity-button';
        minus.textContent = '−';
        minus.setAttribute('aria-label', `Уменьшить количество: ${product.name}`);

        const quantityInput = document.createElement('input');
        quantityInput.type = 'number';
        quantityInput.className = 'order-product-quantity-input';
        quantityInput.min = '1';
        quantityInput.max = '50';
        quantityInput.step = '1';
        quantityInput.inputMode = 'numeric';
        quantityInput.dataset.productId = product.id;
        quantityInput.value = String(savedQuantities.get(product.id) || 1);
        quantityInput.setAttribute('aria-label', `Количество товара ${product.name}`);

        const plus = document.createElement('button');
        plus.type = 'button';
        plus.className = 'order-quantity-button';
        plus.textContent = '+';
        plus.setAttribute('aria-label', `Увеличить количество: ${product.name}`);

        minus.addEventListener('click', () => {
          setOrderProductQuantity(row, Number(quantityInput.value) - 1);
        });

        plus.addEventListener('click', () => {
          setOrderProductQuantity(row, Number(quantityInput.value) + 1);
        });

        quantityInput.addEventListener('change', () => {
          setOrderProductQuantity(row, quantityInput.value);
        });

        quantityInput.addEventListener('input', () => {
          const value = Number(quantityInput.value);
          if (Number.isFinite(value) && value >= 1 && value <= 50) {
            updateOrderTotal();
          }
        });

        checkbox.addEventListener('change', () => {
          if (checkbox.checked && Number(quantityInput.value) < 1) {
            quantityInput.value = '1';
          }
          syncOrderProductRowState(row);
          updateOrderTotal();
        });

        quantity.append(minus, quantityInput, plus);
        row.append(checkbox, name, price, quantity);
        list.appendChild(row);

        syncOrderProductRowState(row);
      });

      if (pendingOrderQuery) {
        selectOrderProductByQuery(pendingOrderQuery);
      }

      updateOrderTotal();
    }

    function findOrderProductIndexByQuery(query) {
      const normalized = normalizeOrderQuery(query);
      if (!normalized) return -1;

      const canonicalize = value => normalizeOrderQuery(value)
        .replace(/\bразмер\b/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

      const canonicalQuery = canonicalize(query);

      // 1. Сначала ищем точное полное название товара.
      let index = orderProducts.findIndex(product =>
        normalizeOrderQuery(product.name) === normalized
      );

      if (index >= 0) return index;

      // 2. Позволяем совпасть "Муссовый торт S"
      //    с "Муссовый торт размер S", но не с другим тортом.
      index = orderProducts.findIndex(product =>
        canonicalize(product.name) === canonicalQuery
      );

      if (index >= 0) return index;

      // 3. Последний безопасный вариант: должны совпасть ВСЕ
      //    значимые слова, а не одно слово вроде "торт".
      const keywords = canonicalQuery
        .split(/\s+/)
        .filter(Boolean);

      if (!keywords.length) return -1;

      return orderProducts.findIndex(product => {
        const haystack = canonicalize(`${product.name} ${product.category || ''}`);
        return keywords.every(word => haystack.includes(word));
      });
    }

    function selectOrderProductByQuery(query) {
      if (!orderProducts.length) return;

      const index = findOrderProductIndexByQuery(query);
      if (index < 0) return;

      const checkbox = document.querySelector(
        `#order-product-list input[data-index="${index}"]`
      );

      if (checkbox) {
        checkbox.checked = true;
        const row = checkbox.closest('.order-product-option');
        syncOrderProductRowState(row);
        row?.scrollIntoView({
          block: 'nearest',
          behavior: 'smooth'
        });
        updateOrderTotal();
      }
    }

    function openOrderModal(productQuery = '') {
      const modal = document.getElementById('order-modal');
      if (!modal) return;

      pendingOrderQuery = productQuery || '';

      const dateInput = document.getElementById('order-date');
      if (dateInput) {
        const tomorrow = getTomorrowISO();
        dateInput.min = tomorrow;
        if (!dateInput.value || dateInput.value < tomorrow) {
          dateInput.value = tomorrow;
        }
      }

      const message = document.getElementById('order-form-message');
      if (message) {
        message.textContent = '';
        message.className = 'order-form-message';
      }

      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('modal-open');

      ensureOrderProductsLoaded().then(() => {
        if (pendingOrderQuery) selectOrderProductByQuery(pendingOrderQuery);
      });

      updateOrderDeliveryFields();
      updateOrderTotal();

      setTimeout(() => {
        document.getElementById('order-name')?.focus({ preventScroll: true });
      }, 60);
    }

    function resetOrderForm() {
      const form = document.getElementById('order-form');
      if (form) form.reset();

      /* Сбрасываем выбранные десерты, включая позицию,
         которая могла автоматически отмечаться после нажатия на цену. */
      document
        .querySelectorAll('#order-product-list .order-product-option')
        .forEach(row => {
          const checkbox = row.querySelector('input[type="checkbox"]');
          const quantityInput = row.querySelector('.order-product-quantity-input');

          if (checkbox) checkbox.checked = false;
          if (quantityInput) quantityInput.value = '1';

          syncOrderProductRowState(row);
        });

      pendingOrderQuery = '';

      const submitButton = document.getElementById('order-submit');
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = 'Оставить заявку';
      }

      const message = document.getElementById('order-form-message');
      if (message) {
        message.textContent = '';
        message.className = 'order-form-message';
      }

      const productList = document.getElementById('order-product-list');
      if (productList) productList.scrollTop = 0;

      const panel = document.querySelector('.order-modal-panel');
      if (panel) panel.scrollTop = 0;

      updateOrderDeliveryFields();
      updateOrderTotal();
    }

    function closeOrderModal() {
      const modal = document.getElementById('order-modal');
      if (!modal) return;

      const resultOverlay = document.getElementById('order-result-overlay');
      if (resultOverlay) {
        resultOverlay.className = 'order-result-overlay';
        resultOverlay.setAttribute('aria-hidden', 'true');
      }

      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('modal-open');

      resetOrderForm();
    }

    function updateOrderDeliveryFields() {
      const isDelivery = document.getElementById('order-delivery')?.checked;
      const pickupField = document.getElementById('order-pickup-field');
      const addressField = document.getElementById('order-address-field');
      const pickupSelect = document.getElementById('order-pickup-location');
      const addressInput = document.getElementById('order-address');

      pickupField?.classList.toggle('is-visible', !isDelivery);
      addressField?.classList.toggle('is-visible', Boolean(isDelivery));

      if (pickupSelect) pickupSelect.required = !isDelivery;
      if (addressInput) addressInput.required = Boolean(isDelivery);

      updateOrderTotal();
    }

    function getSelectedOrderProducts() {
      return Array.from(
        document.querySelectorAll('#order-product-list input[type="checkbox"]:checked')
      )
        .map(input => {
          const index = Number(input.dataset.index);
          const product = Number.isInteger(index) ? orderProducts[index] || null : null;
          if (!product) return null;

          const row = input.closest('.order-product-option');
          const quantityInput = row?.querySelector('.order-product-quantity-input');
          const quantity = Math.max(
            1,
            Math.min(50, Number(quantityInput?.value) || 1)
          );

          return {
            ...product,
            quantity
          };
        })
        .filter(Boolean);
    }

    function updateOrderTotal() {
      const products = getSelectedOrderProducts();
      const productsTotal = products.reduce(
        (sum, product) => (
          sum + Number(product.price || 0) * Number(product.quantity || 1)
        ),
        0
      );

      const totalQuantity = products.reduce(
        (sum, product) => sum + Number(product.quantity || 1),
        0
      );

      const isDelivery = document.getElementById('order-delivery')?.checked;
      const deliveryPrice = isDelivery ? ORDER_DELIVERY_PRICE : 0;

      const productPriceEl = document.getElementById('order-product-price');
      const deliveryPriceEl = document.getElementById('order-delivery-price');
      const totalEl = document.getElementById('order-total');
      const summaryLabel = document.getElementById('order-products-summary-label');

      if (summaryLabel) {
        summaryLabel.textContent = products.length
          ? `Десерты (${totalQuantity} шт.)`
          : 'Десерты';
      }

      if (productPriceEl) {
        productPriceEl.textContent = products.length ? formatPrice(productsTotal) : '—';
      }

      if (deliveryPriceEl) {
        deliveryPriceEl.textContent = deliveryPrice ? formatPrice(deliveryPrice) : '0 ₽';
      }

      if (totalEl) {
        totalEl.textContent = products.length
          ? formatPrice(productsTotal + deliveryPrice)
          : '—';
      }
    }

    function isValidOrderPhone(value) {
      const digits = String(value || '').replace(/\D/g, '');
      return digits.length >= 10 && digits.length <= 11;
    }

    function openOrderResultModal() {
      const overlay = document.getElementById('order-result-overlay');
      const icon = document.getElementById('order-result-icon');
      const title = document.getElementById('order-result-title');
      const text = document.getElementById('order-result-text');

      if (!overlay || !icon || !title || !text) return;

      overlay.className = 'order-result-overlay is-open is-processing';
      overlay.setAttribute('aria-hidden', 'false');

      icon.innerHTML = '<span class="order-result-spinner"></span>';
      title.textContent = 'Подождите';
      text.textContent = 'Заявка обрабатывается…';
    }

    function showOrderResultSuccess() {
      const overlay = document.getElementById('order-result-overlay');
      const icon = document.getElementById('order-result-icon');
      const title = document.getElementById('order-result-title');
      const text = document.getElementById('order-result-text');
      const closeButton = document.getElementById('order-result-close');

      if (!overlay || !icon || !title || !text) return;

      overlay.className = 'order-result-overlay is-open is-complete is-success';
      icon.textContent = '✓';
      title.textContent = 'Заявка отправлена';
      text.textContent = 'Спасибо! Мы свяжемся с вами для подтверждения.';

      setTimeout(() => closeButton?.focus({ preventScroll: true }), 50);
    }

    function showOrderResultError() {
      const overlay = document.getElementById('order-result-overlay');
      const icon = document.getElementById('order-result-icon');
      const title = document.getElementById('order-result-title');
      const text = document.getElementById('order-result-text');
      const closeButton = document.getElementById('order-result-close');

      if (!overlay || !icon || !title || !text) return;

      overlay.className = 'order-result-overlay is-open is-complete is-error';
      icon.textContent = '!';
      title.textContent = 'Не получилось отправить заявку';
      text.textContent = 'Попробуйте позже.';

      setTimeout(() => closeButton?.focus({ preventScroll: true }), 50);
    }

    function closeOrderResultModal() {
      const overlay = document.getElementById('order-result-overlay');

      if (overlay) {
        overlay.className = 'order-result-overlay';
        overlay.setAttribute('aria-hidden', 'true');
      }

      closeOrderModal();
    }

    async function handleOrderSubmit(event) {
      event.preventDefault();

      const form = event.currentTarget;
      const message = document.getElementById('order-form-message');
      const phone = document.getElementById('order-phone');
      const products = getSelectedOrderProducts();
      const submitButton = document.getElementById('order-submit');

      message.className = 'order-form-message';
      message.textContent = '';

      if (!orderProductsLoaded) {
        message.classList.add('error');
        message.textContent =
          'Не удалось загрузить товары. ' +
          'Закройте форму и попробуйте открыть её снова.';

        document
          .getElementById('order-product-list')
          ?.scrollIntoView({
            block: 'nearest'
          });

        return;
      }

      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      if (!isValidOrderPhone(phone.value)) {
        message.classList.add('error');
        message.textContent = 'Проверьте номер телефона — в нём должно быть 10–11 цифр.';
        phone.focus();
        return;
      }

      if (!products.length) {
        message.classList.add('error');
        message.textContent = 'Выберите хотя бы один десерт.';
        document.getElementById('order-product-list')?.scrollIntoView({ block: 'nearest' });
        return;
      }

      const isDelivery = document.getElementById('order-delivery')?.checked;

      const payload = {
        name: document.getElementById('order-name')?.value.trim() || '',
        phone: phone.value.trim(),
        date: document.getElementById('order-date')?.value || '',
        time: document.getElementById('order-time')?.value || '',
        items: products.map(product => ({
          product_id: product.id,
          quantity: product.quantity
        })),
        delivery_type: isDelivery ? 'delivery' : 'pickup',
        pickup_location: isDelivery
          ? null
          : (document.getElementById('order-pickup-location')?.value || null),
        address: isDelivery
          ? (document.getElementById('order-address')?.value.trim() || null)
          : null,
        website: document.getElementById('order-website')?.value || '',
        consent: Boolean(document.getElementById('order-consent')?.checked)
      };

      if (submitButton) {
        submitButton.disabled = true;
      }

      openOrderResultModal();

      try {
        const response = await fetch('/api/orders/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        let data = {};
        try {
          data = await response.json();
        } catch (_) {}

        if (!response.ok) {
          throw new Error(
            typeof data.detail === 'string'
              ? data.detail
              : `HTTP ${response.status}`
          );
        }

        showOrderResultSuccess();
      } catch (error) {
        console.error('Ошибка отправки заявки:', error);
        showOrderResultError();
      }
    }

    document.getElementById('order-modal')?.addEventListener('click', event => {
      const resultOverlay = document.getElementById('order-result-overlay');

      if (resultOverlay?.classList.contains('is-open')) {
        return;
      }

      if (event.target.id === 'order-modal') closeOrderModal();
    });

    document.getElementById('order-result-overlay')?.addEventListener('click', event => {
      const overlay = event.currentTarget;

      if (
        event.target === overlay &&
        overlay.classList.contains('is-complete')
      ) {
        closeOrderResultModal();
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;

      const legalModal = document.getElementById('legal-modal');
      if (legalModal?.classList.contains('is-open')) {
        closeLegalModal();
        return;
      }

      const resultOverlay = document.getElementById('order-result-overlay');

      if (resultOverlay?.classList.contains('is-open')) {
        if (resultOverlay.classList.contains('is-complete')) {
          closeOrderResultModal();
        }
        return;
      }

      if (document.getElementById('order-modal')?.classList.contains('is-open')) {
        closeOrderModal();
      }
    });

    document.getElementById('order-pickup')?.addEventListener('change', updateOrderDeliveryFields);
    document.getElementById('order-delivery')?.addEventListener('change', updateOrderDeliveryFields);
    document.getElementById('order-form')?.addEventListener('submit', handleOrderSubmit);

    const orderConsentCheckbox = document.getElementById('order-consent');

    orderConsentCheckbox?.addEventListener('invalid', () => {
      if (!orderConsentCheckbox.checked) {
        orderConsentCheckbox.setCustomValidity(
          'Чтобы продолжить, дайте согласие на обработку персональных данных'
        );
      }
    });

    orderConsentCheckbox?.addEventListener('change', () => {
      orderConsentCheckbox.setCustomValidity('');
    });


    let legalModalPreviousFocus = null;

    function formatLegalPublishedAt(value) {
      if (!value) return '';

      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '';

      return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }).format(date);
    }

    async function openLegalDocument({
      url,
      fallbackTitle,
      documentLabel
    }) {
      const modal = document.getElementById('legal-modal');
      const title = document.getElementById('legal-modal-title');
      const meta = document.getElementById('legal-modal-meta');
      const text = document.getElementById('legal-modal-text');

      if (!modal || !title || !meta || !text) return;

      legalModalPreviousFocus = document.activeElement;

      title.textContent = fallbackTitle;
      meta.textContent = '';
      text.className = 'legal-modal-text';
      text.textContent = 'Загрузка документа…';

      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('modal-open');

      try {
        const response = await fetch(url, {
          headers: {
            'Accept': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        title.textContent = String(data.title || fallbackTitle);
        text.textContent = String(data.text || 'Текст документа пока не опубликован.');

        const metaParts = [];

        if (data.version) {
          metaParts.push(`Версия ${String(data.version)}`);
        }

        const publishedAt = formatLegalPublishedAt(data.published_at);
        if (publishedAt) {
          metaParts.push(`опубликовано ${publishedAt}`);
        }

        meta.textContent = metaParts.join(' · ');
      } catch (error) {
        console.error(`Не удалось загрузить ${documentLabel}:`, error);
        meta.textContent = '';
        text.className = 'legal-modal-text is-error';
        text.textContent = 'Не удалось загрузить документ. Попробуйте ещё раз позже.';
      }
    }

    function openPrivacyPolicy() {
      return openLegalDocument({
        url: '/api/legal/privacy-policy/',
        fallbackTitle: 'Политика обработки персональных данных',
        documentLabel: 'политику обработки персональных данных'
      });
    }

    function openConsentText() {
      return openLegalDocument({
        url: '/api/legal/consent/',
        fallbackTitle: 'Согласие на обработку персональных данных',
        documentLabel: 'текст согласия'
      });
    }

    function closeLegalModal() {
      const modal = document.getElementById('legal-modal');
      if (!modal) return;

      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');

      const orderModalOpen =
        document.getElementById('order-modal')?.classList.contains('is-open');

      if (!orderModalOpen) {
        document.body.classList.remove('modal-open');
      }

      if (
        legalModalPreviousFocus &&
        typeof legalModalPreviousFocus.focus === 'function'
      ) {
        legalModalPreviousFocus.focus({ preventScroll: true });
      }

      legalModalPreviousFocus = null;
    }

    document.getElementById('legal-modal')?.addEventListener('click', event => {
      if (event.target.id === 'legal-modal') {
        closeLegalModal();
      }
    });

    function formatPrice(value) {
      const number = Number(value);
      if (Number.isFinite(number)) return `${Math.round(number)} Руб.`;
      return `${value} Руб.`;
    }

    function looksSavory(product) {
      const text = `${product?.name || ''} ${product?.category?.name || ''}`.toLowerCase();
      return ['сэндвич', 'скрэмбл', 'каша', 'сырнич', 'суп', 'боул', 'цыплен', 'лосос', 'завтрак', 'сыт'].some(word => text.includes(word));
    }

    function moveShowcaseLine(button) {
      const line = document.getElementById('showcase-active-line');
      if (!line || !button) return;
      const isSecond = button.classList.contains('two');
      line.style.left = isSecond ? '1301px' : '439px';
      line.style.width = isSecond ? '213px' : '153px';
    }

    function resizeShowcaseForContent() {
      const section = document.querySelector('.showcases');
      const card = document.querySelector('.showcase-card');
      const price = document.querySelector('.price-section');
      const products = document.querySelector('.products-section');
      const contacts = document.querySelector('.contacts-section');
      const footer = document.querySelector('.site-footer');

      if (!section || !card || !price || !products || !contacts || !footer) {
        return;
      }

      if (isMobileLayout()) {
        showcaseDesktopDelta = 0;

        section.style.removeProperty('height');
        price.style.removeProperty('top');
        products.style.removeProperty('top');
        contacts.style.removeProperty('top');
        footer.style.removeProperty('top');

        fitDesignStage();
        return;
      }

      // The beige card grows naturally with its contents.
      // Only when it becomes taller than the original Figma space do we
      // push all following desktop sections down by the same amount.
      const requiredSectionHeight = Math.max(
        DESKTOP_LAYOUT_BASE.showcaseHeight,
        card.offsetTop +
          card.scrollHeight +
          DESKTOP_LAYOUT_BASE.showcaseBottomPadding
      );

      showcaseDesktopDelta =
        requiredSectionHeight - DESKTOP_LAYOUT_BASE.showcaseHeight;

      section.style.height = `${requiredSectionHeight}px`;
      price.style.top =
        `${DESKTOP_LAYOUT_BASE.priceTop + showcaseDesktopDelta}px`;
      products.style.top =
        `${DESKTOP_LAYOUT_BASE.productsTop + showcaseDesktopDelta}px`;
      contacts.style.top =
        `${DESKTOP_LAYOUT_BASE.contactsTop + showcaseDesktopDelta}px`;
      footer.style.top =
        `${DESKTOP_LAYOUT_BASE.footerTop + showcaseDesktopDelta}px`;

      fitDesignStage();
    }

    async function loadShowcase(address, button = null) {
      document.querySelectorAll('.showcase-tab').forEach(tab => tab.classList.remove('active'));
      const activeButton = button || document.querySelector('.showcase-tab.one');
      if (activeButton) activeButton.classList.add('active');
      moveShowcaseLine(activeButton);

      const dessertBox = document.getElementById('showcase-desserts');
      const foodBox = document.getElementById('showcase-food');
      dessertBox.innerHTML = '';
      foodBox.innerHTML = '';

      try {
        const response = await fetch('/api/showcase/?format=json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const items = await response.json();
        const filtered = items.filter(item => (item.pickup_location?.address || '').includes(address));
        const desserts = filtered.filter(item => !looksSavory(item.product));
        const food = filtered.filter(item => looksSavory(item.product));

        const render = (target, list) => {
          if (!list.length) {
            target.innerHTML = '<p class="showcase-empty">Актуальный ассортимент появится здесь.</p>';
            return;
          }
          list.forEach(item => {
            const row = document.createElement('div');
            row.className = 'showcase-row';

            const name = document.createElement('span');
            name.textContent = String(item?.product?.name || '');

            const price = document.createElement('span');
            price.className = 'price';
            price.textContent = formatPrice(item?.product?.price);

            row.append(name, price);
            target.appendChild(row);
          });
        };

        render(dessertBox, desserts);
        render(foodBox, food);
        syncContactPhones(filtered);

        requestAnimationFrame(() => {
          resizeShowcaseForContent();
        });
      } catch (error) {
        console.error('Ошибка загрузки витрины:', error);
        dessertBox.innerHTML = '<p class="showcase-empty">Не удалось загрузить витрину.</p>';
        foodBox.innerHTML = '<p class="showcase-empty">Не удалось загрузить витрину.</p>';

        requestAnimationFrame(() => {
          resizeShowcaseForContent();
        });
      }
    }

    function formatContactPhone(phone) {
      const digits = String(phone || '').replace(/\D/g, '');

      let normalized = digits;

      if (normalized.length === 11 && normalized.startsWith('8')) {
        normalized = `7${normalized.slice(1)}`;
      }

      if (normalized.length === 10) {
        normalized = `7${normalized}`;
      }

      if (normalized.length === 11 && normalized.startsWith('7')) {
        return `+7 (${normalized.slice(1, 4)}) ${normalized.slice(4, 7)}-${normalized.slice(7, 9)}-${normalized.slice(9, 11)}`;
      }

      return String(phone || '');
    }

    function syncContactPhones(items) {
      items.forEach(item => {
        const location = item.pickup_location;
        if (!location?.phone || !location?.address) return;

        const digits = String(location.phone).replace(/\D/g, '');
        const normalizedDigits =
          digits.length === 11 && digits.startsWith('8')
            ? `7${digits.slice(1)}`
            : digits.length === 10
              ? `7${digits}`
              : digits;

        const target = location.address.includes('Ленина')
          ? document.getElementById('contact-phone-lenina')
          : location.address.includes('Забабахина')
            ? document.getElementById('contact-phone-zababakhina')
            : null;

        if (target) {
          target.href = normalizedDigits ? `tel:+${normalizedDigits}` : '#';
          target.textContent = formatContactPhone(location.phone);
        }
      });
    }

    function getProductImageKey(imageUrl) {
      if (!imageUrl || !String(imageUrl).trim()) return '';
      try {
        return new URL(imageUrl, window.location.origin).pathname.toLowerCase();
      } catch (error) {
        return String(imageUrl).split('?')[0].split('#')[0].trim().toLowerCase();
      }
    }

    function getProductCardTitle(product) {
      return product?.display_name || product?.name || 'Десерт';
    }

    function getSafeHttpUrl(value, { allowSameOrigin = true } = {}) {
      const raw = String(value || '').trim().replaceAll('\\', '/');
      if (!raw) return '';

      try {
        const parsed = new URL(raw, window.location.origin);

        if (!['http:', 'https:'].includes(parsed.protocol)) {
          return '';
        }

        if (!allowSameOrigin && parsed.origin === window.location.origin) {
          return '';
        }

        return parsed.href;
      } catch (_) {
        return '';
      }
    }

    function getSafeVkUrl(value) {
      const safeUrl = getSafeHttpUrl(value, { allowSameOrigin: false });
      if (!safeUrl) return '';

      try {
        const parsed = new URL(safeUrl);
        const host = parsed.hostname.toLowerCase();

        const isVkHost =
          host === 'vk.ru' ||
          host.endsWith('.vk.ru') ||
          host === 'vk.com' ||
          host.endsWith('.vk.com');

        return isVkHost ? safeUrl : '';
      } catch (_) {
        return '';
      }
    }

    function normalizeProductImageUrl(imageUrl) {
      return getSafeHttpUrl(imageUrl);
    }

    async function loadProducts() {
      const track = document.getElementById('products');
      track.innerHTML = '';

      try {
        const response = await fetch('/api/products/?format=json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const products = await response.json();

        /* Сохраняем исходный порядок товаров, но всю категорию «Сытная еда»
           переносим в самый конец карусели. sort() в современных браузерах стабилен,
           поэтому порядок внутри каждой из двух групп не меняется. */
        const sortedProducts = [...products].sort((a, b) => {
          const aIsSavory = a?.category?.slug === 'savory-food' || a?.category?.name === 'Сытная еда';
          const bIsSavory = b?.category?.slug === 'savory-food' || b?.category?.name === 'Сытная еда';
          return Number(aIsSavory) - Number(bIsSavory);
        });

        /* В карусели показываем только один товар для каждого отображаемого имени.
           Сравниваем именно то название, которое видит пользователь: display_name,
           а при его отсутствии — обычное name. Регистр и лишние пробелы не учитываем. */
        const seenDisplayNames = new Set();

        sortedProducts
          .filter(product => Boolean(normalizeProductImageUrl(product?.image_url)))
          .filter(product => {
            const displayNameKey = getProductCardTitle(product)
              .trim()
              .replace(/\s+/g, ' ')
              .toLocaleLowerCase('ru-RU');

            if (seenDisplayNames.has(displayNameKey)) return false;

            seenDisplayNames.add(displayNameKey);
            return true;
          })
          .forEach(product => {
            const imageUrl = normalizeProductImageUrl(product.image_url);
            const title = String(getProductCardTitle(product));
            const vkUrl = getSafeVkUrl(product.vk_url);

            const card = document.createElement(vkUrl ? 'a' : 'div');
            card.className = 'product-card';

            if (vkUrl) {
              card.href = vkUrl;
              card.target = '_blank';
              card.rel = 'noopener noreferrer';
              card.setAttribute('aria-label', `${title} — открыть товар во ВКонтакте`);
            }

            const priceText =
              product.price !== null && product.price !== undefined
                ? formatPrice(product.price)
                : '';

            const imageWrap = document.createElement('div');
            imageWrap.className = 'product-card-image';

            const image = document.createElement('img');
            image.src = imageUrl;
            image.alt = title;
            image.loading = 'lazy';
            image.decoding = 'async';

            const heading = document.createElement('h3');
            heading.textContent = title;

            const price = document.createElement('p');
            price.textContent = priceText;

            imageWrap.appendChild(image);
            card.append(imageWrap, heading, price);
            track.appendChild(card);
          });

        productOffset = 0;
        track.style.transform = 'translateX(0)';
      } catch (error) {
        console.error('Ошибка загрузки товаров:', error);
      }
    }

    function scrollProducts(direction) {
      const track = document.getElementById('products');
      const windowEl = document.querySelector('.products-window');
      if (!track || !windowEl) return;

      if (isMobileLayout()) {
        const firstCard = track.querySelector('.product-card');
        const gap = 14;
        const step = firstCard
          ? firstCard.getBoundingClientRect().width + gap
          : windowEl.clientWidth * 0.8;

        windowEl.scrollBy({
          left: direction * step,
          behavior: 'smooth'
        });
        return;
      }

      const count = track.children.length;
      const visible = 5;
      const step = 330;
      const maxOffset = Math.max(0, (count - visible) * step);
      productOffset = Math.min(maxOffset, Math.max(0, productOffset + direction * step));
      track.style.transform = `translateX(${-productOffset}px)`;
    }

    function contactDisplayUrl(url) {
      try {
        const parsed = new URL(url);
        const path = parsed.pathname.replace(/\/$/, '');
        return `${parsed.hostname}${path}`;
      } catch (_) {
        return url;
      }
    }

    async function loadFooterContacts() {
      const links = Array.from(
        document.querySelectorAll('[data-contact-type]')
      );

      links.forEach(link => {
        link.dataset.contactReady = 'false';
        link.addEventListener('click', event => {
          if (link.dataset.contactReady !== 'true') {
            event.preventDefault();
          }
        });
      });

      try {
        const response = await fetch('/api/contacts/');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const contacts = await response.json();
        const byType = new Map(
          contacts.map(contact => [
            String(contact.type || '').toLowerCase(),
            contact
          ])
        );

        links.forEach(link => {
          const type = String(link.dataset.contactType || '').toLowerCase();
          const contact = byType.get(type);

          const safeContactUrl = getSafeHttpUrl(
            contact?.value,
            { allowSameOrigin: false }
          );

          if (!safeContactUrl) {
            link.dataset.contactReady = 'false';
            link.removeAttribute('href');
            link.removeAttribute('target');
            link.removeAttribute('rel');
            return;
          }

          link.href = safeContactUrl;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.dataset.contactReady = 'true';

          const label = contact.title || link.textContent.trim() || type.toUpperCase();
          link.textContent = `${label} · ${contactDisplayUrl(safeContactUrl)}`;
          link.setAttribute(
            'aria-label',
            `${label} — открыть в новом окне`
          );
        });
      } catch (error) {
        console.error('Ошибка загрузки контактов футера:', error);
      }
    }

    function initRevealAnimations() {
      const blocks = document.querySelectorAll('.reveal-block');

      if (isMobileLayout()) {
        blocks.forEach(block => block.classList.add('is-visible'));
        document.querySelector('.contacts-section')?.classList.add('contacts-footer-visible');
        document.querySelector('.site-footer')?.classList.add('contacts-footer-visible');
        return;
      }

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.08,
        rootMargin: '0px 0px -4% 0px'
      });

      blocks.forEach(block => {
        observer.observe(block);
      });

      const contacts = document.querySelector('.contacts-section');
      const footer = document.querySelector('.site-footer');
      if (contacts && footer) {
        const contactsObserver = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              contacts.classList.add('contacts-footer-visible');
              footer.classList.add('contacts-footer-visible');
              contactsObserver.unobserve(contacts);
            }
          });
        }, {
          threshold: 0.08,
          rootMargin: '0px 0px -4% 0px'
        });
        contactsObserver.observe(contacts);
      }
    }

    loadShowcase('Ленина');
    loadProducts();
    loadFooterContacts();
    initRevealAnimations();
