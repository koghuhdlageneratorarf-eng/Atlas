# ATLAS MASTER CHECKPOINT v8.0
**Дата:** 2026-07-21
**Сессий объединено:** 9 (Чекпоинт 1-7 + Текущая сессия)
**GitHub:** https://github.com/koghuhdlageneratorarf-eng/Atlas
**Статус:** Создано ядро Atlas Code Agent v1.0, тесты пройдены, баги OpenRouter/temperature в процессе фикса, добавлена Roadmap 2026

---

## 1. ЧТО НОВОГО (от v7.0)

### ✅ Создано ядро Atlas Code Agent v1.0
```
atlas_core/
├── __init__.py      # Пакетный init
├── session.py       # SQLite память сессии (messages, tool_calls, история)
├── context.py       # Менеджер контекста проекта (дерево, кэш, поиск, skills)
├── tools.py         # 11 инструментов: read/write/edit/list/run/search/git/backup/delete
└── agent.py         # REPL + цикл Tool Use + fallback OpenRouter
```

**CLI-команда:** `atlas.bat` (Windows) / `atlas` (Linux/Mac)

### ✅ Пройдены тесты
| Шаг | Тест | Результат |
|---|---|---|
| 3 | Импорты (`session`, `context`, `tools`, `agent`) | ✅ OK |
| 4 | Сессия SQLite — создание, чтение, история | ✅ OK |
| 5 | Контекст проекта — 109 файлов, 2 skills | ✅ OK |
| 6 | Инструменты — `list_directory`, `search_files` | ✅ OK |
| 7 | Запуск REPL — баннер, приглашение `atlas>` | ✅ OK |

### 🔬 Новое: Диагностика LLM-стека (из Чекпоинта 6)
| Проверка | Результат |
|---|---|
| `_load_env()` читает `.env` | ✅ OK, ключ `sk-or-v1-4123dc99c7e` читается |
| `ask_llm` без `temperature` | ✅ OK, роутер выбирает Ollama (qwen2.5-coder:3b) |
| `ask_llm` с `temperature` | ❌ Падает (баг `llm_client.py:119`) |
| OpenRouter напрямую | ❌ 403 — блокировка по IP/региону/политике |
| Ollama 3b — простой prompt | ✅ Понимает JSON-формат `{"tools": [...]}` |
| Ollama 3b — сложный prompt | ❌ Генерирует несуществующие инструменты (`install_module`) |
| Ollama 7b | ❌ CUDA error — не хватает VRAM |
| `deepseek-coder:6.7b` | ⏳ Не проверен — следующий кандидат |

---

## 2. БАГИ / В ПРОЦЕССЕ

| Проблема | Статус | Детали |
|---|---|---|
| **OpenRouter 403 Forbidden** | 🔴 | Блокировка со стороны OpenRouter (регион/IP). Ключ валиден, но endpoint отвечает `Access denied by security policy`. Не фиксится кодом — нужен VPN/другой ключ/другой провайдер |
| **ask_llm() temperature** | 🔴 | `Config/llm_client.py:119` — передаёт `temperature` в API Ollama, вызывает ошибку. Не наша проблема, но ломает Model Router |
| **Ollama 3b не понимает SYSTEM_PROMPT** | 🔴 | Сложный prompt (русский, длинный) → модель генерирует несуществующие инструменты. Упрощённый prompt (английский, короткий) → работает, но агент всё равно не выполняет инструменты |
| **Цикл Tool Use не запускается** | 🔴 | Агент выводит `[THOUGHT]` и JSON, но `🔧` (выполнение инструмента) не появляется. Парсер `_parse_tool_response` работает на тестах. Проблема в `process()` или в `_call_llm` — требует отладки |
| **Skill loading (product_showcase)** | ⚠️ | Developer падает на загрузке skill, генерирует с нуля (из v6.0) |
| **Unsplash ключ** | ⚠️ | Image Generator без stock-фото (из v6.0) |
| **API-ключи (Cerebras, Groq, Cloudflare, HF)** | ⚠️ | Не критично, OpenRouter работает (из v6.0) |

