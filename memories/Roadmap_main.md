# ATLAS ROADMAP v2

> Главная цель:
>
> Atlas становится ежедневным AI-ассистентом разработчика.
>
> Только после этого Atlas начинает самостоятельно разрабатывать себя.

---

# Главный принцип

Atlas — это Runtime.

LLM — лишь один из модулей.

Главная задача Runtime — предоставить модели:

- инструменты
- контекст
- память
- историю
- возможность работать с кодом

---

# MVP

До конца MVP Atlas должен полностью заменить ChatGPT
в ежедневной разработке.

То есть я могу открыть WebUI и написать:

> Найди где реализован Router

или

> Объясни архитектуру проекта

или

> Исправь ошибку

не открывая ChatGPT.

---

# Этап 1. Chat Core

Цель:

Получить полноценный AI Chat.

## Задачи

- [ ] единый API /chat
- [ ] OpenAI-compatible endpoint
- [ ] Streaming
- [ ] история сообщений
- [ ] системный промпт
- [ ] сохранение диалогов
- [ ] поддержка нескольких моделей

После этого Atlas становится обычным GPT.

---

# Этап 2. Router

Цель:

Любая модель подключается одинаково.

Структура

providers/

router/

## Задачи

- [ ] Router
- [ ] Provider Interface
- [ ] Ollama
- [ ] Gemini
- [ ] OpenRouter
- [ ] OpenAI
- [ ] Groq
- [ ] Cloudflare

Router сам выбирает нужную модель.

---

# Этап 3. Tool Calling

Atlas начинает пользоваться инструментами.

tools/

## Инструменты

- [ ] read_file
- [ ] write_file
- [ ] list_files
- [ ] grep
- [ ] bash
- [ ] search
- [ ] git_status
- [ ] git_diff

После этого Atlas уже полезнее ChatGPT.

---

# Этап 4. Project Context

Цель

Atlas понимает проект.

context/

## Задачи

- [ ] Project Scanner
- [ ] File Selector
- [ ] Dependency Scanner
- [ ] Symbol Resolver
- [ ] Prompt Builder

После этого можно спрашивать:

> Где создаётся Router?

> Какие файлы используют Executive?

---

# Этап 5. Developer Assistant

Теперь Atlas становится разработчиком.

Возможности

✔ объясняет код

✔ ищет зависимости

✔ отвечает по архитектуре

✔ предлагает изменения

Но ещё ничего не меняет.

---

# Этап 6. Patch Engine

Atlas начинает менять код.

patch/

## Возможности

- [ ] Unified Diff
- [ ] Search Replace
- [ ] Diff Preview
- [ ] Apply Patch
- [ ] Undo

Никакой полной перезаписи файлов.

---

# Этап 7. Validation

После изменения проекта.

validation/

## Проверки

- [ ] Syntax
- [ ] Ruff
- [ ] Black
- [ ] Tests
- [ ] Import Check

Если ошибка —

patch отклоняется.

---

# Этап 8. Git

git/

## Возможности

- [ ] Backup
- [ ] Commit
- [ ] Rollback
- [ ] Diff
- [ ] Branch

---

# Этап 9. Runtime

Только теперь появляется настоящий Runtime.

runtime/

Runtime управляет циклом

Task

↓

Collect Context

↓

Tool Calling

↓

Generate Patch

↓

Validate

↓

Review

↓

Done

---

# Этап 10. Planner

planner/

Atlas начинает разбивать задачи.

Например

> Добавь нового Provider

↓

Planner

↓

7 подзадач

↓

Executor

---

# Этап 11. Reviewer

После каждого изменения

Atlas проверяет сам себя.

Если плохо —

возвращает задачу обратно.

---

# Этап 12. Memory

Только после рабочего агента.

memory/

- [ ] Session Memory
- [ ] Long Memory
- [ ] Graph
- [ ] RAG

---

# Этап 13. Studio

Текущая Studio становится Skill.

skills/

studio/

Atlas вызывает её как инструмент.

Например

> Сделай лендинг

↓

Skill Studio

↓

готовый сайт

---

# Этап 14. Autonomous Development

Финальная цель.

Пользователь пишет

> Добавь MCP Provider

Atlas

✔ анализирует проект

✔ ищет нужные файлы

✔ пишет код

✔ запускает проверки

✔ показывает diff

✔ ждёт подтверждения

✔ делает commit

---

# Что НЕ делать сейчас

До завершения Developer Assistant запрещено:

- новые Skills
- MCP
- Telegram
- Analytics
- Event Bus
- новые Memory Provider
- новые пайплайны Studio
- рефакторинг ради красоты

Все силы идут на превращение Atlas
в ежедневного AI-разработчика.

---

# Критерии готовности

M1

Я пользуюсь Atlas вместо ChatGPT.

---

M2

Atlas понимает собственный проект.

---

M3

Atlas умеет безопасно менять код.

---

M4

Atlas проходит цикл

Task

↓

Patch

↓

Validation

↓

Review

---

M5

Atlas самостоятельно реализует небольшие задачи.