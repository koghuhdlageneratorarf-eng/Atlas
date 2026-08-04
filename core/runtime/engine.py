"""
Runtime Engine — единственный координатор Atlas.

Согласно Конституции (Article IV):
- Runtime — единственный координатор системы
- Все компоненты взаимодействуют через Runtime
- Запрещены прямые вызовы агентов

Согласно Master Plan (Этап 3):
- Runtime знает только: Workflow, Event, State, Task, Agent, Tool
- Не знает CEO, Planner, Reviewer
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from pathlib import Path
import yaml

# ============================================================
# STATE
# ============================================================


class TaskState(Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    FIXING = "fixing"
    RETESTING = "retesting"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"
    REPLAN = "replan"
    DONE = "done"


# ============================================================
# TASK
# ============================================================


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    state: TaskState = TaskState.NEW
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data: dict = field(default_factory=dict)
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    result: str | None = None
    error: str | None = None


# ============================================================
# EVENT
# ============================================================


@dataclass
class Event:
    type: str
    payload: dict
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ============================================================
# WORKFLOW
# ============================================================


@dataclass
class WorkflowStep:
    name: str
    action: Callable[[dict], dict]
    on_success: str | None = None
    on_failure: str | None = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Workflow:
    id: str
    name: str
    steps: list[WorkflowStep]
    current_step: int = 0
    state: str = "idle"  # idle | running | success | failed
    context: dict = field(default_factory=dict)


# ============================================================
# STATE MACHINE
# ============================================================


class StateMachine:
    """Валидация переходов между состояниями задач."""

    TRANSITIONS = {
        TaskState.NEW: [TaskState.ANALYZING, TaskState.FAILED],
        TaskState.ANALYZING: [TaskState.PLANNING, TaskState.FAILED],
        TaskState.PLANNING: [TaskState.READY, TaskState.FAILED],
        TaskState.READY: [TaskState.EXECUTING, TaskState.FAILED],
        TaskState.EXECUTING: [
            TaskState.VERIFYING,
            TaskState.FAILED,
            TaskState.ROLLBACK,
        ],
        TaskState.VERIFYING: [TaskState.SUCCESS, TaskState.FIXING, TaskState.FAILED],
        TaskState.FIXING: [TaskState.RETESTING, TaskState.FAILED],
        TaskState.RETESTING: [TaskState.SUCCESS, TaskState.FIXING, TaskState.FAILED],
        TaskState.SUCCESS: [TaskState.DONE],
        TaskState.FAILED: [TaskState.ROLLBACK, TaskState.REPLAN],
        TaskState.ROLLBACK: [TaskState.REPLAN, TaskState.DONE],
        TaskState.REPLAN: [TaskState.PLANNING, TaskState.FAILED],
        TaskState.DONE: [],
    }

    @classmethod
    def can_transition(cls, from_state: TaskState, to_state: TaskState) -> bool:
        return to_state in cls.TRANSITIONS.get(from_state, [])

    @classmethod
    def validate(cls, from_state: TaskState, to_state: TaskState) -> None:
        if not cls.can_transition(from_state, to_state):
            allowed = [s.value for s in cls.TRANSITIONS.get(from_state, [])]
            raise ValueError(
                f"Недопустимый переход: {from_state.value} → {to_state.value}. "
                f"Разрешено: {allowed}"
            )


# ============================================================
# WORKFLOW
# ============================================================


class WorkflowStep:
    def __init__(
        self,
        name: str,
        action,
        on_success: str = None,
        on_failure: str = None,
        max_retries: int = 3,
    ):
        self.name = name
        self.action = action
        self.on_success = on_success
        self.on_failure = on_failure
        self.max_retries = max_retries
        self.retry_count = 0


class Workflow:
    def __init__(self, workflow_id: str, name: str, steps: list):
        self.id = workflow_id
        self.name = name
        self.steps = steps
        self.current_step = 0
        self.state = "idle"
        self.context = {}


# ============================================================
# RUNTIME ENGINE
# ============================================================


class RuntimeEngine:
    """Единственный координатор Atlas."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.workflows: dict[str, Workflow] = {}
        self.events: list[Event] = []
        self.agents: dict[str, Any] = {}
        self.tools: dict[str, Callable] = {}
        self._state_listeners: list[Callable] = []
        self.event_bus = EventBus()
        self._load_agents()

    def _load_agents(self):
        agents_dir = Path("agents")
        if not agents_dir.exists():
            return

        for yaml_file in agents_dir.rglob("agent.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                name = config.get("name") or yaml_file.parent.name
                self.register_agent(name, config)

            except Exception as e:
                print(f"[Runtime] Agent load error {yaml_file}: {e}")

    # ============================================================
    # TASK MANAGEMENT
    # ============================================================

    def create_task(
        self, title: str, description: str = "", parent_id: str = None
    ) -> Task:
        """Создать задачу."""
        task = Task(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            parent_id=parent_id,
            state=TaskState.NEW,
        )
        self.tasks[task.id] = task
        self._emit_event("task_created", {"task_id": task.id, "title": task.title})
        return task

    def update_task_state(
        self, task_id: str, state: TaskState, result: str = None, error: str = None
    ):
        task = self.tasks.get(task_id)
        if not task:
            return
        # Проверка перехода через StateMachine
        StateMachine.validate(task.state, state)
        task.state = state
        task.updated_at = datetime.now().isoformat()
        if result:
            task.result = result
        if error:
            task.error = error
        self._emit_event(
            "task_state_changed",
            {
                "task_id": task_id,
                "state": state.value,
                "result": result,
                "error": error,
            },
        )
        self._notify_listeners(task)

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def get_tasks_by_state(self, state: TaskState) -> list[Task]:
        return [t for t in self.tasks.values() if t.state == state]

    def register_workflow(self, workflow: Workflow):
        self.workflows[workflow.id] = workflow
        self._emit_event(
            "workflow_registered", {"workflow_id": workflow.id, "name": workflow.name}
        )

    def run_workflow(self, workflow_id: str, context: dict = None) -> dict:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": f"Workflow {workflow_id} not found"}
        if context:
            workflow.context.update(context)
        workflow.state = "running"
        self._emit_event("workflow_started", {"workflow_id": workflow_id})
        for step in workflow.steps:
            workflow.current_step += 1
            self._emit_event(
                "workflow_step",
                {
                    "workflow_id": workflow_id,
                    "step": step.name,
                    "step_index": workflow.current_step,
                },
            )
            try:
                result = step.action(workflow.context)
                workflow.context.update(result)
                if step.on_success:
                    workflow.context.update(
                        self._run_step(workflow, step.on_success, workflow.context)
                    )
            except Exception as e:
                workflow.state = "failed"
                self._emit_event(
                    "workflow_failed",
                    {"workflow_id": workflow_id, "step": step.name, "error": str(e)},
                )
                if step.on_failure:
                    workflow.context.update(
                        self._run_step(workflow, step.on_failure, workflow.context)
                    )
                return {"error": str(e), "step": step.name}
        workflow.state = "success"
        self._emit_event("workflow_completed", {"workflow_id": workflow_id})
        return {"status": "success", "context": workflow.context}

    def _run_step(self, workflow: Workflow, step_name: str, context: dict) -> dict:
        for step in workflow.steps:
            if step.name == step_name:
                return step.action(context)
        return context

    def add_task_dependency(self, parent_id: str, child_id: str) -> bool:
        parent = self.tasks.get(parent_id)
        child = self.tasks.get(child_id)
        if not parent or not child:
            return False
        if child_id not in parent.children:
            parent.children.append(child_id)
            child.parent_id = parent_id
            self._emit_event(
                "task_dependency_added", {"parent": parent_id, "child": child_id}
            )
            return True
        return False

    def get_task_children(self, task_id: str) -> list[Task]:
        task = self.tasks.get(task_id)
        if not task:
            return []
        return [self.tasks[cid] for cid in task.children if cid in self.tasks]

    def get_task_parent(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if not task or not task.parent_id:
            return None
        return self.tasks.get(task.parent_id)

    def can_execute_task(self, task_id: str) -> bool:
        """Проверить, можно ли выполнить задачу (все родители завершены)."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.parent_id:
            parent = self.tasks.get(task.parent_id)
            if parent and parent.state != TaskState.DONE:
                return False
        return True

    def get_ready_tasks(self) -> list[Task]:
        """Вернуть все задачи, готовые к выполнению."""
        return [
            t
            for t in self.tasks.values()
            if t.state == TaskState.NEW and self.can_execute_task(t.id)
        ]

    # ============================================================
    # WORKFLOW MANAGEMENT
    # ============================================================

    def register_workflow(self, workflow: Workflow):
        """Зарегистрировать workflow."""
        self.workflows[workflow.id] = workflow
        self._emit_event(
            "workflow_registered", {"workflow_id": workflow.id, "name": workflow.name}
        )

    def run_workflow(self, workflow_id: str, context: dict = None) -> dict:
        """Запустить workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": f"Workflow {workflow_id} not found"}

        if context:
            workflow.context.update(context)

        workflow.state = "running"
        self._emit_event("workflow_started", {"workflow_id": workflow_id})

        for step in workflow.steps:
            workflow.current_step += 1
            self._emit_event(
                "workflow_step",
                {
                    "workflow_id": workflow_id,
                    "step": step.name,
                    "step_index": workflow.current_step,
                },
            )

            try:
                result = step.action(workflow.context)
                workflow.context.update(result)
                if step.on_success:
                    workflow.context = self._run_step(
                        workflow, step.on_success, workflow.context
                    )
            except Exception as e:
                workflow.state = "failed"
                self._emit_event(
                    "workflow_failed",
                    {"workflow_id": workflow_id, "step": step.name, "error": str(e)},
                )
                if step.on_failure:
                    workflow.context = self._run_step(
                        workflow, step.on_failure, workflow.context
                    )
                return {"error": str(e), "step": step.name}

        workflow.state = "success"
        self._emit_event("workflow_completed", {"workflow_id": workflow_id})
        return {"status": "success", "context": workflow.context}

    def _run_step(self, workflow: Workflow, step_name: str, context: dict) -> dict:
        """Выполнить шаг по имени."""
        for step in workflow.steps:
            if step.name == step_name:
                return step.action(context)
        return context

    # ============================================================
    # AGENT MANAGEMENT
    # ============================================================

    def register_agent(self, name: str, agent: Any):
        """Зарегистрировать агента."""
        self.agents[name] = agent
        self._emit_event("agent_registered", {"name": name})

    def get_agent(self, name: str) -> Any | None:
        return self.agents.get(name)

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())

    # ============================================================
    # TOOL MANAGEMENT
    # ============================================================

    def register_tool(self, name: str, tool: Callable):
        """Зарегистрировать инструмент."""
        self.tools[name] = tool
        self._emit_event("tool_registered", {"name": name})

    def get_tool(self, name: str) -> Callable | None:
        return self.tools.get(name)

    def execute_tool(self, name: str, args: dict) -> dict:
        """Выполнить инструмент через Runtime."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool {name} not found"}
        try:
            result = tool(args)
            self._emit_event(
                "tool_executed", {"name": name, "result": str(result)[:100]}
            )
            return {"result": result}
        except Exception as e:
            self._emit_event("tool_failed", {"name": name, "error": str(e)})
            return {"error": str(e)}

    # ============================================================
    # EVENTS
    # ============================================================

    def _emit_event(self, event_type: str, payload: dict):
        """Внутренняя эмиссия события."""
        event = Event(type=event_type, payload=payload, source="runtime")
        self.events.append(event)
        self.event_bus.publish(event)

    def get_events(self, event_type: str = None, limit: int = 100) -> list[Event]:
        """Получить события."""
        events = self.events[-limit:]
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events

    # ============================================================
    # LISTENERS
    # ============================================================

    def add_listener(self, callback: Callable):
        """Добавить слушателя состояния."""
        self._state_listeners.append(callback)

    def _notify_listeners(self, task: Task):
        """Уведомить слушателей."""
        for cb in self._state_listeners:
            try:
                cb(task)
            except Exception:
                pass

    # ============================================================
    # STATUS
    # ============================================================

    def status(self) -> str:
        """Статус Runtime."""
        return f"""
Runtime Engine v2.0
───────────────────
Tasks: {len(self.tasks)}
Workflows: {len(self.workflows)}
Agents: {len(self.agents)}
Tools: {len(self.tools)}
Events: {len(self.events)}

Task states:
  NEW: {len(self.get_tasks_by_state(TaskState.NEW))}
  DONE: {len(self.get_tasks_by_state(TaskState.DONE))}
  FAILED: {len(self.get_tasks_by_state(TaskState.FAILED))}
"""


# ============================================================
# SINGLETON
# ============================================================

_runtime = None


def get_runtime() -> RuntimeEngine:
    global _runtime
    if _runtime is None:
        _runtime = RuntimeEngine()
    return _runtime


# ============================================================
# EVENT BUS
# ============================================================


class EventBus:
    """Шина событий — подписчики получают события от Runtime."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: Event):
        if event.type in self._subscribers:
            for cb in self._subscribers[event.type]:
                try:
                    cb(event)
                except Exception as e:
                    print(f"[EventBus] Ошибка в подписчике {event.type}: {e}")


# Добавить в RuntimeEngine:
# self.event_bus = EventBus()
# В _emit_event: self.event_bus.publish(event)

if __name__ == "__main__":
    runtime = get_runtime()
    print(runtime.status())

    # Тест: создать задачу
    task = runtime.create_task("Тестовая задача", "Проверка Runtime")
    runtime.update_task_state(task.id, TaskState.ANALYZING)
    runtime.update_task_state(task.id, TaskState.DONE, result="Успешно")

    print(runtime.status())
