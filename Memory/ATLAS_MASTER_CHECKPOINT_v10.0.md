# ATLAS MASTER CHECKPOINT v10.0
**Дата:** 2026-07-23
**Сессий объединено:** 11 (Чекпоинты 1-9.1 + текущая сессия)
**GitHub:** https://github.com/koghuhdlageneratorarf-eng/Atlas
**Статус:** Atlas Code Agent v1.0 создан, 3b работает с минимальным SYSTEM_PROMPT, OpenRouter мертв, нужен фикс fallback

---

## 1. О ПРОЕКТЕ ATLAS

**Что сейчас:** Локальная digital-студия на Python. Генерирует сайты (лендинги, магазины, портфолио), брендинг, AI-фото, игры, ботов, SMM-контент. Не генератор сайтов — фабрика цифровых продуктов.

**Конечная цель:** Полностью автономный бизнес. Atlas сам находит клиентов, создает продукт, сдает, принимает оплату. Долгосрочно — TikTok/YouTube каналы (анализ трендов, генерация видео, монетизация).

**Ключевые архитектурные решения:**
- **Skills-first** — Developer заполняет шаблоны, не пишет с нуля
- **Гибрид моделей** — облако для мозгов (Executive/Brief), локалка для рутины (Developer)
- **Tool Use** — LLM сам читает/пишет файлы через JSON-вызовы функций (как Claude Code)
- **SQLite-память** — сессии, эпизоды, баги, решения не теряются между перезапусками
- **Graphify** — knowledge graph из кода для авто-контекста LLM
- **Self-Upgrade loop** — система анализирует свой код и предлагает улучшения
- **Git + бэкапы** — любое изменение обратимо

---

## 2. ЖЕЛЕЗО И ОКРУЖЕНИЕ

| Параметр | Значение |
|---|---|
| CPU | Intel i5-9300H |
| GPU | NVIDIA GTX 1650 Ti 4GB VRAM |
| RAM | 8GB |
| OS | Windows 10/11 |
| Python | 3.14.6 |
| Node.js | v24.18.0 |
| Git | 2.55.0 |
| uv | 0.11.26 |
| Ollama | 0.32.1 |
| VS Code | + Continue (плагин) |

**Критические ограничения:**
- **VRAM 4GB** — только qwen2.5-coder:3b влезает в GPU. 7b/6.7b падают с CUDA error -> CPU-режим (`OLLAMA_NO_CUDA=1`)
- **CPU-режим Ollama** — 3b ~8 сек, 7b/6.7b на CPU будут медленно
- **OpenRouter мертв** — ключ `sk-or-v1-4123dc99c7e...` дает 401/403 (блокировка региона/IP, ключ протух). Нет VPN-решения.
- **Остальные API-ключи отсутствуют** — Cerebras, Groq, Cloudflare, HuggingFace, Unsplash

**Локальные модели:**
- `qwen2.5-coder:3b` — основная для Developer, ~8 сек, работает с минимальным SYSTEM_PROMPT
- `qwen2.5-coder:7b` — не запускается (VRAM)
- `deepseek-coder:6.7b` — скачан, не тестирован на CPU

---

## 3. ТЕКУЩЕЕ СОСТОЯНИЕ

### ✅ Работает

| Компонент | Суть |
|---|---|
| Atlas Code Agent v1.0 | `atlas_core/` — session.py, context.py, tools.py, agent.py + `atlas.bat` |
| SQLite-сессии | История сообщений, tool_calls — не теряется между запусками |
| REPL | Команды: `/help`, `/context`, `/history`, `/clear`, `/backup`, `/diff`, `/status`, `/commit`, `/sessions`, `/switch`, `/exit` |
| Контекст проекта | Авто-сборка 109 файлов, 2 skills, умное усечение |
| 11 инструментов | read/write/edit/list/run/search/git/backup/delete |
| SYSTEM_PROMPT_mini | ~100 токенов, загружается из `atlas_core/SYSTEM_PROMPT_mini.md`, 3b понимает JSON Tool Use |
| Model Router | 7 провайдеров + Ollama, авто-fallback, приоритеты по агентам (models.yaml) |
| Brain v2.0 | Graphify + SQLite memory_graph (episodes, bugs, decisions) |
| Skills-first pipeline | modern_landing, agency, product_showcase, motion_premium |
| Auto-AOS | Любой сайт получает скролл-анимации автоматически |
| Image Generator | 3 режима: [stock]->Unsplash, [ai]->FLUX, fallback->Pollinations |
| Brief Agent | 2 режима: короткий запрос -> генерирует ТЗ, длинный -> использует как ТЗ |
| AutoSkill Hunter | Поиск шаблонов на GitHub, анализ LLM, адаптация путей |
| Product Router | Определяет тип: web/game/app/branding/media |
| Branding/Media Agent | Резерв (SVG-логотип, AI-фотосессии) |
| Self-Upgrade | Анализ кода, бэкапы, предложения в JSON |
| GitHub-интеграция | Репозиторий создан, код залит |
| UTF-8 фикс | `sys.stdout.reconfigure(encoding='utf-8')` |