---

## 3. ТЕКУЩИЙ СТАТУС AGENT.PY

### Что работает
- REPL с командами: `/help`, `/context`, `/history`, `/clear`, `/backup`, `/diff`, `/status`, `/commit`, `/sessions`, `/switch`, `/exit`
- SQLite-сессии — история не теряется
- Tool Use цикл — LLM → JSON с инструментами → выполнение → результат → LLM (структура есть, но не работает на практике)
- Контекст проекта — авто-сборка, приоритетные файлы, умное усечение
- Бэкап через `/backup`
- `SYSTEM_PROMPT` упрощён до английского, короткого формата

### Что сломано
- **LLM-вызов**: `ask_llm()` падает на `temperature` → fallback OpenRouter → 403 (ключ не читается из-за блокировки)
- **Fallback Ollama 3b**: понимает простой JSON, но не выполняет инструменты в цикле
- **Результат**: агент не может выполнить задачи требующие LLM (все задачи)

---

## 4. НАХОДКИ / ИНСТРУМЕНТЫ ДЛЯ ВНЕДРЕНИЯ (20 штук)

| # | Название | Что делает | Польза | Сложность | Нужно сейчас | Приоритет |
|---|---|---|---|---|---|---|
| 1 | **gstack** | 23 инструмента для ведения проекта как команда из 20 человек | Высшая — это буквально видение "AI-команды" | 4/5 | 🔥 Да | **P0** |
| 2 | **Caveman** | Простой язык для AI-кодинга, сокращает токены на 65% | Критично — решение проблемы слабой 3b модели | 2/5 | 🔥 Да | **P0** |
| 3 | **Agent-Skills** | Набор проф. навыков для AI-агентов | Высокая — можно встроить как скиллы в Atlas | 2/5 | ✅ Да | **P1** |
| 4 | **auto-coder** | AI-разработчик с MCP и локальными моделями | Конкурент/инспирация, изучить архитектуру | 3/5 | ⚠️ Потом | **P2** |
| 5 | **RAGFlow** | RAG-платформа с визуальными workflow | Для "второго мозга" и памяти проекта | 4/5 | ⚠️ Потом | **P2** |
| 6 | **STORM** | Генерация полноценных статей из источников | Для агента-аналитика/контент-отдела | 3/5 | ❌ Нет | **P3** |
| 7 | **Understand-Anything** | Код → интерактивная сеть связей | Визуализация кодовой базы Atlas | 3/5 | ⚠️ Потом | **P2** |
| 8 | **orca** | Среда управления несколькими AI-агентами | Для мульти-агентности | 3/5 | ❌ Нет | **P3** |
| 9 | **openwiki** | Автодокументация проекта | Для автогенерации доков | 2/5 | ⚠️ Потом | **P2** |
| 10 | **pxpipe** | Сжатие контекста (текст → изображение) | Экономия токенов для больших кодовых баз | 3/5 | ❌ Нет | **P3** |
| 11 | **colibri** | Запуск больших моделей на ~25GB RAM | Альтернатива Ollama | 3/5 | ⚠️ Потом | **P2** |
| 12 | **Morphic** | AI-поисковик как Perplexity | Не про код | 3/5 | ❌ Нет | **P4** |
| 13 | **Docmost** | Confluence-альтернатива | База знаний, не про агентов | 3/5 | ❌ Нет | **P4** |
| 14 | **notebooklm-py** | Python API для NotebookLM | Для контента, не для код-агента | 2/5 | ❌ Нет | **P4** |
| 15 | **Open-Design** | Claude Design альтернатива | Фронтенд/дизайн | 3/5 | ❌ Нет | **P4** |
| 16 | **Whisper** | Распознавание речи | Голосовой ввод, не приоритет | 2/5 | ❌ Нет | **P4** |
| 17 | **Fooocus** | Генерация изображений | Не релевантно для код-агента | — | ❌ Нет | **P4** |
| 18 | **PrismML (тернарная квантизация)** | Экспериментальная квантизация 3-bit | Нестабильно, Ollama не поддерживает | — | ❌ Нет | — |
| 19 | **Qwen 27B 1-bit** | Очень большая модель в 1-bit | Потери качества огромные, не для production | — | ❌ Нет | — |
| 20 | **deepseek-coder:6.7b** | Локальная модель 6.7B (3.8 GB) | Умнее 3b, может работать на CPU | 2/5 | 🔥 Да | **P0** |

