# ATLAS MASTER CHECKPOINT v6.0
**Дата:** 2026-07-20  
**Сессий объединено:** 7 (Чекпоинт 1-5 + ChatGPT-Настройка AI-станции + Текущая сессия)  
**GitHub:** https://github.com/koghuhdlageneratorarf-eng/Atlas  
**Статус:** OpenRouter подключён, Model Router работает, агенты обновлены, начат переход к Atlas Code Agent

---

## 1. ЧТО ТАКОЕ ATLAS

**Atlas** — локальная мультифункциональная digital-студия на Python.  
Не генератор сайтов, а **фабрика цифровых продуктов**: сайты, брендинг, AI-фото, игры, приложения, боты, SMM-контент.

**Главная цель:** автономный бизнес — Atlas сам находит клиентов, создаёт продукт, сдаёт, принимает оплату.  
**Долгосрочная цель:** TikTok/YouTube каналы (анализ трендов, генерация видео, монетизация).

**Текущий фокус:** создание **Atlas Code Agent** — автономной системы разработки, которая работает с файлами проекта без потери контекста, как Claude Code. После доведения ядра до автономности — система сама добавляет модули, навыки и фичи.

### Философия
1. **Не изобретай велосипед** — использовать готовые open-source решения
2. **Skills-first** — Developer заполняет шаблоны, не пишет с нуля
3. **Гибрид моделей** — облако для мозгов, локалка для рутины
4. **Автоматизировать всё, что повторяется**
5. **Любое улучшение должно быть обратимым**
6. **Никакой магии** — любое действие объяснимо
7. **Автономность** — система сама себя развивает через Tool Use + Self-Upgrade

---

## 2. ЖЕЛЕЗО И ОКРУЖЕНИЕ

| Параметр | Значение |
|---|---|
| GPU | NVIDIA GTX 1650 Ti 4GB VRAM |
| CUDA | Работает, но Ollama падает на больших моделях → используем CPU-режим |
| OS | Windows 10/11 |
| Python | 3.14.6 |
| Node.js | v24.18.0 |
| Git | 2.55.0 |
| uv | 0.11.26 |
| Ollama | 0.31.1 (CPU-режим через `$env:OLLAMA_NO_CUDA="1"`) |
| VS Code | + Continue (плагин) |
| Локальные модели | qwen2.5-coder:3b, qwen2.5-coder:7b, deepseek-coder:6.7b |

### Скорость моделей (измерено)
- **qwen2.5-coder:3b** → ~8 сек (быстро, для Developer)
- **qwen2.5-coder:7b** → ~15 сек (умнее, для Executive/Self-Upgrade)

---

## 3. АРХИТЕКТУРА

```
Atlas/
├── Agents/
│   ├── executive.py          # Планировщик (OpenRouter / Ollama 7B)
│   ├── brief.py              # Генератор ТЗ + image tasks [stock]/[ai]
│   ├── developer.py          # Заполнение шаблонов + AOS + подстановка фото
│   ├── image_generator.py    # Unsplash / FLUX / Pollinations
│   ├── auto_skill_hunter.py  # Авто-поиск шаблонов на GitHub
│   ├── product_router.py     # Определяет тип продукта (web/game/app/branding/media)
│   ├── branding_agent.py     # SVG-логотип, brand book HTML (резерв)
│   └── media_agent.py        # AI-фотосессии + HTML-альбом (резерв)
├── Brain/
│   ├── graphify_bridge.py    # Адаптер Graphify + каталог skills
│   └── memory_graph.py       # SQLite эпизодическая память
├── Config/
│   ├── llm_client.py         # Model Router (7 провайдеров + Ollama)
│   ├── models.yaml           # Приоритеты провайдеров по агентам
│   └── .env                  # API-ключи
├── Skills/
│   ├── agency/               # Bootstrap agency (skill.json + dist/)
│   ├── modern_landing/       # Tailwind landing
│   ├── product_showcase/     # Карточки товаров с hover
│   └── motion_premium/       # GSAP + Lenis + glassmorphism + bento + magnetic
├── Projects/                 # Готовые продукты
├── Memory/
│   ├── backups/              # Бэкапы (исключены из самих бэкапов)
│   ├── Ideas/roadmap.md      # Дорожная карта
│   └── brain_memory.db       # SQLite память (episodes, bugs, decisions)
├── Tools/
│   ├── skills_manager.py     # Git-clone скиллов
│   └── self_upgrade.py       # Анализ кода + бэкапы
├── atlas_core/               # 🆕 ЯДРО Atlas Code Agent (в разработке)
│   ├── session.py            # SQLite память сессии
│   ├── context.py            # Менеджер контекста проекта
│   ├── tools.py              # Инструменты (read/write/run/edit)
│   └── agent.py              # REPL + цикл Tool Use
├── graphify-out/             # Авто-создаётся Graphify
│   ├── graph.json
│   └── GRAPH_REPORT.md
├── main.py                   # Оркестратор (legacy pipeline)
└── README.md / ROADMAP.md
```