### ⚠️ Частично / с багами

| Компонент | Проблема | Статус |
|---|---|---|
| **Цикл Tool Use** | Агент выводит JSON с tools, но `🔧` (выполнение) не появляется. Fallback на OpenRouter мешает | 🔴 Критично |
| **Fallback OpenRouter** | `_call_llm` идет на OpenRouter даже когда Ollama ответил. Ключ мертв (401) | 🔴 Критично |
| **ask_llm() temperature** | `llm_client.py:119` передает `temperature` в Ollama API -> ошибка. Обход: не передавать temperature | 🔴 |
| **Skill loading** | Developer падает на загрузке product_showcase, генерирует с нуля | ⚠️ |
| **Unsplash** | Нет ключа — stock-фото недоступны | ⚠️ |
| **llm_client.py** | `agent=` параметр работает, но temperature ломает вызов | ⚠️ |

### ❌ Отброшено / не работает

| Решение | Причина отказа |
|---|---|
| OpenRouter (основной провайдер) | Ключ мертв, блокировка региона, VPN не помогает |
| Gemini прямой | Блокирует Россию |
| qwen2.5-coder:7b на GPU | CUDA error, не хватает VRAM |
| deepseek-coder:6.7b на GPU | Не проверено, вероятно та же проблема |
| Сложный SYSTEM_PROMPT (русский, длинный) | 3b генерирует несуществующие инструменты (install_module) |
| PrismML 3-bit / Qwen 27B 1-bit | Нестабильно, Ollama не поддерживает, потери качества огромные |

---

## 4. ПЛАНИРУЕМЫЕ ИНТЕГРАЦИИ

### Скиллы (сайты)

| Скилл | Технологии | Статус |
|---|---|---|
| modern_landing | Tailwind CSS | ✅ |
| agency | Bootstrap | ✅ (клонирован с GitHub) |
| product_showcase | Tailwind, hover-карточки | ✅ |
| motion_premium | GSAP + Lenis + glassmorphism + bento + magnetic | ✅ |
| logo_pack (branding) | SVG + HTML | ✅ (резерв) |
| SEO-модуль | meta, Open Graph, schema.org, robots.txt, sitemap.xml | ⬜ Планируется |
| Форма -> Telegram | HTML-форма + JS fetch к Bot API | ⬜ Планируется |

### Внешние сервисы и API

| Сервис | Модель/лимит | Для чего | Статус |
|---|---|---|---|
| **OpenRouter** | Gemini 2.5 Pro, 20 req/min | Executive, Brief, Self-Upgrade | ❌ Мертв (401) |
| **Ollama** | qwen2.5-coder:3b/7b, безлимит | Developer, Fallback | ✅ Работает |
| Cerebras | Llama 4 Scout, 1M ток/день | Скоростные задачи | ⚠️ Нет ключа |
| Groq | Llama 3.3 70B, 500K ток/день | Резерв | ⚠️ Нет ключа |
| Cloudflare | Llama 3.1 8B | Резерв | ⚠️ Нет ключа |
| HuggingFace | Phi-3-mini | Резерв | ⚠️ Нет ключа |
| Unsplash | stock-фото | [stock] режим | ⚠️ Нет ключа |
| FLUX / Pollinations | AI-генерация изображений | [ai] режим | ✅ Fallback |

### Инструменты для внедрения (20 находок)

