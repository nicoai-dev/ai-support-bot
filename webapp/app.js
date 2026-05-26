// Инициализация Telegram WebApp SDK
const tg = window.Telegram.WebApp;

// Расширяем приложение на весь экран телефона
tg.expand();

// Сообщаем Telegram, что WebApp загружен
tg.ready();

// === БЕЗОПАСНОСТЬ: экранирование HTML для защиты от XSS ===
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Фиксируем цвета для темной темы, игнорируя системную тему Telegram
document.documentElement.style.setProperty('--bg-color', '#0f0c1b');
document.documentElement.style.setProperty('--text-color', '#f3f4f6');
document.documentElement.style.setProperty('--text-muted', '#9ca3af');

try {
    tg.setHeaderColor('#0f0c1b');
    tg.setBackgroundColor('#0f0c1b');
} catch (e) {
    console.error("Error setting Telegram colors:", e);
}

// UI элементы
const greetingEl = document.getElementById('user-greeting');
const avatarEl = document.getElementById('user-avatar');
const catalogContainer = document.getElementById('catalog-container');
const cartBar = document.getElementById('cart-bar');
const cartCountEl = document.getElementById('cart-count');
const cartTotalEl = document.getElementById('cart-total');
const checkoutBtn = document.getElementById('btn-checkout');
const searchInput = document.getElementById('search-input');
const searchClearBtn = document.getElementById('search-clear-btn');

// Парсинг данных пользователя из Telegram с защитой от задержки инициализации SDK
function loadTelegramUser() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryFirstName = urlParams.get('first_name');
        const queryPhotoUrl = urlParams.get('photo_url') || (tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.photo_url);

        // 1. Пытаемся взять данные стандартно из SDK
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            const user = tg.initDataUnsafe.user;
            greetingEl.textContent = `Привет, ${user.first_name || 'Гость'}!`;
            
            if (queryPhotoUrl) {
                const decodedPhoto = decodeURIComponent(queryPhotoUrl);
                avatarEl.textContent = "";
                avatarEl.style.background = `url('${decodedPhoto}') center/cover no-repeat`;
            } else if (user.first_name) {
                avatarEl.textContent = user.first_name[0].toUpperCase();
                avatarEl.style.background = 'var(--primary-glow)';
            }
            return true; // Удалось загрузить
        }
        
        // 2. Фоллбек: вытаскиваем из параметров URL (для iOS и обхода багов кэша/ReplyKeyboard)
        if (queryFirstName) {
            const decodedName = decodeURIComponent(queryFirstName);
            greetingEl.textContent = `Привет, ${decodedName}!`;
            
            if (queryPhotoUrl) {
                const decodedPhoto = decodeURIComponent(queryPhotoUrl);
                avatarEl.textContent = "";
                avatarEl.style.background = `url('${decodedPhoto}') center/cover no-repeat`;
            } else {
                avatarEl.textContent = decodedName[0].toUpperCase();
                avatarEl.style.background = 'var(--primary-glow)';
            }
            return true;
        }
    } catch (e) {
        console.error("Error parsing user data:", e);
    }
    return false; // Пока не загружено
}

// Запускаем проверку
if (!loadTelegramUser()) {
    console.log("User data not ready yet, starting interval checks...");
    let attempts = 0;
    const userInterval = setInterval(() => {
        attempts++;
        if (loadTelegramUser() || attempts >= 20) {
            clearInterval(userInterval);
        }
    }, 100);
}

// Каталог загружается динамически из products.json (единый источник правды)
let PRODUCTS = [];

