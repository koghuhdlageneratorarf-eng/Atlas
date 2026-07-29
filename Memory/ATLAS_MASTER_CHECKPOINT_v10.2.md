# ATLAS MASTER CHECKPOINT v10.2
**Дата:** 2026-07-24
**Сессий объединено:** 12 (Чекпоинты 1-10.1 + текущая сессия)
**GitHub:** https://github.com/koghuhdlageneratorarf-eng/Atlas
**Статус:** Все API получены (OpenRouter, Gemini, Groq, Cloudflare, Unsplash, Cerebras). Tool Use работает на Ollama 3b. Проблема: облачные модели (OpenRouter/Gemini) игнорируют SYSTEM_PROMPT, возвращают свой формат JSON.

---

## 1. О ПРОЕКТЕ ATLAS

Atlas — локальная digital-студия на Python. Генерирует сайты, брендинг, AI-фото, игры, ботов, SMM-контент. Конечная цель — полностью автономный бизнес.

Ключевые архитектурные решения:
- Skills-first — Developer заполняет шаблоны
- Гибрид моделей — облако для мозгов, локалка для рутины
- Tool Use — LLM сам читает/пишет файлы через JSON-вызовы
- SQLite-память — сессии не теряются
- Graphify — knowledge graph из кода
- Self-Upgrade loop — система анализирует свой код
- Git + бэкапы — любое изменение обратимо

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

**Критические ограничения:**
- VRAM 4GB — только qwen2.5-coder:3b в GPU. 7b/6.7b → CPU-режим
- Ollama 3b нестабильна — иногда plain text вместо JSON

**Локальные модели:**
- qwen2.5-coder:3b — основная, ~8 сек, Tool Use работает
- qwen2.5-coder:7b — не запускается (VRAM)
- deepseek-coder:6.7b — скачан, не тестирован на CPU

---

## 3. ТЕКУЩЕЕ СОСТОЯНИЕ

### ✅ Работает

| Компонент | Суть |
|---|---|
| Atlas Code Agent v1.0 | atlas_core/ — session, context, tools, agent + atlas.bat |
| Tool Use цикл (Ollama 3b) | LLM → JSON → выполнение → результат → LLM |
| JSON-парсер | Фиксит raw newlines внутри строк от 3b |
| SQLite-сессии | История не теряется |
| REPL | /help, /context, /history, /clear, /backup, /diff, /status, /commit, /sessions, /switch, /exit |
| 11 инструментов | read/write/edit/list/run/search/git/backup/delete |
| Model Router | 7 провайдеров + Ollama, авто-fallback |
| Brain v2.0 | Graphify + SQLite memory_graph |
| Skills-first pipeline | modern_landing, agency, product_showcase, motion_premium |
| Auto-AOS | Скролл-анимации автоматически |
| Image Generator | [stock]-&gt;Unsplash, [ai]-&gt;FLUX, fallback-&gt;Pollinations |
| Brief Agent | 2 режима генерации ТЗ |
| AutoSkill Hunter | Поиск шаблонов на GitHub |
| Product Router | Определяет тип продукта |
| Self-Upgrade | Анализ кода, бэкапы |
| GitHub-интеграция | Репозиторий создан, код залит |
| UTF-8 фикс | sys.stdout.reconfigure |

### ⚠️ Частично / с багами

| Компонент | Проблема | Статус |
|---|---|---|
| **Облачные модели игнорируют SYSTEM_PROMPT** | OpenRouter/Gemini возвращают `{"tools": [{"type": "..."}]}` вместо Atlas-формата | 🔴 Критично |
| **Ollama 3b нестабильность** | Иногда plain text, иногда свой формат JSON | ⚠️ |
| **Skill loading** | Developer падает на product_showcase | ⚠️ |
| **Cerebras 404** | Модель llama-4-scout не найдена — нужен другой endpoint | ⚠️ |
| **Gemini 429** | Too Many Requests — лимит или блокировка | ⚠️ |

### ❌ Отброшено

| Решение | Причина |
|---|---|
| qwen2.5-coder:7b на GPU | CUDA error, не хватает VRAM |
| Сложный SYSTEM_PROMPT (русский) | 3b генерирует несуществующие инструменты |

---

## 4. API КЛЮЧИ (Config/.env)

