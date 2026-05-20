// Инициализация Telegram WebApp SDK
const tg = window.Telegram.WebApp;

// Расширяем приложение на весь экран телефона
tg.expand();

// Сообщаем Telegram, что WebApp загружен
tg.ready();

// Настройка цветов под тему Telegram пользователя
document.documentElement.style.setProperty('--bg-color', tg.backgroundColor || '#0f0c1b');
document.documentElement.style.setProperty('--text-color', tg.themeParams.text_color || '#f3f4f6');
document.documentElement.style.setProperty('--text-muted', tg.themeParams.hint_color || '#9ca3af');

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

// Реальный ассортимент из нашей базы знаний (03_catalog.txt)
const PRODUCTS = [
    // --- КАТЕГОРИЯ A: ФИЗИЧЕСКИЕ ТОВАРЫ (hardware) ---
    // A1. Смартфоны и планшеты
    { id: 1, title: "iPhone 16 Pro Max 256GB", desc: "Экран 6.9\" Super Retina XDR, Камера 48MP, Гарантия 12 мес.", price: 1199, emoji: "📱", category: "hardware" },
    { id: 2, title: "Samsung Galaxy S25 Ultra 512GB", desc: "Dynamic AMOLED 2X, Камера 200MP, S Pen, Гарантия 12 мес.", price: 1299, emoji: "🤖", category: "hardware" },
    { id: 3, title: "Google Pixel 9 Pro 128GB", desc: "Экран 6.3\" LTPO, Чистый Android, AI Gemini, Гарантия 12 мес.", price: 999, emoji: "👾", category: "hardware" },
    { id: 4, title: "iPad Pro M4 13\" 256GB", desc: "Тончайший корпус, Tandem OLED, Чип M4, Гарантия 12 мес.", price: 1299, emoji: "🍏", category: "hardware" },
    { id: 5, title: "Samsung Galaxy Tab S10 Ultra", desc: "Экран 14.6\", Защита IP68, Тонкий корпус, Гарантия 12 мес.", price: 1199, emoji: "📟", category: "hardware" },
    { id: 6, title: "OnePlus 13 256GB", desc: "Чип Snapdragon 8 Elite, Камера Hasselblad, Гарантия 12 мес.", price: 799, emoji: "⚡", category: "hardware" },
    { id: 7, title: "Xiaomi 15 Pro 512GB", desc: "Оптика Leica, Батарея 5400мАч, Быстрая зарядка, Гарантия 12 мес.", price: 699, emoji: "🐉", category: "hardware" },

    // A2. Ноутбуки и компьютеры
    { id: 8, title: "MacBook Pro 16\" M4 Pro", desc: "36GB RAM, 512GB SSD, Экран Liquid Retina XDR, Гарантия 12 мес.", price: 2499, emoji: "💻", category: "hardware" },
    { id: 9, title: "MacBook Air 15\" M4", desc: "16GB RAM, 256GB SSD, Бесшумный, Легкий, Гарантия 12 мес.", price: 1299, emoji: "☁️", category: "hardware" },
    { id: 10, title: "Dell XPS 16", desc: "Intel Ultra 9, 32GB RAM, 1TB SSD, OLED Сенсорный, Гарантия 12 мес.", price: 1899, emoji: "💎", category: "hardware" },
    { id: 11, title: "Lenovo ThinkPad X1 Carbon Gen 12", desc: "Бизнес-классика, Корпус из углеволокна, Гарантия 12 мес.", price: 1749, emoji: "💼", category: "hardware" },
    { id: 12, title: "ASUS ROG Zephyrus G16", desc: "Геймерский монстр, Чип RTX 5080, OLED 240Hz, Гарантия 12 мес.", price: 2299, emoji: "🎮", category: "hardware" },
    { id: 13, title: "Framework Laptop 16", desc: "Модульный и легко ремонтируемый ноутбук, Гарантия 12 мес.", price: 1399, emoji: "🔧", category: "hardware" },
    { id: 14, title: "Mac Mini M4 Pro", desc: "24GB RAM, 512GB SSD, Суперкомпактный ПК, Гарантия 12 мес.", price: 1399, emoji: "📦", category: "hardware" },

    // A3. Аудиотехника
    { id: 15, title: "Apple AirPods Pro 3", desc: "Адаптивное шумоподавление, Улучшенный звук, Гарантия 12 мес.", price: 249, emoji: "🎵", category: "hardware" },
    { id: 16, title: "Sony WH-1000XM6", desc: "Полноразмерные наушники, Абсолютная тишина, Гарантия 12 мес.", price: 349, emoji: "🎧", category: "hardware" },
    { id: 17, title: "Bose QuietComfort Ultra", desc: "Премиальные наушники, Максимальный комфорт, Гарантия 12 мес.", price: 429, emoji: "🎹", category: "hardware" },
    { id: 18, title: "Marshall Emberton III", desc: "Портативная колонка, Легендарный рок-дизайн, Гарантия 12 мес.", price: 169, emoji: "📻", category: "hardware" },
    { id: 19, title: "JBL Charge 6", desc: "Мощный бас, Встроенный павербанк, Влагозащита, Гарантия 12 мес.", price: 179, emoji: "🔊", category: "hardware" },
    { id: 20, title: "Sonos Era 300", desc: "Умная домашняя колонка, Пространственный звук, Гарантия 12 мес.", price: 449, emoji: "🎼", category: "hardware" },

    // A4. Умный дом и IoT
    { id: 21, title: "Apple HomePod mini", desc: "Компактная смарт-колонка, Интеграция с Siri, Гарантия 12 мес.", price: 99, emoji: "🍎", category: "hardware" },
    { id: 22, title: "Google Nest Hub Max", desc: "Экран 10\", Камера наблюдения, Google Ассистент, Гарантия 12 мес.", price: 229, emoji: "📺", category: "hardware" },
    { id: 23, title: "Ring Video Doorbell Pro 2", desc: "Умный видеозвонок, Запись 1536p HD, Гарантия 12 мес.", price: 249, emoji: "🔔", category: "hardware" },
    { id: 24, title: "Philips Hue Starter Kit", desc: "3 умные лампы + блок управления мостом, Гарантия 24 мес.", price: 129, emoji: "💡", category: "hardware" },
    { id: 25, title: "iRobot Roomba j9+", desc: "Робот-пылесос с автовыгрузкой мусора, Гарантия 12 мес.", price: 799, emoji: "🧹", category: "hardware" },
    { id: 26, title: "Aqara Smart Lock U200", desc: "Умный дверной замок, Сканер отпечатков, Гарантия 12 мес.", price: 189, emoji: "🔒", category: "hardware" },
    { id: 27, title: "Ecobee Smart Thermostat Premium", desc: "Умный термостат, Встроенная Alexa, Гарантия 24 мес.", price: 249, emoji: "🌡️", category: "hardware" },

    // A5. Носимые устройства
    { id: 28, title: "Apple Watch Ultra 3", desc: "Титановый корпус, Время работы до 72 часов, Гарантия 12 мес.", price: 799, emoji: "⌚", category: "hardware" },
    { id: 29, title: "Samsung Galaxy Watch 7", desc: "Мониторинг здоровья, Сенсорный AMOLED, Гарантия 12 мес.", price: 299, emoji: "🏃", category: "hardware" },
    { id: 30, title: "Garmin Fenix 8 Solar", desc: "Премиум GPS-часы, Солнечная батарея, Гарантия 24 мес.", price: 899, emoji: "🏔️", category: "hardware" },
    { id: 31, title: "Oura Ring Gen 4", desc: "Стильное умное кольцо, Анализ фаз сна, Гарантия 12 мес.", price: 349, emoji: "💍", category: "hardware" },
    { id: 32, title: "Meta Ray-Ban Smart Glasses", desc: "Умные очки с камерой, Динамиками и ИИ, Гарантия 12 мес.", price: 299, emoji: "🕶️", category: "hardware" },

    // A6. Аксессуары
    { id: 33, title: "Logitech MX Master 3S", desc: "Эргономичная мышь, Бесшумные клики, Гарантия 12 мес.", price: 99, emoji: "🖱️", category: "hardware" },
    { id: 34, title: "Keychron Q1 Pro", desc: "Металлическая механическая клавиатура, Гарантия 12 мес.", price: 199, emoji: "⌨️", category: "hardware" },
    { id: 35, title: "Samsung T9 Portable SSD 2TB", desc: "Портативный сверхбыстрый внешний диск, Гарантия 36 мес.", price: 179, emoji: "💾", category: "hardware" },
    { id: 36, title: "Anker 737 Power Bank 24k", desc: "Внешний аккумулятор 140W, Дисплей, Гарантия 18 мес.", price: 109, emoji: "🔋", category: "hardware" },
    { id: 37, title: "Belkin 3-in-1 MagSafe Charger", desc: "Беспроводная зарядка Apple Watch/iPhone, Гарантия 12 мес.", price: 149, emoji: "🔌", category: "hardware" },
    { id: 38, title: "Elgato Stream Deck MK.2", desc: "Контроллер для стримеров, 15 ЖК-клавиш, Гарантия 12 мес.", price: 149, emoji: "📽️", category: "hardware" },
    { id: 39, title: "CalDigit TS4 Thunderbolt Dock", desc: "18 портов, Питание до 98W, Гарантия 24 мес.", price: 379, emoji: "⛽", category: "hardware" },

    // A7. Дроны и камеры
    { id: 40, title: "DJI Air 3S", desc: "Дрон с двойной камерой, Сенсор 1\", Гарантия 12 мес.", price: 1099, emoji: "🛸", category: "hardware" },
    { id: 41, title: "DJI Mini 4 Pro", desc: "Легкий дрон до 249г, Съемка 4K HDR, Гарантия 12 мес.", price: 759, emoji: "🚁", category: "hardware" },
    { id: 42, title: "GoPro HERO 13 Black", desc: "Экшн-камера, Улучшенный стабилизатор, Гарантия 12 мес.", price: 399, emoji: "📷", category: "hardware" },
    { id: 43, title: "Sony ZV-E10 II", desc: "Камера со сменной оптикой для влогов, Гарантия 12 мес.", price: 899, emoji: "🎥", category: "hardware" },
    { id: 44, title: "Insta360 X4", desc: "Экшн-камера 360 градусов, Запись 8K, Гарантия 12 мес.", price: 499, emoji: "👁️", category: "hardware" },

    // --- КАТЕГОРИЯ B: ЦИФРОВЫЕ ПРОДУКТЫ (software) ---
    // B1. Лицензии ПО
    { id: 45, title: "Microsoft 365 Personal (1 год)", desc: "Оригинальный офисный пакет на 1 год для 1 ПК/Mac", price: 69, emoji: "🔑", category: "software" },
    { id: 46, title: "Microsoft 365 Family (1 год)", desc: "Подписка для семьи, до 6 пользователей на 1 год", price: 99, emoji: "👥", category: "software" },
    { id: 47, title: "Adobe Creative Cloud (1 год)", desc: "Лицензия на все приложения Creative Cloud на год", price: 599, emoji: "🎨", category: "software" },
    { id: 48, title: "JetBrains All Products (1 год)", desc: "Пакет лучших IDE для разработчиков на год", price: 249, emoji: "☕", category: "software" },
    { id: 49, title: "Notion Plus (1 год)", desc: "Годовая подписка на Notion Plus для продуктивности", price: 96, emoji: "📓", category: "software" },
    { id: 50, title: "1Password Personal (1 год)", desc: "Лицензия на менеджер паролей №1 в мире на год", price: 36, emoji: "🔐", category: "software" },
    { id: 51, title: "NordVPN Complete (2 года)", desc: "Премиум VPN-сервис, Защита от угроз, 2 года подписки", price: 99, emoji: "🛡️", category: "software" },

    // B2. Облака и хостинг
    { id: 52, title: "Nico Cloud Starter (50GB)", desc: "Персональное облачное хранилище, Бэкапы, Месячная подписка", price: 5, emoji: "☁️", category: "software" },
    { id: 53, title: "Nico Cloud Pro (500GB)", desc: "Облако для профи, Приоритетная поддержка, Месячная подписка", price: 13, emoji: "⛈️", category: "software" },
    { id: 54, title: "Nico Cloud Business (2TB)", desc: "Командный доступ, Личный менеджер, Месячная подписка", price: 30, emoji: "🏢", category: "software" },
    { id: 55, title: "VPS Nico Lite", desc: "Виртуальный сервер: 2 vCPU, 4GB RAM, 80GB SSD, В месяц", price: 10, emoji: "🔌", category: "software" },
    { id: 56, title: "VPS Nico Power", desc: "Мощный сервер: 4 vCPU, 16GB RAM, 200GB NVMe, В месяц", price: 30, emoji: "🏎️", category: "software" },
    { id: 57, title: "Managed WordPress Hosting", desc: "Готовый быстрый хостинг под WordPress, В месяц", price: 8, emoji: "🌸", category: "software" },

    // B3. Обучение
    { id: 58, title: "Курс 'Python с нуля до Junior'", desc: "60 часов видеолекций, Практические ДЗ, Сертификат", price: 49, emoji: "🐍", category: "software" },
    { id: 59, title: "Курс 'Fullstack Web Dev'", desc: "120 часов обучения (HTML/CSS/React/Node.js), Сертификат", price: 99, emoji: "🕸️", category: "software" },
    { id: 60, title: "Курс 'AI & Machine Learning'", desc: "Практическое обучение ML, Создание нейросетей, 80 часов", price: 79, emoji: "🧠", category: "software" },
    { id: 61, title: "Курс 'Кибербезопасность'", desc: "От основ ИБ до тестирования на проникновение, 90 часов", price: 89, emoji: "🚔", category: "software" },
    { id: 62, title: "Курс 'UI/UX Дизайн Figma'", desc: "Создание интерфейсов, Figma Masterclass, 40 часов", price: 39, emoji: "📐", category: "software" },
    { id: 63, title: "Academy All Access Pass", desc: "Годовой безлимитный доступ ко всем курсам Nico Academy", price: 199, emoji: "🎫", category: "software" },

    // B4. Развлечения
    { id: 64, title: "Xbox Game Pass Ultimate", desc: "Подписка на 1 месяц, Доступ к сотням игр на ПК/Консоли", price: 15, emoji: "💚", category: "software" },
    { id: 65, title: "PlayStation Plus Premium", desc: "Подписка на 3 месяца, Каталог классики и онлайн", price: 50, emoji: "💙", category: "software" },
    { id: 66, title: "Nintendo eShop Card $50", desc: "Карта пополнения баланса Nintendo eShop на $50", price: 50, emoji: "❤️", category: "software" },

    // --- КАТЕГОРИЯ C: IT-УСЛУГИ (services) ---
    // C1. Разработка
    { id: 67, title: "Создание Telegram-бота", desc: "Разработка ботов любой сложности (включая AI и RAG)", price: 300, emoji: "🤖", category: "services" },
    { id: 68, title: "Разработка лендинга", desc: "Эксклюзивный дизайн + верстка + запуск под ключ", price: 500, emoji: "🎨", category: "services" },
    { id: 69, title: "Разработка веб-приложения", desc: "Сложное приложение под ваши задачи на React/Next.js", price: 2000, emoji: "🌐", category: "services" },
    { id: 70, title: "Разработка мобильного приложения", desc: "Кроссплатформенное приложение на React Native", price: 5000, emoji: "📲", category: "services" },
    { id: 71, title: "Интеграция AI в бизнес", desc: "Внедрение нейросетевых ассистентов в ваши процессы", price: 1500, emoji: "🦾", category: "services" },

    // C2. Техподдержка
    { id: 72, title: "Разовая консультация IT (1ч)", desc: "Решение технических проблем с инженером в живом звонке", price: 50, emoji: "🛠️", category: "services" },
    { id: 73, title: "Tech Support Monthly", desc: "Пакет администрирования (до 10 часов поддержки в месяц)", price: 299, emoji: "🧰", category: "services" },
    { id: 74, title: "Аудит IT-инфраструктуры", desc: "Комплексный анализ ваших серверов, кода и архитектуры", price: 500, emoji: "📋", category: "services" },
    { id: 75, title: "Настройка облака и серверов", desc: "Развертывание Linux-серверов, Docker, облаков AWS/GCP", price: 200, emoji: "🏗️", category: "services" },
    { id: 76, title: "Миграция данных и систем", desc: "Безопасный перенос баз данных и сайтов на новые хостинги", price: 300, emoji: "🚚", category: "services" },

    // C3. Безопасность
    { id: 77, title: "Аудит веб-безопасности", desc: "Проверка на уязвимости OWASP Top 10, Поиск брешей", price: 800, emoji: "🦺", category: "services" },
    { id: 78, title: "Пентест под ключ", desc: "Имитация хакерской атаки на вашу инфраструктуру", price: 2000, emoji: "🏴‍☠️", category: "services" },
    { id: 79, title: "Настройка корп. VPN", desc: "Развертывание защищенного WireGuard/OpenVPN сервера", price: 300, emoji: "🧗", category: "services" },
    { id: 80, title: "Мониторинг угроз (Nico Shield)", desc: "Подписка на систему безопасности и мониторинга, В месяц", price: 50, emoji: "💎", category: "services" },

    // C4. Дизайн
    { id: 81, title: "Дизайн логотипа", desc: "3 концепта, Индивидуальный дизайн, Исходники", price: 150, emoji: "✒️", category: "services" },
    { id: 82, title: "Разработка фирменного стиля", desc: "Логотип + брендбук + дизайн мерча/визиток под ключ", price: 500, emoji: "🎴", category: "services" },
    { id: 83, title: "UI/UX дизайн приложения", desc: "Интерактивный макет в Figma до 15 экранов под ключ", price: 1200, emoji: "📐", category: "services" },
    { id: 84, title: "Дизайн презентации", desc: "Качественная бизнес-презентация до 20 слайдов", price: 200, emoji: "📊", category: "services" }
];

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
                <div class="product-title">${p.title}</div>
                <div class="product-desc">${p.desc}</div>
            </div>
            <div class="product-footer">
                <div class="product-price">$${p.price}</div>
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

// Действие по кнопке «Оформить заказ»
checkoutBtn.addEventListener('click', () => {
    const orderData = {
        items: cart,
        total: Object.values(cart).reduce((sum, item) => sum + (item.price * item.count), 0),
        timestamp: Date.now()
    };

    // Отправляем JSON-строку заказа обратно в бот
    tg.sendData(JSON.stringify(orderData));
    
    // Закрываем Mini App
    tg.close();
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
                    <span class="cart-item-title">${item.title}</span>
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

// Первоначальный запуск отрисовки
renderProducts("hardware");