async function loadCatalog() {
    try {
        const response = await fetch('products.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        PRODUCTS = await response.json();
        console.log(`✅ Каталог загружен: ${PRODUCTS.length} товаров`);
        renderProducts("hardware");
    } catch (error) {
        console.error("❌ Ошибка загрузки каталога:", error);
        // Показываем сообщение об ошибке пользователю
        const catalogContainer = document.getElementById('catalog-container');
        if (catalogContainer) {
            catalogContainer.innerHTML = `
                <div style="grid-column: span 2; text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">⚠️</div>
                    <h3>Каталог временно недоступен</h3>
                    <p style="font-size: 0.85rem; margin-top: 5px;">Пожалуйста, попробуйте позже</p>
                </div>
            `;
        }
    }
}

// Локальное состояние корзины
let cart = {};

// Отрисовка товаров каталога
function renderProducts(categoryFilter = "hardware", searchQuery = "") {
    catalogContainer.innerHTML = "";
    
    let filtered = PRODUCTS;
    const query = searchQuery.trim().toLowerCase();

    if (query) {
        // Глобальный поиск по названию или описанию
        filtered = PRODUCTS.filter(p => 
            p.title.toLowerCase().includes(query) || 
            p.desc.toLowerCase().includes(query)
        );
    } else {
        // Фильтр по активной категории
        filtered = PRODUCTS.filter(p => p.category === categoryFilter);
    }

    // Если ничего не нашли
    if (filtered.length === 0) {
        catalogContainer.innerHTML = `
            <div style="grid-column: span 2; text-align: center; padding: 40px 20px; color: var(--text-muted);">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🔍</div>
                <h3>Ничего не найдено</h3>
                <p style="font-size: 0.85rem; margin-top: 5px;">Попробуйте изменить поисковый запрос</p>
            </div>
        `;
        return;
    }

    filtered.forEach(p => {
        const countInCart = cart[p.id] ? cart[p.id].count : 0;
        const isInCart = countInCart > 0;

        const card = document.createElement('div');
        card.className = `product-card ${isInCart ? 'in-cart' : ''}`;
        card.innerHTML = `
            <div class="product-card-clickable" onclick="openProductModal(${p.id})">
                <div class="product-img">${p.emoji}</div>
                <div class="product-title">${escapeHtml(p.title)}</div>
                <div class="product-desc">${escapeHtml(p.desc)}</div>
            </div>
            <div class="product-footer">
                <div class="product-price">$${escapeHtml(String(p.price))}</div>
                <button class="btn-add" onclick="addToCart(${p.id}, event)">
                    ${isInCart ? `+${countInCart}` : '+'}
                </button>
            </div>
        `;
        catalogContainer.appendChild(card);
    });
}

// Добавить в корзину
window.addToCart = function(productId, event) {
    if (event) event.stopPropagation();
    const product = PRODUCTS.find(p => p.id === productId);
    if (!product) return;

    if (cart[productId]) {
        cart[productId].count += 1;
    } else {
        cart[productId] = {
            title: product.title,
            price: product.price,
            count: 1
        };
    }

    // Легкая вибрация телефона при клике (Telegram Taptic Engine)
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }

    updateCartUI();
    renderProducts(document.querySelector('.tab-btn.active').dataset.category, searchInput.value);
    
    // Синхронизация модала, если он открыт для этого товара
    updateModalUIIfOpen(productId);
};

// Обновление состояния и высоты плавающей корзины
function updateCartUI() {
    let totalItems = 0;
    let totalPrice = 0;

    for (let id in cart) {
        totalItems += cart[id].count;
        totalPrice += cart[id].price * cart[id].count;
    }

    // Обновляем значок корзины в шапке
    const cartBadge = document.getElementById('cart-badge');
    if (cartBadge) {
        cartBadge.textContent = totalItems;
        if (totalItems > 0) {
            cartBadge.classList.add('visible');
        } else {
            cartBadge.classList.remove('visible');
        }
    }

    if (totalItems > 0) {
        cartBar.classList.add('visible');
        cartCountEl.textContent = `${totalItems} ${getNoun(totalItems, 'товар', 'товара', 'товаров')}`;
        cartTotalEl.textContent = `$${totalPrice}`;
    } else {
        cartBar.classList.remove('visible');
    }

    // Если открыт модал корзины — перерисовываем его содержимое
    if (isCartModalOpen) {
        renderCartModalItems();
    }
}

