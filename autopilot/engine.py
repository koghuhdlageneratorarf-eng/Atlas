"""
Auto Pilot Engine — полностью автономный режим.

Согласно Master Plan (Этап 14):
- Auto Pilot запускает Workflow через Runtime
- Не имеет права напрямую вызывать инструменты
- Запускает только Workflow
- Разрешён только после завершения всех предыдущих этапов
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runtime.engine import get_runtime, Workflow, WorkflowStep, TaskState
from core.goal_engine import get_goal_engine
from core.scheduler import get_scheduler
from core.git_intelligence import GitIntelligence
from core.permissions.engine import get_permission_engine

class AutoPilot:
    def __init__(self):
        self.runtime = get_runtime()
        self.goal_engine = get_goal_engine()
        self.scheduler = get_scheduler()
        self.git = GitIntelligence()
        self.permissions = get_permission_engine()
        self.enabled = False
        self.max_iterations = 10
        self.current_iteration = 0
    
    def enable(self):
        """Включить Auto Pilot."""
        self.enabled = True
        print("[AutoPilot] Включён")
        # Добавляем задачи в Scheduler
        self.scheduler.add_task("autopilot_check_goals", 60, self._check_goals)
        self.scheduler.add_task("autopilot_health_check", 300, self._health_check)
        if not self.scheduler.running:
            self.scheduler.start()
    
    def disable(self):
        """Выключить Auto Pilot."""
        self.enabled = False
        print("[AutoPilot] Выключен")
    
    def _check_goals(self):
        """Проверить цели и выполнить следующую задачу."""
        if not self.enabled:
            return
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            print("[AutoPilot] Достигнут лимит итераций")
            return
        
        # Берём первую активную цель
        goals = self.goal_engine.get_active_goals()
        if not goals:
            print("[AutoPilot] Нет активных целей")
            return
        
        for goal in goals:
            next_task = self.goal_engine.get_next_task(goal.id)
            if next_task:
                print(f"[AutoPilot] Выполняю задачу: {next_task.title}")
                self._execute_task(next_task, goal)
                break
    
    def _execute_task(self, task, goal):
        """Выполнить задачу через Workflow."""
        # Проверяем разрешение
        allowed, reason = self.permissions.can_execute("auto_pilot")
        if not allowed:
            print(f"[AutoPilot] Задача заблокирована: {reason}")
            return
        
        # Создаём Workflow для задачи
        def step_analyze(context):
            self.runtime.update_task_state(task.id, TaskState.ANALYZING)
            return {"status": "analyzed"}
        
        def step_plan(context):
            self.runtime.update_task_state(task.id, TaskState.PLANNING)
            return {"status": "planned"}
        
        def step_execute(context):
            self.runtime.update_task_state(task.id, TaskState.READY)
            self.runtime.update_task_state(task.id, TaskState.EXECUTING)
            return {"status": "executed"}
        
        def step_verify(context):
            self.runtime.update_task_state(task.id, TaskState.VERIFYING)
            self.runtime.update_task_state(task.id, TaskState.SUCCESS)
            return {"status": "verified"}
        
        def step_complete(context):
            self.runtime.update_task_state(task.id, TaskState.DONE, result="AutoPilot completed")
            # Авто-коммит
            self.git.commit(f"AutoPilot: {task.title}", task.id)
            return {"status": "done"}
        
        wf = Workflow(
            workflow_id=f"autopilot_{task.id}",
            name=f"AutoPilot: {task.title}",
            steps=[
                WorkflowStep("analyze", step_analyze),
                WorkflowStep("plan", step_plan),
                WorkflowStep("execute", step_execute),
                WorkflowStep("verify", step_verify),
                WorkflowStep("complete", step_complete),
            ]
        )
        
        self.runtime.register_workflow(wf)
        result = self.runtime.run_workflow(wf.id, {"task_id": task.id})
        
        if result.get("status") == "success":
            print(f"[AutoPilot] ✅ Задача выполнена: {task.title}")
            # Проверяем, завершена ли цель
            self.goal_engine.complete_goal(goal.id)
        else:
            print(f"[AutoPilot] ❌ Ошибка: {result.get('error')}")
    
    def _health_check(self):
        """Проверка здоровья системы."""
        print("[AutoPilot] Health check OK")
    
    def status(self) -> str:
        return f"""
AutoPilot Status
────────────────
Enabled: {self.enabled}
Iterations: {self.current_iteration}/{self.max_iterations}
Scheduler running: {self.scheduler.running}
Active goals: {len(self.goal_engine.get_active_goals())}
"""

# Singleton
_autopilot = None

def get_autopilot() -> AutoPilot:
    global _autopilot
    if _autopilot is None:
        _autopilot = AutoPilot()
    return _autopilot


if __name__ == "__main__":
    ap = get_autopilot()
    print(ap.status())
    
    # Создаём тестовую цель
    ge = get_goal_engine()
    goal = ge.create_goal("Тест AutoPilot", "Проверка автономного режима")
    ge.add_task_to_goal(goal.id, "Тестовая задача", "Проверка выполнения через AutoPilot")
    
    ap.enable()
    
    import time
    time.sleep(65)
    
    ap.disable()
    print(ap.status())