# ATLAS MASTER CHECKPOINT v9.1
**Дата:** 2026-07-22 03:08
**Сессий объединено:** 10 (Чекпоинт 1-8 + Текущая сессия)
**GitHub:** https://github.com/koghuhdlageneratorarf-eng/Atlas
**Статус:** Патч SYSTEM_PROMPT для 3b, тесты пройдены, проблема fallback на OpenRouter

---

## 1. ЧТО НОВОГО (от v8.0)

### ✅ Создан минимальный SYSTEM_PROMPT для 3b
```
atlas_core/SYSTEM_PROMPT_mini.md
```
**Содержимое:**
```
Reply JSON:{"thought":"...","tools":[{"name":"N","args":{}}],"response":"..."}
Tools:list_directory,read_file,write_file,edit_file,run_command,search_files,git_status,git_commit,backup_file
Use tools for files. Search first if unsure.
```

### ✅ Патч agent.py — загрузка SYSTEM_PROMPT из файла
```python
# Load SYSTEM_PROMPT from file for easy editing
_SYSTEM_PROMPT_PATH = Path(__file__).parent / "SYSTEM_PROMPT_mini.md"
if _SYSTEM_PROMPT_PATH.exists():
    SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = """You are Atlas Code Agent. Use tools. Reply ONLY in JSON format.
FORMAT: {"thought":"...","tools":[{"name":"TOOL","args":{}}],"response":"..."}
"""
```

### ✅ Пройдены тесты
| Шаг | Тест | Результат |
|---|---|---|
| 1 | Ollama версия | ✅ 0.32.1 |
| 2 | Список моделей | ✅ 3b, 7b, 6.7b скачаны |
| 3 | Железо: CPU/RAM/GPU | ✅ i5-9300H, 8GB, GTX 1650 Ti 4GB |
| 4 | OpenRouter через VPN | ❌ Ключ мёртв (401) |
| 5 | 3b + минимальный промпт | ✅ JSON Tool Use работает |
| 6 | ask_llm + SYSTEM_PROMPT_mini | ✅ Возвращает JSON с tools |
| 7 | REPL запуск | ✅ Баннер, приглашение atlas> |

---

## 2. БАГИ / В ПРОЦЕССЕ

| Проблема | Статус | Детали |
|---|---|---|
| **Агент идёт на OpenRouter fallback** | 🔴 | `_call_llm` вызывает `ask_llm`, но потом всё равно fallback на OpenRouter. Причина: `_parse_tool_response` возвращает `tools: []` когда 3b не понимает промпт, или `ask_llm` падает |
| **OpenRouter ключ мёртв** | 🔴 | 401 User not found. Не фиксится — нужен новый ключ/провайдер |
| **3b не понимает длинный SYSTEM_PROMPT** | 🟢 Фикс | Минимальный промпт (~100 токенов) работает |
| **Кодировка при создании файлов** | ⚠️ | PowerShell ломает UTF-8 при `Set-Content`. Решение: `notepad` или Python |
| **llm_client.py temperature** | ⚠️ | Баг из v8.0 — пока не трогали, т.к. 3b работает без temperature |

---

## 3. КЛЮЧЕВЫЕ ИНСАЙТЫ

1. **3b УМЕЕТ Tool Use** — при условии, что SYSTEM_PROMPT < 150 токенов.
2. **Минимальный промпт = работающий агент** — не нужна 6.7b или API.
3. **Fallback на OpenRouter — проблема** — агент не доверяет ответу 3b и идёт на API.
4. **GTX 1650 Ti 4GB** — только 3b влезает в VRAM. 6.7b/7b на CPU = медленно.
5. **OpenRouter 401** — ключ `sk-or-v1-4123dc99c7e...` мёртв, VPN не помогает.

---

## 4. ТЕКУЩИЙ СТАТУС AGENT.PY

### Что работает
- REPL с командами: `/help`, `/context`, `/history`, `/clear`, `/backup`, `/diff`, `/status`, `/exit`
- SQLite-сессии — история не теряется
- Загрузка SYSTEM_PROMPT из файла `SYSTEM_PROMPT_mini.md`
- `ask_llm` с 3b + минимальный промпт → JSON с `tools`

### Что сломано
- **Fallback на OpenRouter** — агент не использует локальную модель как основную
- **Цикл Tool Use не запускается через 3b** — агент выводит JSON, но `🔧` (выполнение) не появляется
- **`_parse_tool_response`** — возвращает `tools: []` при plain text ответе

---

## 5. СЛЕДУЮЩИЙ ШАГ (приоритет)

### Разобраться с fallback на OpenRouter
1. Проверить, что `_call_llm` действительно вызывает `ask_llm` с `agent='executive'`
2. Проверить, не падает ли `ask_llm` при `agent='executive'` (vs `developer`)
3. Если падает — пофиксить или обойти
4. Если работает — убрать fallback на OpenRouter, сделать Ollama основным

### Альтернатива
- Убрать OpenRouter fallback полностью — оставить только Ollama
- Добавить проверку: если Ollama не отвечает → сообщение об ошибке, не fallback

---

## 6. ФАЙЛЫ, ИЗМЕНЁННЫЕ В ЭТОЙ СЕССИИ

1. `atlas_core/agent.py` — патч SYSTEM_PROMPT (загрузка из файла)
2. `atlas_core/SYSTEM_PROMPT_mini.md` — создан
3. `Config/.env` — добавлен `OLLAMA_MODEL=qwen2.5-coder:3b`

---

## 7. КОРОТКАЯ ИНСТРУКЦИЯ ДЛЯ ПАМЯТИ (500 симв)

> Atlas v1.0: 3b модель работает с минимальным SYSTEM_PROMPT (~100 токенов). agent.py патч — загрузка промпта из файла. Fallback на OpenRouter — проблема, ключ мёртв (401). Следующий шаг: убрать fallback, сделать Ollama основным. Железо: i5-9300H, GTX 1650 Ti 4GB. GitHub: koghuhdlageneratorarf-eng/Atlas.

---

## 8. ИНСТРУКЦИИ ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ (обязательны к исполнению)

### Инструкция 1: Роль
**Ты — мозг проекта Atlas, пользователь — твои руки.** Ты анализируешь, принимаешь решения, даёшь пошаговые команды. Пользователь выполняет. Один шаг = одно сообщение.

### Инструкция 2: Контекст сессии
**В конце КАЖДОГО сообщения пиши оставшийся контекст сессии Kimi в процентах.** Формат: `Контекст сессии Kimi: ~X%`

### Инструкция 3: Чекпоинты
**При достижении ~80% контекста сессии Kimi — автоматически создавать чекпоинт в формате .md.** В чекпоинте обязательно указывать инструкции для следующей сессии.

### Инструкция 4: Вопросы пользователя
**Когда пользователь задаёт вопрос — это НЕ команда к действию.** Это значит, что он просто интересуется. Не меняй план без прямого указания.

### Инструкция 5: Формат работы
**Один шаг = одно сообщение.** Не давай несколько команд сразу. Жди выполнения каждого шага перед следующим.

---

**Конец MASTER CHECKPOINT v9.1**