// Склонение слов
function getNoun(number, one, two, five) {
    let n = Math.abs(number);
    n %= 100;
    if (n >= 5 && n <= 20) return five;
    n %= 10;
    if (n === 1) return one;
    if (n >= 2 && n <= 4) return two;
    return five;
}

// Переключение табов категорий
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // При переключении таба сбрасываем поиск для лучшего UX
        searchInput.value = '';
        searchClearBtn.style.display = 'none';
        
        renderProducts(e.target.dataset.category);
    });
});

// Поиск товаров
searchInput.addEventListener('input', (e) => {
    const val = e.target.value;
    if (val.trim()) {
        searchClearBtn.style.display = 'flex';
    } else {
        searchClearBtn.style.display = 'none';
    }
    const activeCategory = document.querySelector('.tab-btn.active').dataset.category;
    renderProducts(activeCategory, val);
});

// Кнопка очистки поиска
searchClearBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchClearBtn.style.display = 'none';
    const activeCategory = document.querySelector('.tab-btn.active').dataset.category;
    renderProducts(activeCategory, '');
    searchInput.focus();
});


// --- ИНТЕГРАЦИЯ ДЕТАЛЬНОГО ОПИСАНИЯ ТОВАРОВ (МОДАЛ) ---
const productModal = document.getElementById('product-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalEmoji = document.getElementById('modal-product-emoji');
const modalTitle = document.getElementById('modal-product-title');
const modalBadge = document.getElementById('modal-product-badge');
const modalPrice = document.getElementById('modal-product-price');
const modalDesc = document.getElementById('modal-product-desc');
const modalQtyCount = document.getElementById('modal-qty-count');
const modalBtnAction = document.getElementById('modal-btn-action');

let activeModalProductId = null;

// Готовые премиум-описания для флагманских товаров
const FLAGSHIP_DESCRIPTIONS = {
    1: `<strong>Флагманский смартфон Apple iPhone 16 Pro Max 256GB</strong><br><br>
        Новейший шедевр от Apple в титановом корпусе космического класса. Оснащен потрясающим 6.9-дюймовым экраном Super Retina XDR с технологией ProMotion 120Hz и передовым процессором A18 Pro.<br><br>
        <strong>Ключевые преимущества:</strong><br>
        • Невероятная тройная камера 48MP с поддержкой макросъемки и 5х оптическим зумом<br>
        • Непревзойденное время автономной работы (до 33 часов воспроизведения видео)<br>
        • Кнопка Camera Control для мгновенного доступа к съемке и настройкам ИИ Apple Intelligence<br><br>
        <strong>Доставка и гарантия:</strong><br>
        • Быстрая доставка по Фиджи: 1-2 рабочих дня<br>
        • Международная доставка: 3-7 рабочих дней (в зависимости от региона)<br>
        • Официальная гарантия Nico Market: 12 месяцев.`,
    2: `<strong>Флагманский Android-смартфон Samsung Galaxy S25 Ultra 512GB</strong><br><br>
        Абсолютный лидер среди Android-устройств. Выполнен в титановом корпусе, защищен бронированным стеклом Gorilla Glass Armor и оснащен процессором Snapdragon 8 Gen 4 для беспрецедентной производительности.<br><br>
        <strong>Ключевые преимущества:</strong><br>
        • Профессиональная камера 200MP с искусственным интеллектом Galaxy AI для идеальных ночных кадров<br>
        • Встроенное перо S Pen для рисования, заметок и дистанционного управления<br>
        • Роскошный плоский экран Dynamic AMOLED 2X с пиковой яркостью 2600 нит<br><br>
        <strong>Доставка и гарантия:</strong><br>
        • Доставка по Фиджи: 1-2 рабочих дня<br>
        • Международная доставка: 3-7 рабочих дней<br>
        • Гарантия: 12 месяцев от сервисного центра Nico Market.`,
    8: `<strong>Мощнейший ноутбук Apple MacBook Pro 16" M4 Pro</strong><br><br>
        Невероятный рабочий инструмент для разработчиков, дизайнеров и видеомонтажеров. Оснащен чипом M4 Pro, который с легкостью справляется с самыми сложными проектами, компиляцией кода и рендерингом 3D.<br><br>
        <strong>Ключевые преимущества:</strong><br>
        • Огромный объем объединенной памяти 36GB RAM для безупречной многозадачности<br>
        • Дисплей Liquid Retina XDR 16.2" с экстремальным динамическим диапазоном и ProMotion<br>
        • Фантастическая автономность — до 22 часов работы без подзарядки<br><br>
        <strong>Доставка и гарантия:</strong><br>
        • Доставка по Фиджи: 2-3 рабочих дня<br>
        • Международная доставка: 5-10 рабочих дней<br>
        • Гарантия: 12 месяцев.`
};

// Функция динамической генерации красивых подробных описаний для остальных товаров
function getProductLongDescription(p) {
    if (FLAGSHIP_DESCRIPTIONS[p.id]) {
        return FLAGSHIP_DESCRIPTIONS[p.id];
    }
    
    if (p.category === 'hardware') {
        return `
            <strong>Премиальное устройство Nico Market</strong><br><br>
            Этот товар представляет собой оригинальное сертифицированное устройство с полноценной гарантией. Мы поставляем только проверенные девайсы напрямую от производителей.<br><br>
            <strong>Ключевые особенности:</strong><br>
            • ${p.desc}<br>
            • 100% Оригинальный товар в заводской упаковке<br>
            • Полная комплектация и готовность к работе из коробки<br><br>
            <strong>Доставка и гарантия:</strong><br>
            • Доставка по Фиджи: 1-2 рабочих дня<br>
            • Международная доставка: 3-10 рабочих дней<br>
            • Официальная гарантия Nico Market: 12 месяцев.
        `;
    } else if (p.category === 'software') {
        return `
            <strong>Лицензионный софт Nico Market</strong><br><br>
            Цифровой продукт с мгновенной доставкой. Вы покупаете 100% лицензионный ключ активации.<br><br>
            <strong>Особенности лицензии:</strong><br>
            • ${p.desc}<br>
            • Официальный дистрибутив и пожизненные обновления<br>
            • Доставка на указанный Email в течение 5-15 минут после оплаты<br><br>
            <strong>Что входит в комплект:</strong><br>
            • Уникальный ключ активации (ESD)<br>
            • Пошаговая инструкция по установке и настройке<br>
            • Бесплатная техническая поддержка 24/7 по вопросам активации.
        `;
    } else if (p.category === 'services') {
        return `
            <strong>Профессиональная IT-услуга Nico Market</strong><br><br>
            Высококлассное решение вашей задачи под ключ от квалифицированных специалистов нашей команды.<br><br>
            <strong>Как мы работаем:</strong><br>
            • **Спецификация:** ${p.desc}<br>
            • Обязательное составление ТЗ и подписание договора (NDA при необходимости)<br>
            • Поэтапная демонстрация промежуточных результатов<br><br>
            <strong>Наши гарантии:</strong><br>
            • Соблюдение дедлайнов и четкая отчетность<br>
            • Бесплатный период технической поддержки и исправления ошибок после сдачи работ.
        `;
    }
    return p.desc;
}

// Открытие модального окна товара
window.openProductModal = function(productId) {
    const product = PRODUCTS.find(p => p.id === productId);
    if (!product) return;

    activeModalProductId = productId;
    
    // Заполняем данные
    modalEmoji.textContent = product.emoji;
    modalTitle.textContent = product.title;
    modalPrice.textContent = `$${product.price}`;
    modalDesc.innerHTML = getProductLongDescription(product);
    
    // Устанавливаем категорию
    let categoryName = "Устройства";
    if (product.category === 'software') categoryName = "Софт";
    if (product.category === 'services') categoryName = "Услуги";
    modalBadge.textContent = categoryName;

    // Обновляем состояние кнопок корзины в модале
    updateModalUIIfOpen(productId);

    // Легкая вибрация при открытии
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('medium');
    }

    // Показываем оверлей
    productModal.classList.add('active');
};