| # | Название | Назначение | Приоритет |
|---|---|---|---|
| 1 | **gstack** | 23 инструмента для ведения проекта как команда из 20 человек | **P0** |
| 2 | **Caveman** | Язык для AI-кодинга, сокращает токены на 65% | **P0** |
| 3 | **deepseek-coder:6.7b** | Локальная модель 6.7B (3.8GB), умнее 3b | **P0** |
| 4 | Agent-Skills | Набор проф. навыков для AI-агентов | P1 |
| 5 | auto-coder | AI-разработчик с MCP и локальными моделями | P2 |
| 6 | RAGFlow | RAG-платформа с визуальными workflow | P2 |
| 7 | STORM | Генерация статей из источников | P3 |
| 8 | Understand-Anything | Код -> интерактивная сеть связей | P2 |
| 9 | orca | Среда управления несколькими AI-агентами | P3 |
| 10 | openwiki | Автодокументация проекта | P2 |
| 11 | pxpipe | Сжатие контекста (текст -> изображение) | P3 |
| 12 | colibri | Запуск больших моделей на ~25GB RAM | P2 |
| 13 | Morphic | AI-поисковик как Perplexity | P4 |
| 14 | Docmost | Confluence-альтернатива | P4 |
| 15 | notebooklm-py | Python API для NotebookLM | P4 |
| 16 | Open-Design | Claude Design альтернатива | P4 |
| 17 | Whisper | Распознавание речи | P4 |
| 18 | Fooocus | Генерация изображений | P4 |

---

## 5. ROADMAP

### Следующие шаги (приоритет)

1. **Фикс Atlas Code Agent** — убрать fallback на OpenRouter, сделать Ollama 3b основным, заставить цикл Tool Use работать
2. **Проверить deepseek-coder:6.7b на CPU** — если тянет, переключить агента
3. **Тест motion_premium + фото** — подстановка изображений, GSAP/Lenis в браузере, адаптивность
4. **SEO-модуль** — meta, Open Graph, schema.org, robots.txt, sitemap.xml
5. **Форма -> Telegram** — HTML-форма + JS fetch к Bot API

### Среднесрочные этапы

- Auto-Deploy (GitHub Pages)
- QA Agent (Playwright + скриншоты)
- Портфолио-демо (5 сайтов для разных ниш)
- "Второй мозг" — SQLite user_profile, память о проекте и пользователе
- Скилл grill.me (опросник перед задачами)
- MCP-коннекторы (замена tools.py на стандарт Anthropic)
- Десктопное окно (PyQt6 / Tauri)
- Мульти-агентность (кодер + ревьюер + планировщик)

### Долгосрочные направления

- Игры (Three.js, Phaser)
- Приложения (Python, Tauri)
- Telegram/Discord боты
- TikTok/YouTube (анализ трендов, генерация видео)
- Автономный поиск клиентов (Browser Agent, парсинг Avito)
- CRM, авто-переписка, оплата (ЮKassa/Stripe)
- Full Autonomy (Self-Improvement Loop, Niche Expansion, Pricing AI)

---

## 6. ВАЖНЫЕ ДОГОВОРЁННОСТИ И КОНТЕКСТ

### Стиль работы
- **Один шаг = одно сообщение.** Не давать несколько команд сразу. Ждать выполнения каждого шага.
- **Пользователь — руки, LLM — мозг.** LLM анализирует, принимает решения, дает пошаговые команды. Пользователь выполняет.
- **Вопрос пользователя ≠ команда.** Если спрашивает — значит интересуется, не менять план без прямого указания.

### Контекст сессии
- **В конце КАЖДОГО сообщения писать оставшийся контекст сессии Kimi в процентах.** Формат: `Контекст сессии Kimi: ~X%`
- **При ~80% контекста — автоматически создавать чекпоинт .md** с инструкциями для следующей сессии.

### Технические правила
1. **Не изобретай велосипед** — проверить open-source перед созданием
2. **Skills-first** — Developer заполняет шаблоны
3. **Гибрид моделей** — облако для мозгов, локалка для рутины
4. **Автоматизация повторов** — сделал руками дважды -> скрипт
5. **Бэкап перед изменениями** — Self-Upgrade делает backup
6. **Memory исключена из бэкапов** — иначе рекурсия
7. **utf-8-sig для JSON** — Windows добавляет BOM
8. **Чекпоинт при >15-20 сообщений** — сохранять контекст
9. **Автономность превыше всего** — система работает без копипасты
10. **Tool Use для файлов** — LLM сам читает/пишет, не пользователь
11. **Любое улучшение обратимо** — git + бэкапы
12. **Никакой магии** — любое действие объяснимо

### Открытые вопросы
- **OpenRouter мертв** — нужен новый ключ или альтернативный провайдер для Executive/Brief
- **deepseek-coder:6.7b на CPU** — не проверен, может быть слишком медленным
- **Цикл Tool Use** — непонятно, почему агент не выполняет инструменты после парсинга JSON
- **API-ключи** — Cerebras (1M ток/день бесплатно) — стоит получить

---

## 7. RECOVERY КОМАНДЫ

