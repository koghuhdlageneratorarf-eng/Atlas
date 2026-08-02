Atlas Roadmap Current Target

Version: 3.2
Focus: DeepSeek Replacement
Priority: Reliability First

STATUS
Completed
P0 — Foundation

✅ Runtime
✅ Agents
✅ Memory
✅ Tools
✅ Plugins
✅ Git Integration
✅ Model Router

P0+ — AI Software Engineer Core

Статус:

🟡 Реализовано, требуется стабилизация

Есть:

✅ Project Intelligence
✅ Code Search
✅ Symbol Analysis
✅ Patch System
✅ Multi-file Editing
✅ Git Operations
✅ Basic Debugging
✅ Development Memory

P0.5 — Reliability Layer
Цель

Сделать Atlas надёжным автономным разработчиком.

1. Self-Debugger Reliability 🔴
Проблема

Atlas умеет создавать исправления, но иногда генерирует неправильные патчи.

Задачи
 Проверка diff перед применением
 Проверка изменения после применения
 Проверка, что ошибка действительно исправлена
 Автоматическая повторная генерация исправления
 Ограничение количества попыток
 Сохранение истории исправлений
Критерий готовности

Atlas способен самостоятельно исправлять типовые ошибки без участия пользователя.

2. Autonomous Development Loop 🔴
Цель

Один цикл разработки без ручного управления.

Задача

↓

Анализ

↓

План

↓

Изменение

↓

Тест

↓

Исправление

↓

Commit

↓

Отчёт
Задачи
 Единая команда разработки
 Автоматический запуск проверок
 Автоматическое исправление ошибок
 Финальный отчёт
3. Executor Mode 🔴
Проблема

Atlas иногда выступает как консультант.

Задачи

Добавить режимы:

Advisor

Обсуждение и идеи.

Executor

Выполнение действий.

Правило:

Если пользователь говорит:

"сделай", "добавь", "исправь"

→ использовать Executor.

4. Git Safety 🟡
Задачи
 Автоматическая ветка перед изменениями
 Backup
 Commit после успешного теста
 Rollback при ошибке
 Diff Review
5. Permission Layer 🟡
Цель

Безопасное автономное изменение.

Уровни:

SAFE:

чтение;
анализ;
поиск.

MEDIUM:

изменение кода;
создание файлов.

HIGH:

удаление;
изменение ядра;
установка зависимостей.
6. Testing System 🟡
Задачи

Добавить тесты:

Patch Engine
AST Editor
Memory
Runtime
Agents
Tools

Добавить:

coverage report
regression tests
7. Model Independence 🟡

Цель:

Atlas не зависит от одной модели.

Задачи:

 Local fallback
 Model Router
 Code model
 Reasoning model
 Cheap model
Definition of Done

Atlas считается готовым заменить DeepSeek, когда:

✅ Может понять проект.

✅ Может предложить решение.

✅ Может изменить несколько файлов.

✅ Может проверить изменения.

✅ Может исправить ошибки.

✅ Может откатиться.

✅ Может сохранить историю решений.

✅ Может выполнять цикл разработки без ручного контроля.