// Закрытие модального окна
window.closeProductModal = function() {
    productModal.classList.remove('active');
    activeModalProductId = null;
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
};

// Закрытие по крестику
modalCloseBtn.addEventListener('click', closeProductModal);

// Закрытие по клику на оверлей вне карточки
productModal.addEventListener('click', (e) => {
    if (e.target === productModal) {
        closeProductModal();
    }
});

// Обновление кнопок управления количеством в модале
window.updateModalUIIfOpen = function(productId) {
    if (activeModalProductId !== productId) return;

    const countInCart = cart[productId] ? cart[productId].count : 0;
    
    modalQtyCount.textContent = countInCart;
    
    if (countInCart > 0) {
        modalBtnAction.textContent = "В корзине";
        modalBtnAction.classList.add('in-cart-btn'); // Дополнительный стиль при желании
    } else {
        modalBtnAction.textContent = "Добавить в корзину";
        modalBtnAction.classList.remove('in-cart-btn');
    }
};

// Изменение количества товара внутри модала
window.adjustModalQty = function(change) {
    if (!activeModalProductId) return;
    
    const countInCart = cart[activeModalProductId] ? cart[activeModalProductId].count : 0;
    const newCount = countInCart + change;

    if (newCount <= 0) {
        // Удаляем из корзины
        delete cart[activeModalProductId];
    } else {
        // Обновляем количество
        if (cart[activeModalProductId]) {
            cart[activeModalProductId].count = newCount;
        } else {
            const product = PRODUCTS.find(p => p.id === activeModalProductId);
            cart[activeModalProductId] = {
                title: product.title,
                price: product.price,
                count: newCount
            };
        }
    }

    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }

    updateCartUI();
    renderProducts(document.querySelector('.tab-btn.active').dataset.category, searchInput.value);
    updateModalUIIfOpen(activeModalProductId);
};

