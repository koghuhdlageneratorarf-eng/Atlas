"""
Пример плагина для Atlas.

Структура плагина:
- register() → возвращает метаданные и список команд
- Функции-обработчики для каждой команды
"""


def register():
    return {
        "name": "Example Plugin",
        "version": "1.0.0",
        "description": "Пример плагина для демонстрации",
        "commands": {"/example": "handle_example", "/hello": "handle_hello"},
    }


def handle_example(args: str) -> str:
    """Обработчик команды /example."""
    return f"👋 Пример плагина! Аргументы: {args if args else 'нет'}"


def handle_hello(args: str) -> str:
    """Обработчик команды /hello."""
    name = args.strip() or "Мир"
    return f"Привет, {name}! Это плагин Example Plugin."
