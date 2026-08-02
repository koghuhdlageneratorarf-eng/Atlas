import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

"""
Goal Engine — работа с целями, а не задачами.

Согласно Master Plan (Этап 12):
- Цель → Task Graph → задачи
- После выполнения задачи — выбор следующей
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from core.runtime.engine import Task, TaskState, get_runtime


@dataclass
class Goal:
    id: str
    title: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active | completed | failed | paused
    tasks: list[str] = field(default_factory=list)  # ID задач
    current_task_index: int = 0


class GoalEngine:
    def __init__(self):
        self.goals: dict[str, Goal] = {}
        self.runtime = get_runtime()

    def create_goal(self, title: str, description: str = "") -> Goal:
        """Создать цель."""
        goal = Goal(id=uuid.uuid4().hex[:8], title=title, description=description)
        self.goals[goal.id] = goal
        print(f"[GoalEngine] Создана цель: {title} ({goal.id})")
        return goal

    def add_task_to_goal(
        self, goal_id: str, task_title: str, task_description: str = ""
    ) -> str | None:
        """Добавить задачу к цели."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        task = self.runtime.create_task(task_title, task_description)
        goal.tasks.append(task.id)
        print(f"[GoalEngine] Задача {task.id} добавлена к цели {goal.title}")
        return task.id

    def get_next_task(self, goal_id: str) -> Task | None:
        """Получить следующую невыполненную задачу из цели."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        if goal.status != "active":
            return None
        for task_id in goal.tasks:
            task = self.runtime.get_task(task_id)
            if task and task.state != TaskState.DONE:
                return task
        return None

    def get_all_goals(self) -> list[Goal]:
        return list(self.goals.values())

    def get_active_goals(self) -> list[Goal]:
        return [g for g in self.goals.values() if g.status == "active"]

    def complete_goal(self, goal_id: str) -> bool:
        """Отметить цель как завершённую."""
        goal = self.goals.get(goal_id)
        if not goal:
            return False
        # Проверяем, все ли задачи выполнены
        for task_id in goal.tasks:
            task = self.runtime.get_task(task_id)
            if task and task.state != TaskState.DONE:
                return False
        goal.status = "completed"
        print(f"[GoalEngine] Цель завершена: {goal.title}")
        return True

    def status(self) -> str:
        lines = ["Goal Engine Status", "────────────────"]
        for goal in self.goals.values():
            tasks_done = sum(
                1
                for t in goal.tasks
                if self.runtime.get_task(t)
                and self.runtime.get_task(t).state == TaskState.DONE
            )
            total = len(goal.tasks)
            status = (
                "✅"
                if goal.status == "completed"
                else "🔄" if goal.status == "active" else "⏸️"
            )
            lines.append(
                f"{status} {goal.title} [{goal.id}] — {tasks_done}/{total} задач"
            )
        return "\n".join(lines)


# Singleton
_goal_engine = None


def get_goal_engine() -> GoalEngine:
    global _goal_engine
    if _goal_engine is None:
        _goal_engine = GoalEngine()
    return _goal_engine


if __name__ == "__main__":
    ge = get_goal_engine()

    # Создаём цель
    goal = ge.create_goal(
        "Разработка Runtime Engine", "Реализовать полноценный Runtime"
    )

    # Добавляем задачи
    ge.add_task_to_goal(
        goal.id, "Создать базовый Runtime", "Базовый класс RuntimeEngine"
    )
    ge.add_task_to_goal(goal.id, "Добавить Event Bus", "Шина событий для Runtime")
    ge.add_task_to_goal(goal.id, "Добавить State Machine", "Валидация переходов")

    print(ge.status())

    # Получаем следующую задачу
    next_task = ge.get_next_task(goal.id)
    if next_task:
        print(f"Следующая задача: {next_task.title} ({next_task.id})")
