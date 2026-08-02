"""
Scheduler — автоматический запуск задач по расписанию.

Согласно Master Plan (Этап 13):
- каждые 30 минут — проверять Roadmap
- каждый день — искать архитектурные проблемы
- каждую неделю — искать технический долг
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: int
    action: Callable
    last_run: datetime | None = None
    enabled: bool = True


class Scheduler:
    def __init__(self):
        self.tasks: list[ScheduledTask] = []
        self.running = False
        self.thread: threading.Thread | None = None

    def add_task(self, name: str, interval_seconds: int, action: Callable):
        """Добавить задачу с интервалом в секундах."""
        self.tasks.append(
            ScheduledTask(name=name, interval_seconds=interval_seconds, action=action)
        )
        print(
            f"[Scheduler] Добавлена задача: {name} (каждые {interval_seconds//60} мин)"
        )

    def start(self):
        """Запустить планировщик в фоновом потоке."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("[Scheduler] Запущен")

    def stop(self):
        """Остановить планировщик."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[Scheduler] Остановлен")

    def _run(self):
        """Основной цикл планировщика."""
        while self.running:
            now = datetime.now()
            for task in self.tasks:
                if not task.enabled:
                    continue
                if (
                    task.last_run is None
                    or (now - task.last_run).total_seconds() >= task.interval_seconds
                ):
                    try:
                        task.action()
                        task.last_run = now
                        print(
                            f"[Scheduler] Выполнена: {task.name} в {now.strftime('%H:%M:%S')}"
                        )
                    except Exception as e:
                        print(f"[Scheduler] Ошибка в {task.name}: {e}")
            time.sleep(10)  # Проверка каждые 10 секунд

    def status(self) -> str:
        """Статус планировщика."""
        lines = ["Scheduler Status", "────────────────", f"Running: {self.running}"]
        for task in self.tasks:
            last = task.last_run.strftime("%H:%M:%S") if task.last_run else "never"
            status = "✅" if task.enabled else "❌"
            lines.append(f"{status} {task.name}: last run {last}")
        return "\n".join(lines)


# Singleton
_scheduler = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


if __name__ == "__main__":
    s = get_scheduler()

    def test_task():
        print("  ⏰ Тестовая задача выполнена")

    s.add_task("test", 30, test_task)
    s.start()

    print(s.status())

    try:
        time.sleep(65)
    except KeyboardInterrupt:
        pass
    finally:
        s.stop()