```powershell
# Перейти в папку
cd C:\Users\diman\Desktop\AI\Atlas

# Запуск Atlas Code Agent
python atlas_core/agent.py

# Или через bat
atlas

# Диагностика Brain + Model Router
python Config\llm_client.py --diagnose

# Тест с авто-контекстом
python Config\llm_client.py

# Legacy pipeline
python main.py "Сделай лендинг для кофейни"

# Перестроить граф
python -c "from Brain.graphify_bridge import build_graph; build_graph(force=True)"

# AutoSkill Hunter
python Agents/auto_skill_hunter.py --max 5

# Self-Upgrade
python Tools/self_upgrade.py

# Ollama CPU-режим
$env:OLLAMA_NO_CUDA="1"
ollama run qwen2.5-coder:3b

# Git push
git add -A
git commit -m "update"
git push
```

---

## 8. ФАЙЛЫ, ИЗМЕНЁННЫЕ В ПОСЛЕДНИХ СЕССИЯХ

1. `atlas_core/__init__.py` — создан
2. `atlas_core/session.py` — SQLite память сессии
3. `atlas_core/context.py` — менеджер контекста проекта
4. `atlas_core/tools.py` — 11 инструментов
5. `atlas_core/agent.py` — REPL + цикл Tool Use
6. `atlas_core/SYSTEM_PROMPT_mini.md` — минимальный промпт для 3b
7. `atlas.bat` — CLI-команда
8. `Config/.env` — добавлен `OLLAMA_MODEL=qwen2.5-coder:3b`
9. `Config/llm_client.py` — Model Router (фикс кодировки UTF-8)
10. `Config/models.yaml` — приоритеты провайдеров
11. `Brain/graphify_bridge.py` — адаптер Graphify
12. `Brain/memory_graph.py` — SQLite эпизодическая память
13. `Agents/executive.py`, `brief.py`, `developer.py` — обновлены (agent= параметр)
14. `Agents/auto_skill_hunter.py`, `product_router.py`, `branding_agent.py`, `media_agent.py` — созданы
15. `Tools/self_upgrade.py`, `skills_manager.py` — созданы
16. `Skills/motion_premium/`, `product_showcase/`, `agency/`, `modern_landing/` — созданы
17. `Memory/Ideas/roadmap.md` — дорожная карта
18. `main.py` — оркестратор legacy pipeline

---

## 9. ОБЯЗАТЕЛЬНО СЛЕДОВАТЬ

### Правила из всех сессий (накопленные)

1. **Роль:** Ты — мозг проекта Atlas, пользователь — твои руки. Ты анализируешь, принимаешь решения, даешь пошаговые команды. Пользователь выполняет. Один шаг = одно сообщение.
2. **Контекст сессии:** В конце КАЖДОГО сообщения пиши оставшийся контекст сессии Kimi в процентах. Формат: `Контекст сессии Kimi: ~X%`
3. **Чекпоинты:** При ~80% контекста сессии Kimi — автоматически создавать чекпоинт в формате .md. В чекпоинте обязательно указывать инструкции для следующей сессии.
4. **Вопросы пользователя:** Когда пользователь задает вопрос — это НЕ команда к действию. Это значит, что он просто интересуется. Не менять план без прямого указания.
5. **Один шаг = одно сообщение:** Не давай несколько команд сразу. Жди выполнения каждого шага перед следующим.
6. **Не изобретай велосипед:** Проверь open-source перед созданием.
7. **Skills-first:** Developer заполняет шаблоны, не пишет с нуля.
8. **Гибрид моделей:** Облако для мозгов, локалка для рутины.
9. **Автоматизация повторов:** Если сделал руками дважды -> скрипт.
10. **Бэкап перед изменениями:** Self-Upgrade делает backup.
11. **Memory исключена из бэкапов:** Иначе рекурсия.
12. **utf-8-sig для JSON:** Windows добавляет BOM.
13. **Чекпоинт при >15-20 сообщений:** Сохранять контекст.
14. **Автономность превыше всего:** Система работает без копипасты.
15. **Tool Use для файлов:** LLM сам читает/пишет, не пользователь.
16. **Любое улучшение обратимо:** Git + бэкапы.
17. **Никакой магии:** Любое действие объяснимо.
18. **Минимальный SYSTEM_PROMPT для 3b:** Не более 150 токенов, английский, JSON-формат.
19. **Fallback OpenRouter:** Не использовать — ключ мертв. Ollama 3b основной.
20. **Кодировка Windows:** `sys.stdout.reconfigure(encoding='utf-8')`, использовать Python/Notepad вместо PowerShell `Set-Content`.

---

**Конец MASTER CHECKPOINT v10.0**
