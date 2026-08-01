import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
ROADMAP_FILE = ROOT / "roadmap.yaml"

class RoadmapEngine:
    def __init__(self):
        self.data = self._load()
        self._flatten_tasks()

    def _load(self):
        if ROADMAP_FILE.exists():
            with open(ROADMAP_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {"stages": []}

    def _flatten_tasks(self):
        """Превращает список задач в плоский список с метаданными."""
        self.tasks = []
        for stage in self.data.get("stages", []):
            stage_name = stage.get("name", "Unknown")
            stage_id = stage.get("id", "unknown")
            priority = stage.get("priority", "P2")
            for task in stage.get("tasks", []):
                if isinstance(task, str):
                    task = {"title": task, "status": "pending"}
                self.tasks.append({
                    "stage": stage_name,
                    "stage_id": stage_id,
                    "priority": priority,
                    "id": task.get("id", task.get("title", "").lower().replace(" ", "_")),
                    "title": task.get("title", task),
                    "status": task.get("status", "pending")
                })

    def save(self):
        # Сохраняем обратно в YAML (пока не реализовано, чтобы не сломать структуру)
        pass

    def get_next_task(self):
        """Находит первую pending задачу."""
        for task in self.tasks:
            if task.get("status") == "pending":
                return task, None
        return None, None

    def mark_done(self, task_id: str):
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = "done"
                return True
        return False

    def status(self) -> str:
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.get("status") == "done")
        return f"📊 Прогресс: {done}/{total} задач выполнено"

    def list_tasks(self, status: str = None) -> str:
        result = []
        for t in self.tasks:
            if status and t.get("status") != status:
                continue
            result.append(f"[{t.get('stage')}] {t.get('title')} — {t.get('status')}")
        return "\n".join(result[:20]) + ("\n... и ещё" if len(result) > 20 else "")

if __name__ == "__main__":
    engine = RoadmapEngine()
    print(engine.status())
    task, _ = engine.get_next_task()
    if task:
        print(f"Следующая задача: {task['title']} ({task['stage']})")
    else:
        print("✅ Все задачи выполнены!")