---

## 4. ЧТО УЖЕ РАБОТАЕТ (зелёное)

| Компонент | Статус | Суть |
|---|---|---|
| Гибрид моделей | ✅ | Executive/Self-Upgrade → OpenRouter, Developer → Ollama 3B |
| Skills-first | ✅ | Developer заполняет шаблоны, не пишет с нуля |
| Auto-AOS | ✅ | Любой сайт получает анимации скролла автоматически |
| Image Generator | ✅ | 3 режима: [stock]→Unsplash, [ai]→FLUX, fallback→Pollinations |
| Motion Premium skill | ✅ | GSAP + Lenis + glassmorphism + bento + magnetic buttons + spotlight |
| Brief Agent | ✅ | 2 режима: короткий (<300 симв) → генерирует ТЗ, длинный → использует как ТЗ |
| AutoSkill Hunter | ✅ | Ищет шаблоны на GitHub, анализирует LLM, адаптирует пути |
| GitHub-интеграция | ✅ | Репозиторий создан, код залит |
| Brain v2.0 (Graphify) | ✅ | Knowledge graph из кода, авто-контекст для LLM |
| Memory Graph (SQLite) | ✅ | Эпизодическая память: episodes, bugs, decisions |
| Model Router | ✅ | 7 провайдеров, авто-fallback, приоритеты по агентам |
| Product Router | ✅ | Определяет тип: web/game/app/branding/media |
| Branding Agent | ✅ (резерв) | SVG-логотип, палитра, шрифты, brand book HTML |
| Media Agent | ✅ (резерв) | AI-фотосессия + HTML-альбом |
| Self-Upgrade | ✅ | Анализ кода, бэкапы, предложения в JSON |
| OpenRouter интеграция | ✅ | Работает, Executive и Brief ходят в Gemini 2.5 Pro |
| UTF-8 кодировка | ✅ | Фикс sys.stdout.reconfigure(encoding='utf-8') |
| Агенты обновлены | ✅ | executive.py, brief.py, developer.py — используют agent= параметр |
| Правило "Не изобретай велосипед" | ✅ | В roadmap.md |

---

## 5. MODEL ROUTER (7 ПРОВАЙДЕРОВ)

| Провайдер | Модель | Лимит | Для чего | Статус |
|---|---|---|---|---|
| **OpenRouter** | Gemini 2.5 Pro | 20 req/min | Executive, Brief, Self-Upgrade | ✅ Работает |
| **Cerebras** | Llama 4 Scout | 1M токенов/день | Скоростные задачи | ⚠️ Нет ключа |
| **Groq** | Llama 3.3 70B | 500K токенов/день | Резерв | ⚠️ Нет ключа |
| **Cloudflare** | Llama 3.1 8B | edge | Резерв | ⚠️ Нет ключа |
| **HuggingFace** | Phi-3-mini | free tier | Резерв | ⚠️ Нет ключа |
| **Ollama** | qwen2.5-coder 3B/7B | безлимит | Developer, Fallback | ✅ Работает |
| Gemini (прямой) | 2.5 Pro | ~60 req/min | — | ❌ Блокирует Россию |

**Итого:** OpenRouter + Ollama работают. ~2M токенов/день потенциально + локальная Ollama.

