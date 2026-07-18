# 🧠 Atlas Digital Studio

> **Локальная AI-студия для создания цифровых продуктов: сайты, брендинг, AI-фото, игры, приложения.**
> 
> Текущий фокус: **WEB (сайты до идеала)**

---

## ⚡ Быстрый старт

```bash
# 1. Убедись, что Ollama запущена
ollama list

# 2. Запуск полного цикла
python main.py "Сделай лендинг для кофейни..."

# 3. С конкретным скиллом
python main.py "Кофейня премиум" motion_premium
```

---

## 🏗️ Архитектура

```
Atlas/
├── Config/
│   └── llm_client.py          # Ollama клиент (гибрид 3B/7B)
├── Agents/
│   ├── executive.py           # Планировщик (7B)
│   ├── brief.py               # Генератор ТЗ + image tasks
│   ├── developer.py           # Разработчик (3B) + Skills + AOS
│   ├── image_generator.py     # Unsplash / FLUX / Pollinations
│   ├── auto_skill_hunter.py   # Авто-поиск skills с GitHub
│   ├── product_router.py      # Определяет тип продукта
│   ├── branding_agent.py      # Brand kit (резерв)
│   └── media_agent.py         # AI-фотосессии (резерв)
├── Tools/
│   ├── skills_manager.py      # Git-clone скиллов
│   └── self_upgrade.py        # Анализ кода + бэкапы
├── Skills/
│   ├── web/                   # Шаблоны сайтов
│   │   ├── modern_landing/
│   │   ├── agency/
│   │   ├── product_showcase/
│   │   └── motion_premium/    # GSAP + Lenis + glassmorphism
│   ├── games/                 # (резерв)
│   ├── apps/                  # (резерв)
│   ├── branding/
│   │   └── logo_pack/
│   └── media/                 # (резерв)
├── Projects/                  # Готовые продукты
├── Memory/
│   ├── backups/
│   ├── auto_skill_log.json
│   └── Ideas/
│       └── roadmap.md
└── main.py                    # Универсальный оркестратор
```

---

## 📋 Roadmap — «Сайты до идеала»

| # | Шаг | Статус |
|---|-----|--------|
| 1 | Тест motion_premium + фото | ⏳ |
| 2 | SEO-модуль (meta, OG, schema.org) | ⬜ |
| 3 | Форма заявки → Telegram | ⬜ |
| 4 | Auto-Deploy (GitHub Pages) | ⬜ |
| 5 | QA Agent (Playwright скриншоты) | ⬜ |
| 6 | Портфолио-демо (5 сайтов) | ⬜ |

**Резерв (после сайтов):** Game Dev, App Dev, Full Stack, Telegram Bot, Browser Agent, RAG, MCP.

---

## 🔑 API Ключи (получить)

| Сервис | URL | Для чего |
|--------|-----|----------|
| Unsplash | [unsplash.com/developers](https://unsplash.com/developers) | Реальные stock-фото |
| Hugging Face | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | FLUX.1 AI-генерация |
| GitHub | [github.com/settings/tokens](https://github.com/settings/tokens) | AutoSkill Hunter |

Вставь ключи в `Agents/image_generator.py` (переменные `UNSPLASH_ACCESS_KEY` и `HUGGINGFACE_TOKEN`) и в `Agents/auto_skill_hunter.py` (`GITHUB_TOKEN`).

---

## 🖥️ Железо

- **GPU:** GTX 1650 Ti 4GB
- **LLM:** Ollama (qwen2.5-coder:3b / :7b)
- **OS:** Windows (PowerShell)

---

## 📁 Контекст для Kimi

Этот репозиторий используется для работы с AI-ассистентом Kimi. Чтобы продолжить разработку в новой сессии:
1. Открой чат с Kimi
2. Дай ссылку: `https://github.com/ТВОЙ_НИК/Atlas`
3. Напиши: «Продолжаем Atlas, текущий фокус — [шаг из roadmap]»

Kimi прочитает `README.md`, `ROADMAP.md` и любые файлы кода напрямую с GitHub.