// Главная кнопка действия в модале
window.handleModalAction = function() {
    if (!activeModalProductId) return;
    
    const countInCart = cart[activeModalProductId] ? cart[activeModalProductId].count : 0;
    
    if (countInCart === 0) {
        // Если товара нет в корзине — добавляем его
        adjustModalQty(1);
    } else {
        // Если уже есть в корзине — просто закрываем модал, чтобы клиент мог пойти оформлять заказ
        closeProductModal();
    }
};

// --- КОРЗИНА И УПРАВЛЕНИЕ ЗАКАЗОМ ---
const cartModal = document.getElementById('cart-modal');
const cartModalCloseBtn = document.getElementById('cart-modal-close-btn');
const cartItemsContainer = document.getElementById('cart-items-container');
const cartModalTotalPrice = document.getElementById('cart-modal-total-price');

let isCartModalOpen = false;

// Открытие модального окна корзины
window.openCartModal = function() {
    isCartModalOpen = true;
    renderCartModalItems();
    
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('medium');
    }
    
    cartModal.classList.add('active');
};

// Закрытие модального окна корзины
window.closeCartModal = function() {
    cartModal.classList.remove('active');
    isCartModalOpen = false;
    
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
};

// Закрытие по крестику
if (cartModalCloseBtn) {
    cartModalCloseBtn.addEventListener('click', closeCartModal);
}

// Закрытие по клику вне контента
if (cartModal) {
    cartModal.addEventListener('click', (e) => {
        if (e.target === cartModal) {
            closeCartModal();
        }
    });
}