### Приоритеты (models.yaml) — ТЕКУЩИЕ
```yaml
agents:
  executive: [openrouter, cerebras, groq, ollama]
  brief: [openrouter, cerebras, groq, ollama]
  developer: [ollama, openrouter, cloudflare]
  self_upgrade: [openrouter, cerebras, ollama]
  branding: [openrouter, cerebras, ollama]
  media: [ollama, openrouter, cloudflare]
```

---

## 6. BRAIN v2.0 (Graphify + Memory)

### Три слоя
1. **Perception Layer** — Brain/graphify_bridge.py индексирует проект через Graphify (knowledge graph из кода)
2. **Memory Core** — Brain/memory_graph.py (SQLite: episodes, bugs, decisions)
3. **Cognition Layer** — Config/llm_client.py с авто-подгрузкой контекста из графа

### Как работает
1. При вызове ask_llm() система автоматически:
   - Читает graph.json (структура проекта)
   - Читает все skill.json (каталог skills)
   - Читает недавнюю историю из SQLite
2. Формирует контекст: "=== КОНТЕКСТ ПРОЕКТА ATLAS ==="
3. Вставляет как system-сообщение перед задачей
4. LLM видит проект изнутри, не предлагает создать существующие папки

### Ключевые фиксы
- graphify.exe — полный путь в GRAPHIFY_EXE (не в PATH)
- community может быть int в graph.json → str(community_raw)
- BOM в skill.json → encoding="utf-8-sig" в _read_json_safe()
- Skills лежат прямо в Skills/ (не в Skills/web/)

---

## 7. ATLAS CODE AGENT (🆕 НОВОЕ НАПРАВЛЕНИЕ)

### Проблема текущей архитектуры
- Каждый агент — отдельный скрипт, нет единого контекста между шагами
- Graphify строит граф, но не даёт полный код файлов
- Brief → Developer — передача через файлы, потеря контекста
- Нет интерактивности — нельзя уточнить, поправить, продолжить диалог

### Цель
Создать автономную систему, как Claude Code:
- Работает с файлами проекта без ограничений контекста
- Интерактивный REPL: atlas> добавь модуль логирования
- LLM вызывает функции (Tool Use): read_file, write_file, run_command
- Сессионная память — не теряется между перезапусками
- Self-Upgrade loop — система сама анализирует и улучшает код

### Архитектура ядра (в разработке)
```
atlas_core/
├── session.py      # SQLite память сессии (история сообщений)
├── context.py      # Менеджер контекста (дерево файлов + smart truncation)
├── tools.py        # Инструменты: read/write/edit/run/list/search/git
└── agent.py        # REPL + цикл Tool Use
```

### Принципы Atlas Code Agent
| Принцип | Реализация |
|---|---|
| **Никакой потери контекста** | SQLite-сессия + полный проект в контексте при каждом запросе |
| **Никакой копипасты** | Tool Use — LLM сам читает/пишет файлы |
| **Саморазвитие** | Self-Upgrade анализирует код → генерирует задачи → выполняет |
| **Модульность** | Каждая фича — отдельный модуль, система сама решает что добавить |
| **Безопасность** | Git diff перед изменениями, бэкапы, подтверждение пользователя |

### Tool Use — как работает
LLM выдаёт JSON с вызовами функций:
```json
{
  "thought": "Нужно добавить модуль логирования...",
  "tools": [
    {"name": "read_file", "args": {"path": "main.py"}},
    {"name": "list_directory", "args": {"path": "."}}
  ]
}
```
Система выполняет инструменты → возвращает результаты → LLM думает дальше.

---

## 8. SKILLS

| Skill | Технологии | Назначение |
|---|---|---|
| **modern_landing** | Tailwind CSS | Профессиональный лендинг |
| **agency** | Bootstrap | Агентство, компания, портфолио |
| **product_showcase** | Tailwind | Карточки товаров с hover |
| **motion_premium** | GSAP + Lenis + Tailwind | Премиум: плавный скролл, glassmorphism, bento, magnetic buttons, spotlight |
| **logo_pack** (branding) | SVG + HTML | Brand kit: логотип, палитра, шрифты |

---

## 9. АГЕНТЫ (Legacy Pipeline)

