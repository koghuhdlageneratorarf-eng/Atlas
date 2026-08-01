# Development Guide

Структура: atlas_core/, agents/, Config/, Brain/, Skills/, Projects/

Как добавить агента:
1. Создать agents/имя/agent.yaml
2. Добавить команду в atlas_core/agent.py
3. Перезапустить Atlas

Как добавить инструмент:
1. Добавить функцию в atlas_core/tools.py
2. Зарегистрировать в TOOL_REGISTRY