---

## 5. ROADMAP 2026 (Рекомендуемый порядок)

```
1. Фикс текущего агента (deepseek-coder:6.7b или API)
   ↓
2. "Второй мозг" — память о проекте и о тебе (SQLite user_profile)
   ↓
3. Скилл grill.me (опросник перед задачами)
   ↓
4. MCP-коннекторы (замена tools.py на стандарт Anthropic)
   ↓
5. Десктопное окно (PyQt6 / Tauri)
   ↓
6. Мульти-агентность (2-3 роли: кодер + ревьюер + планировщик)
   ↓
7. Автономный поиск улучшений (cron + GitHub API)
```

**Ключевой bottleneck:** Ollama 3b на CPU не тянет даже одного агента-кодера.
**Решение:** Либо deepseek-coder:6.7b (проверить), либо API-ключи (OpenAI/Anthropic), либо гибрид: простые задачи → Ollama, сложные → API.

---

## 6. СЛЕДУЮЩИЙ ШАГ (приоритет)

### Проверить deepseek-coder:6.7b
1. Запустить: `ollama run deepseek-coder:6.7b -- "Say hello"`
2. Если работает — переключить агента на эту модель (через `OLLAMA_MODEL`)
3. Проверить, понимает ли 6.7b формат JSON с `thought/tools/response`
4. Если да — проверить цикл Tool Use: `atlas> добавь модуль логирования`

### Альтернатива (если 6.7b не работает)
- Разобраться, почему цикл Tool Use не запускается (отладка `process()`)
- Или перейти на API (OpenAI/Anthropic) для executive-агента

---

## 7. ФАЙЛЫ, ИЗМЕНЁННЫЕ В ЭТОЙ СЕССИИ

1. `atlas_core/__init__.py` — создан
2. `atlas_core/session.py` — создан
3. `atlas_core/context.py` — создан
4. `atlas_core/tools.py` — создан
5. `atlas_core/agent.py` — создан (v1.0, SYSTEM_PROMPT упрощён)
6. `atlas.bat` — создан

---

## 8. КОРОТКАЯ ИНСТРУКЦИЯ ДЛЯ ПАМЯТИ (500 симв)

> Atlas Code Agent v1.0 создан: atlas_core/ с session.py, context.py, tools.py, agent.py + atlas.bat. Тесты 1-7 пройдены. Баги: OpenRouter 403 (блокировка), temperature в llm_client.py, Ollama 3b не выполняет инструменты. Найдены 20 инструментов для внедрения (P0: gstack, Caveman, deepseek-coder:6.7b). Roadmap: фикс агента → второй мозг → grill.me → MCP → десктоп → мульти-агенты. Следующий шаг — проверить deepseek-coder:6.7b. GitHub: koghuhdlageneratorarf-eng/Atlas.

---

## 9. ПОЛНАЯ ИСТОРИЯ СЕССИИ (Чекпоинт 6 — сырой лог)

<details>
<summary>Раскрыть полный лог сессии (для детального восстановления)</summary>


### События сессии (хронология):

**[Тест 1] Проверка `_load_env()`**
- Команда: `python -c "import sys; sys.path.insert(0, '.'); from atlas_core.agent import _load_env; import os; print('KEY:', os.environ.get('OPENROUTER_API_KEY','нет')[:20])"`
- Результат: `KEY: sk-or-v1-4123dc99c7e` ✅