| Агент | Модель | Задача |
|---|---|---|
| **Executive** | OpenRouter / Ollama 7B | Планирование, выбор агентов |
| **Brief** | OpenRouter / Ollama 7B | Генерация ТЗ + image tasks |
| **Developer** | Ollama 3B | Заполнение шаблонов + AOS + фото |
| **Image Generator** | — | Unsplash / FLUX / Pollinations |
| **AutoSkill Hunter** | OpenRouter 7B | Поиск шаблонов на GitHub |
| **Product Router** | OpenRouter 7B | Определение типа продукта |
| **Branding Agent** | OpenRouter 7B | SVG-логотип, brand book (резерв) |
| **Media Agent** | Ollama 3B | AI-фотосессии (резерв) |
| **Self-Upgrade** | OpenRouter 7B | Анализ кода, предложения |

---

## 10. ИСТОРИЯ СЕССИЙ (кратко)

### Сессия 1 (ChatGPT — Настройка AI-станции)
- Установка базы: Git, VS Code, Node.js, Python 3.14, uv, Ollama
- Фикс PowerShell execution policy
- Установка Ollama + qwen2.5-coder
- Фикс CUDA ошибок → CPU-режим через OLLAMA_NO_CUDA=1
- Подключение Continue в VS Code к Ollama
- Первый "вайбкодинг" — калькулятор на Python

### Сессия 2 (Чекпоинт 1)
- Создание структуры Atlas
- Self-Upgrade (фикс рекурсии в бэкапах)
- modern_landing skill
- Гибрид 3B/7B (измерение скорости)
- Executive на 7B, Developer на 3B
- Brief Agent (2 режима)
- Skills Manager (git clone)
- agency skill клонирован с GitHub
- Фикс BOM в skill.json
- Auto-AOS (AOS.js вставка)
- Правило "Не изобретай велосипед"

### Сессия 3 (Чекпоинт 2)
- Image Generator (Unsplash/FLUX/Pollinations)
- product_showcase skill
- motion_premium skill (GSAP, Lenis, glassmorphism, bento, magnetic)
- AutoSkill Hunter
- Product Router
- Branding Agent
- Media Agent
- Переосмысление: Atlas = Digital Studio, не только сайты

### Сессия 4 (Чекпоинт 3)
- GitHub интеграция (setup_github.py)
- Репозиторий создан: koghuhdlageneratorarf-eng/Atlas
- Model Router (7 провайдеров)
- Roadmap "Сайты до идеала"
- Автономный бизнес pipeline (5 этапов)

### Сессия 5 (Чекпоинт 4)
- Brain v2.0 (Graphify + Memory)
- graphify_bridge.py
- memory_graph.py (SQLite)
- Фиксы: пути, BOM, community=int
- Тест авто-контекста

### Сессия 6 (Чекпоинт 5)
- Завершение Brain v2.0
- Финальный Model Router
- Создание models.yaml и .env
- Диагностика провайдеров

### Сессия 7 (Текущая — переход к Code Agent)
- OpenRouter подключён и работает (diagnose ✅)
- Pipeline main.py работает: Executive → OpenRouter, Developer → Ollama 3B
- Фикс кодировки UTF-8 (sys.stdout.reconfigure)
- Обновление агентов: model= → agent= параметр
- Решение о переходе от legacy pipeline к Atlas Code Agent
- Концепция: система сама себя развивает, пользователь только даёт задачи

---

## 11. ДОРОЖНАЯ КАРТА

### Этап 0: Atlas Code Agent — ЯДРО (ТЕКУЩИЙ)
- [ ] Создать atlas_core/session.py — SQLite память сессии
- [ ] Создать atlas_core/context.py — менеджер контекста проекта
- [ ] Создать atlas_core/tools.py — инструменты (read/write/run/edit)
- [ ] Создать atlas_core/agent.py — REPL + цикл Tool Use
- [ ] Интеграция с OpenRouter (1M контекст Gemini 2.5 Pro)
- [ ] Тест: "добавь модуль логирования в Atlas" → агент сам читает, планирует, пишет
- [ ] Self-Upgrade loop — автозапуск анализа после каждой задачи

### Этап 1: Сайты до идеала (после ядра)
- [x] motion_premium + фото
- [ ] SEO-модуль (meta, Open Graph, schema.org)
- [ ] Форма → Telegram
- [ ] Auto-Deploy (GitHub Pages)
- [ ] QA Agent (Playwright + скриншоты)
- [ ] Портфолио-демо (5 сайтов)