| Сервис | Ключ | Статус |
|---|---|---|
| OpenRouter | ✅ Новый ключ | Работает (1.5s) |
| Gemini | ✅ Новый ключ | 429 Too Many Requests |
| Groq | ✅ Новый ключ | Работает (0.5s) |
| Cloudflare | ✅ Токен + Account ID | Работает (0.8s) |
| Unsplash | ✅ Access Key | Не тестирован |
| Cerebras | ✅ Новый ключ | 404 (модель не найдена) |
| HuggingFace | ❌ Нет | Не нужен |

---

## 5. ПЛАНИРУЕМЫЕ ИНТЕГРАЦИИ

### Скиллы

| Скилл | Технологии | Статус |
|---|---|---|
| modern_landing | Tailwind CSS | ✅ |
| agency | Bootstrap | ✅ |
| product_showcase | Tailwind | ✅ |
| motion_premium | GSAP + Lenis + glassmorphism | ✅ |
| SEO-модуль | meta, Open Graph, schema.org | ⬜ |
| Форма -&gt; Telegram | HTML + JS fetch | ⬜ |

### Внешние сервисы

| Сервис | Для чего | Статус |
|---|---|---|
| Ollama 3b | Developer, основной | ✅ |
| OpenRouter | Executive/Brief | ✅ Работает, но игнорирует промпт |
| Groq | Резерв | ✅ Работает |
| Cloudflare | Резерв | ✅ Работает |
| Gemini | Резерв | ⚠️ 429 |
| Cerebras | Резерв | ⚠️ 404 |

### Инструменты для внедрения

| # | Название | Назначение | Приоритет |
|---|---|---|---|
| 1 | Aider | Готовый AI-агент с git, 45k stars | **P0** |
| 2 | LiteLLM | Единый интерфейс для всех провайдеров | **P0** |
| 3 | Caveman | Язык для AI-кодинга, -65% токенов | P1 |

---

## 6. ROADMAP

### Следующие шаги (приоритет)
1. **Фикс SYSTEM_PROMPT** — добавить пример JSON, чтобы облачные модели понимали формат Atlas
2. **Адаптивный парсер** — поддержка форматов OpenRouter (`type`/`path`) и Ollama (`type`/`files`)
3. **Тест motion_premium + фото** — подстановка изображений, GSAP/Lenis
4. **SEO-модуль** — meta, Open Graph, schema.org
5. **Форма -&gt; Telegram** — HTML-форма + JS fetch

### Среднесрочно
- Auto-Deploy (GitHub Pages)
- QA Agent (Playwright)
- Портфолио-демо (5 сайтов)
- "Второй мозг" — SQLite user_profile
- MCP-коннекторы
- Десктопное окно (PyQt6 / Tauri)

### Долгосрочно
- Игры (Three.js, Phaser)
- Telegram/Discord боты
- TikTok/YouTube
- Автономный поиск клиентов
- Full Autonomy

---

## 7. ВАЖНЫЕ ДОГОВОРЁННОСТИ

1. Роль: Ты — мозг, пользователь — руки. Один шаг = одно сообщение.
2. Вопрос ≠ команда. Не менять план без прямого указания.
3. Контекст сессии: писать ~X% в конце каждого сообщения.
4. Чекпоинт при ~80% контекста.
5. Не изобретай велосипед — проверь open-source.
6. Skills-first — Developer заполняет шаблоны.
7. Гибрид моделей — облако для мозгов, локалка для рутины.
8. Автоматизация повторов — дважды руками → скрипт.
9. Бэкап перед изменениями.
10. Memory исключена из бэкапов.
11. utf-8-sig для JSON на Windows.
12. Tool Use для файлов — LLM сам читает/пишет.
13. Любое улучшение обратимо — git + бэкапы.
14. Минимальный SYSTEM_PROMPT для 3b — &lt;150 токенов, английский, JSON.
15. Fallback OpenRouter — не использовать, ключ мёртв (устарело, ключ обновлён).
16. Windows: sys.stdout.reconfigure(encoding='utf-8'), Python/Notepad вместо PowerShell Set-Content.

---

## 8. RECOVERY КОМАНДЫ

```powershell
cd C:\Users\diman\Atlas
python atlas_core\agent.py
# или
atlas

# Диагностика
python Config\llm_client.py --diagnose

# Legacy pipeline
python main.py "Сделай лендинг для кофейни"

# Перестроить граф
python -c "from Brain.graphify_bridge import build_graph; build_graph(force=True)"

# AutoSkill Hunter
python Agents\auto_skill_hunter.py --max 5

# Self-Upgrade
python Tools\self_upgrade.py

# Ollama CPU-режим
$env:OLLAMA_NO_CUDA="1"
ollama run qwen2.5-coder:3b

# Git
git add -A
git commit -m "update"
git push