**[Тест 2] Проверка `ask_llm` без temperature**
- Команда: `python -c "import sys; sys.path.insert(0, '.'); from atlas_core.agent import _load_env; from Config.llm_client import ask_llm; _load_env(); r = ask_llm([{'role':'user','content':'hi'}], agent='developer'); print('OK:', r[:50])"`
- Результат: `[Brain] developer → Ollama (qwen2.5-coder:3b) OK: Hello! How can I assist you today?` ✅

**[Тест 3] Запуск REPL + /help**
- Команда: `python atlas_core/agent.py` → `atlas> /help`
- Результат: REPL работает, команды отвечают ✅

**[Тест 4] Первая попытка задачи: "добавь модуль логирования"**
- Результат: OpenRouter 403 → CEREBRAS (no key) → GROQ (no key) → Ollama 3b
- Ollama вернул: `{"tools": [{"name": "install_module", "args": {"module": "logging"}}]}` — инструмент `install_module` не существует ❌
- Агент не выполнил инструмент, просто вывел JSON ❌

**[Тест 5] Диагностика OpenRouter 403**
- Команда: `python -c "import os, requests; from atlas_core.agent import _load_env; _load_env(); k = os.environ.get('OPENROUTER_API_KEY',''); print('KEY:', k[:20] if k else 'НЕТ'); h={'Authorization':f'Bearer {k}','Content-Type':'application/json'}; r=requests.post('https://openrouter.ai/api/v1/auth/key', headers=h); print('Status:', r.status_code); print(r.text[:300])"`
- Результат: `KEY: sk-or-v1-4123dc99c7e Status: 403 {"success": false, "error": "Access denied by security policy."}`
- Вывод: Ключ валиден, но OpenRouter блокирует по региону/IP ❌

**[Тест 6] Проверка парсера `_parse_tool_response`**
- Создан `test_parse.py` с JSON-ответом
- Результат: `tools: [{'name': 'list_directory', 'args': {'path': '.'}}]` ✅
- Вывод: Парсер работает

**[Тест 7] Проверка реального ответа Ollama 3b**
- Создан `test_ollama.py` с запросом к executive
- Результат: Ollama вернул `{"files": [...]}` вместо `{"thought": "...", "tools": [...], "response": "..."}` ❌
- Вывод: 3b не понимает сложный SYSTEM_PROMPT

**[Тест 8] Упрощённый prompt для 3b**
- Системный prompt заменён на короткий английский: `You are Atlas Code Agent. Use tools to work with files. Reply ONLY in JSON format.`
- Тест: `list_directory .` → 3b вернул `{"tools": [{"name": "run_command", "args": {"cmd": "ls"}}], "response": "..."}` ✅
- Но: агент всё равно не выполнил инструмент (нет строки `🔧 run_command(...)`) ❌

**[Тест 9] Проверка 7b модели**
- Команда: `ollama run qwen2.5-coder:7b -- "Say hello"`
- Результат: `Error: 500 Internal Server Error: CUDA error: shared object initialization failed` ❌
- Вывод: Не хватает VRAM для 7b

**[Тест 10] Проверка deepseek-coder:6.7b**
- Не выполнен — пользователь не дома, отложено на потом ⏳

**[Промежуточное] Анализ 20 находок**
- Составлена таблица с оценкой по релевантности (см. раздел 4)
- Топ-3: gstack (P0), Caveman (P0), deepseek-coder:6.7b (P0)

**[Промежуточное] Roadmap 2026**
- Составлен 7-шаговый план развития (см. раздел 5)
- Главный bottleneck: Ollama 3b на CPU

**[Промежуточное] Правило контекста**
- Пользователь попросил: "в конце каждого сообщения пиши оставшийся контекст сессии Kimi (токены до лимита) в %"
- Запомнено в memory_instruction

</details>

---

**Конец MASTER CHECKPOINT v8.0**