### Этап 2: Авто-продажи (после 3-5 ручных)
- [ ] Browser Agent (парсинг Avito/Услуги)
- [ ] Lead Scoring
- [ ] Auto-Brief (персонализированное КП)
- [ ] Telegram Bot для лидов

### Этап 3: Авто-переписка
- [ ] CRM-интеграция
- [ ] FAQ Bot
- [ ] Revision Bot
- [ ] Payment Link (ЮKassa/Stripe)

### Этап 4: Автономный pipeline
- [ ] Auto-Deploy
- [ ] Auto-Invoice
- [ ] Auto-Delivery
- [ ] Analytics

### Этап 5: Full Autonomy
- [ ] Self-Improvement Loop
- [ ] Niche Expansion
- [ ] Pricing AI

### Параллельные направления (после web)
- [ ] Игры (Three.js, Phaser)
- [ ] Приложения (Python, Tauri)
- [ ] Брендинг (логотипы, brand book)
- [ ] AI-фото (фотосессии, аватары)
- [ ] SMM-контент (карусели, посты)
- [ ] Telegram/Discord боты
- [ ] TikTok/YouTube (анализ трендов, генерация видео)

---

## 12. ПРАВИЛА РАЗРАБОТКИ

1. **Не изобретай велосипед** — проверь open-source перед созданием
2. **Skills-first** — Developer заполняет шаблоны
3. **Гибрид моделей** — облако для мозгов, локалка для рутины
4. **Автоматизация повторов** — если сделал руками дважды → скрипт
5. **Бэкап перед изменениями** — Self-Upgrade делает backup
6. **Memory исключена из бэкапов** — иначе рекурсия
7. **utf-8-sig для JSON** — Windows добавляет BOM
8. **Чекпоинт при >15-20 сообщений** — сохранять контекст
9. **Автономность превыше всего** — система должна работать без копипасты
10. **Tool Use для файлов** — LLM сам читает/пишет, не пользователь

---

## 13. ЧТО СЛОМАНО / В ПРОЦЕССЕ

| Проблема | Статус | Фикс |
|---|---|---|
| API-ключи (Cerebras, Groq, Cloudflare, HF) | ⚠️ | Не критично, OpenRouter работает |
| Unsplash ключ | ⚠️ | Image Generator без stock-фото |
| Skill loading (product_showcase) | ⚠️ | Developer падает на загрузке skill, генерирует с нуля |
| Legacy pipeline не интерактивный | 🔴 | Переход на Atlas Code Agent |
| Нет atlas_core/ | 🔴 | Создаём в текущей сессии |
| Нет CLI-команды atlas | 🔴 | Создаём после ядра |
| models.yaml не читался | ✅ | Фикс в llm_client.py |
| BOM в skill.json | ✅ | utf-8-sig |
| Skills не в Skills/web/ | ✅ | Искать в Skills/ |
| community = int в graph.json | ✅ | str(community_raw) |
| graphify не в PATH | ✅ | Полный путь в GRAPHIFY_EXE |
| pip не в PATH | ✅ | python -m pip |
| CUDA падает | ✅ | OLLAMA_NO_CUDA=1 |
| LLM не видит конкретные skills | ✅ | _get_skills_catalog() читает skill.json |
| Агенты используют старый model= | ✅ | Переписаны на agent= |
| UTF-8 кодировка в Windows | ✅ | sys.stdout.reconfigure |

---

## 14. RECOVERY КОМАНДЫ

```powershell
# Перейти в папку
cd C:\Users\diman\Desktop\AI\Atlas

# Диагностика Brain + Model Router
python Config\llm_client.py --diagnose

# Тест с авто-контекстом
python Config\llm_client.py

# Полный pipeline (legacy)
python main.py "Сделай лендинг для кофейни"

# С конкретным skill
python main.py "Сайт для агентства" motion_premium

# Брендинг
python main.py "Создай бренд для барбершопа"

# AI-фотосессия
python main.py "Фотосессия для ресторана"

# Перестроить граф
python -c "from Brain.graphify_bridge import build_graph; build_graph(force=True)"

# AutoSkill Hunter
python Agents/auto_skill_hunter.py --max 5

# Self-Upgrade
python Tools/self_upgrade.py

# Добавить skill с GitHub
python Tools/skills_manager.py add https://github.com/user/repo.git name

# Ollama в CPU-режиме
$env:OLLAMA_NO_CUDA="1"
ollama run qwen2.5-coder:3b

# Git push
git add -A
git commit -m "update"
git push

# Запуск Atlas Code Agent (когда будет готов)
python atlas_core/agent.py
```

