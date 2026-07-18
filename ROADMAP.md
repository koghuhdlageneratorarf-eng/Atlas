# Atlas Roadmap

## Активно — WEB (сайты до идеала)

### Шаг 1: Тест motion_premium + фото ⏳
- Проверить подстановку сгенерированных изображений в шаблон
- Убедиться, что GSAP/Lenis анимации работают в браузере
- Проверить адаптивность на мобильных

### Шаг 2: SEO-модуль ⬜
- Автоматическое добавление `<meta name="description">`, `<meta name="keywords">`
- Open Graph теги (`og:title`, `og:image`, `og:description`)
- Schema.org JSON-LD (LocalBusiness, Product)
- Генерация `robots.txt` и `sitemap.xml`

### Шаг 3: Форма заявки → Telegram ⬜
- HTML-форма на сайте (имя, телефон, сообщение)
- Отправка в Telegram бот через Bot API
- Без backend — чистый JS + fetch к Telegram

### Шаг 4: Auto-Deploy (GitHub Pages) ⬜
- Скрипт `deploy.py`: создаёт/обновляет репозиторий, пушит `index.html`
- Клиент получает ссылку `https://username.github.io/project-name`
- Автоматическая генерация `CNAME` для кастомного домена

### Шаг 5: QA Agent (Playwright) ⬜
- Автоматический скриншот готового сайта
- Проверка консоли на ошибки JS
- Проверка всех ссылок (404)
- Сравнение с эталоном (pixel-perfect для ключевых страниц)

### Шаг 6: Портфолио-демо ⬜
- 5 готовых сайтов для разных ниш:
  1. Кофейня (product_showcase)
  2. Барбершоп (motion_premium)
  3. Фотограф (agency)
  4. Клиника (modern_landing)
  5. Стартап (motion_premium)

## Резерв (после завершения WEB)

### Game Developer Agent
- Three.js стартер (3D сцены)
- Phaser 2D платформер
- Интеграция с web-шаблонами

### App Developer Agent
- Python + Tkinter GUI
- Автоматизация скриптов
- Telegram/Discord боты

### Full Stack Agent
- FastAPI backend
- React frontend
- SQLite/PostgreSQL

### Инфраструктура
- Telegram-бот для заказов
- Browser Agent (парсинг конкурентов)
- RAG-память (ChromaDB)
- MCP (Model Context Protocol)
- Облачные API (Gemini, Groq) для Executive/Brief
