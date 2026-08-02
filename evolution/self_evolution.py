"""
Self Evolution Engine — Atlas самостоятельно улучшает себя.

Согласно Master Plan (Этап 15):
1. Найти слабое место
2. Проанализировать архитектуру
3. Создать предложение
4. Оценить риск
5. Построить Workflow
6. Изменить код
7. Протестировать
8. Commit
9. Обновить память
10. Продолжить
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.git_intelligence import GitIntelligence
from core.goal_engine import get_goal_engine
from core.permissions.engine import get_permission_engine
from core.runtime.engine import get_runtime
from core.symbol_resolver import SymbolResolver
from evolution.suggester import Suggester


class SelfEvolution:
    def __init__(self):
        self.runtime = get_runtime()
        self.goal_engine = get_goal_engine()
        self.resolver = SymbolResolver()
        self.permissions = get_permission_engine()
        self.git = GitIntelligence()
        self.suggester = Suggester()
        self.enabled = False

    def enable(self):
        self.enabled = True
        print("[SelfEvolution] Включён")

    def disable(self):
        self.enabled = False
        print("[SelfEvolution] Выключен")

    def analyze_architecture(self) -> list:
        """Анализирует архитектуру и находит слабые места."""
        print("[SelfEvolution] Анализ архитектуры...")
        issues = []

        # Проверяем ключевые файлы
        critical_files = [
            "atlas_core/agent.py",
            "atlas_core/tools.py",
            "core/runtime/engine.py",
        ]

        for filepath in critical_files:
            symbols = self.resolver.get_symbols(filepath)
            if symbols:
                func_count = len(symbols.get("functions", []))
                class_count = len(symbols.get("classes", []))
                if func_count > 20:
                    issues.append(
                        {
                            "file": filepath,
                            "issue": f"Слишком много функций ({func_count})",
                            "severity": "medium",
                        }
                    )
                if class_count > 10:
                    issues.append(
                        {
                            "file": filepath,
                            "issue": f"Слишком много классов ({class_count})",
                            "severity": "low",
                        }
                    )

        return issues

    def create_improvement_goal(self, issue: dict) -> str:
        """Создаёт цель для улучшения на основе найденной проблемы."""
        title = f"Рефакторинг: {Path(issue['file']).name}"
        description = f"{issue['issue']} (severity: {issue['severity']})"

        goal = self.goal_engine.create_goal(title, description)

        # Добавляем задачу на анализ
        self.goal_engine.add_task_to_goal(
            goal.id,
            f"Проанализировать {Path(issue['file']).name}",
            "Изучить код и найти конкретные проблемы",
        )

        # Добавляем задачу на рефакторинг
        self.goal_engine.add_task_to_goal(
            goal.id,
            f"Рефакторинг {Path(issue['file']).name}",
            "Улучшить структуру, разделить на модули",
        )

        # Добавляем задачу на тестирование
        self.goal_engine.add_task_to_goal(
            goal.id,
            "Тестирование после рефакторинга",
            "Убедиться, что ничего не сломалось",
        )

        return goal.id

    def run_evolution_cycle(self):
        """Один цикл самоэволюции."""
        if not self.enabled:
            print("[SelfEvolution] Выключен. Пропускаю.")
            return

        print("[SelfEvolution] Запуск цикла эволюции...")

        # 1. Найти слабое место
        issues = self.analyze_architecture()
        if not issues:
            print("[SelfEvolution] Архитектурных проблем не найдено")
            return

        print(f"[SelfEvolution] Найдено {len(issues)} проблем")

        # 2. Для каждой проблемы создать цель
        for issue in issues[:1]:  # Берём первую проблему
            goal_id = self.create_improvement_goal(issue)
            print(f"[SelfEvolution] Создана цель: {goal_id} для {issue['file']}")

            # 3. Добавляем в AutoPilot (если он включён)
            from autopilot.engine import get_autopilot

            ap = get_autopilot()
            if ap.enabled:
                print("[SelfEvolution] Передаю цель в AutoPilot")

    def status(self) -> str:
        return f"""
SelfEvolution Status
───────────────────
Enabled: {self.enabled}
"""


# Singleton
_self_evolution = None


def get_self_evolution() -> SelfEvolution:
    global _self_evolution
    if _self_evolution is None:
        _self_evolution = SelfEvolution()
    return _self_evolution


if __name__ == "__main__":
    se = get_self_evolution()
    print(se.status())

    se.enable()
    se.run_evolution_cycle()

    print("\nЦели после анализа:")
    for goal in se.goal_engine.get_all_goals():
        print(f"  - {goal.title} [{goal.id}]: {goal.status}")