---

## 15. API КЛЮЧИ (Config/.env)

```env
# === API KEYS ===
GEMINI_API_KEY=                    # Пустой — блокирует Россию
CEREBRAS_API_KEY=                  # Не получен
GROQ_API_KEY=                      # Не получен
OPENROUTER_API_KEY=sk-or-v1-...    # ✅ Работает
UNSPLASH_ACCESS_KEY=               # Не получен
HUGGINGFACE_API_KEY=               # Не получен

# === OLLAMA ===
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_3B=qwen2.5-coder:3b
OLLAMA_MODEL_7B=qwen2.5-coder:7b

# === GRAPHIFY ===
GRAPHIFY_EXE=C:\Users\diman\Desktop\AI\graphify.exe
```

### Где получить ключи
- **OpenRouter:** https://openrouter.ai/keys ✅ (уже получен)
- **Cerebras:** https://cloud.cerebras.ai/ (1M токенов/день)
- **Groq:** https://console.groq.com/keys
- **Unsplash:** https://unsplash.com/developers
- **Hugging Face:** https://huggingface.co/settings/tokens

---

## 16. ДЛЯ НОВОЙ СЕССИИ

Если начинаешь новый чат — прикрепи этот файл. Новая LLM сразу увидит:
- Что сделано
- Что сломано
- Какой следующий шаг
- Архитектуру
- Правила

**Короткая инструкция для памяти (500 симв):**
> Atlas — локальная digital-студия на Python/Ollama. Переходим к Atlas Code Agent — автономной системе как Claude Code: Tool Use + сессионная память + Self-Upgrade. OpenRouter работает (Gemini 2.5 Pro). Ollama 3B/7B локально. Нужно создать atlas_core/ с session.py, context.py, tools.py, agent.py. GitHub: koghuhdlageneratorarf-eng/Atlas. Железо: GTX 1650 Ti 4GB, CPU-режим Ollama.

---

## 17. ФАЙЛЫ, КОТОРЫЕ МЕНЯЛИСЬ В ПОСЛЕДНИХ СЕССИЯХ

1. Config/.env (создан, OpenRouter ключ добавлен)
2. Config/models.yaml (создан, приоритеты без Gemini)
3. Config/llm_client.py (фикс кодировки UTF-8)
4. Agents/executive.py (model= → agent="executive")
5. Agents/brief.py (model= → agent="brief")
6. Agents/developer.py (model= → agent="developer")
7. Brain/graphify_bridge.py (создан, много фиксов)
8. Brain/memory_graph.py (создан)
9. main.py (обновлён — интеграция Brain)
10. Agents/auto_skill_hunter.py (создан)
11. Agents/product_router.py (создан)
12. Agents/branding_agent.py (создан, резерв)
13. Agents/media_agent.py (создан, резерв)
14. Tools/self_upgrade.py (фикс рекурсии)
15. Tools/skills_manager.py (git clone)
16. Skills/motion_premium/ (создан)
17. Skills/product_showcase/ (создан)
18. Skills/agency/ (клонирован с GitHub)
19. Memory/Ideas/roadmap.md (создан)

---

## 18. СЛЕДУЮЩИЙ ШАГ

**Создать ядро Atlas Code Agent:**

1. atlas_core/session.py — SQLite память сессии
2. atlas_core/context.py — менеджер контекста проекта  
3. atlas_core/tools.py — инструменты (read/write/run/edit/git)
4. atlas_core/agent.py — REPL + цикл Tool Use

**Тест:** python atlas_core/agent.py → "добавь модуль логирования" → агент сам читает файлы, планирует, пишет код, показывает diff.

---

**Конец MASTER CHECKPOINT v6.0**