// Отрисовка списка товаров в модале корзины
window.renderCartModalItems = function() {
    cartItemsContainer.innerHTML = '';
    let totalPrice = 0;
    let hasItems = false;

    for (let id in cart) {
        hasItems = true;
        const item = cart[id];
        const product = PRODUCTS.find(p => p.id === parseInt(id));
        const itemTotal = item.price * item.count;
        totalPrice += itemTotal;

        const row = document.createElement('div');
        row.className = 'cart-item-row';
        row.innerHTML = `
            <div class="cart-item-info" onclick="openProductModal(${id})">
                <span class="cart-item-emoji">${product ? product.emoji : '📦'}</span>
                <div class="cart-item-details">
                    <span class="cart-item-title">${escapeHtml(item.title)}</span>
                    <span class="cart-item-price">$${item.price} × ${item.count}</span>
                </div>
            </div>
            <div class="cart-item-actions">
                <div class="cart-item-qty-controls" style="display: flex; align-items: center; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 2px;">
                    <button class="cart-item-qty-btn" onclick="adjustCartItemQty(${id}, -1)" style="width:24px; height:24px; border-radius:50%; border:none; background:transparent; color:white; font-size:0.9rem; cursor:pointer;">-</button>
                    <span class="cart-item-qty-val" style="font-size:0.85rem; font-weight:700; min-width:18px; text-align:center;">${item.count}</span>
                    <button class="cart-item-qty-btn" onclick="adjustCartItemQty(${id}, 1)" style="width:24px; height:24px; border-radius:50%; border:none; background:transparent; color:white; font-size:0.9rem; cursor:pointer;">+</button>
                </div>
                <button class="cart-item-delete" onclick="removeCartItem(${id})" style="background:transparent; border:none; cursor:pointer; font-size:1.1rem; padding: 2px 4px; display:flex; align-items:center;">🗑️</button>
            </div>
        `;
        cartItemsContainer.appendChild(row);
    }

    cartModalTotalPrice.textContent = `$${totalPrice}`;

    const checkoutBtnInModal = document.getElementById('cart-modal-btn-checkout');
    if (checkoutBtnInModal) {
        if (!hasItems) {
            cartItemsContainer.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    <div style="font-size: 3rem; margin-bottom: 12px;">🛒</div>
                    <h3>Ваша корзина пуста</h3>
                    <p style="font-size: 0.85rem; margin-top: 5px;">Добавьте товары из каталога выше</p>
                </div>
            `;
            checkoutBtnInModal.style.opacity = '0.5';
            checkoutBtnInModal.disabled = true;
        } else {
            checkoutBtnInModal.style.opacity = '1';
            checkoutBtnInModal.disabled = false;
        }
    }
};

// Изменение количества прямо в корзине
window.adjustCartItemQty = function(productId, change) {
    if (!cart[productId]) return;
    
    const newCount = cart[productId].count + change;
    
    if (newCount <= 0) {
        delete cart[productId];
    } else {
        cart[productId].count = newCount;
    }

    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }

    updateCartUI();
    renderProducts(document.querySelector('.tab-btn.active').dataset.category, searchInput.value);
    
    // Синхронизация детального модала, если он открыт
    if (activeModalProductId === productId) {
        updateModalUIIfOpen(productId);
    }
};

// Удаление товара из корзины
window.removeCartItem = function(productId) {
    if (cart[productId]) {
        delete cart[productId];
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('medium');
        }

        updateCartUI();
        renderProducts(document.querySelector('.tab-btn.active').dataset.category, searchInput.value);
        
        // Синхронизация детального модала, если он открыт
        if (activeModalProductId === productId) {
            updateModalUIIfOpen(productId);
        }
    }
};

// Действие по кнопке «Оформить заказ» в модале корзины
window.checkoutOrder = function() {
    const orderData = {
        items: cart,
        total: Object.values(cart).reduce((sum, item) => sum + (item.price * item.count), 0),
        timestamp: Date.now()
    };

    // Отправляем JSON-строку заказа обратно в бот
    tg.sendData(JSON.stringify(orderData));
    
    // Закрываем Mini App
    tg.close();
};

// Клик по плавающей корзине или кнопке заказа открывает модальное окно для проверки
cartBar.addEventListener('click', () => {
    openCartModal();
});
checkoutBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // предотвращаем всплытие клика к плавающему бару
    openCartModal();
});

// Первоначальная загрузка каталога и отрисовка
loadCatalog();
