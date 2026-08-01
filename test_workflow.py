from core.runtime.engine import get_runtime, Workflow, WorkflowStep, TaskState

def step1(context):
    print("Step 1: Creating task")
    runtime = get_runtime()
    task = runtime.create_task("Test Workflow", "Automated task")
    context["task_id"] = task.id
    return {"task_id": task.id}

def step2(context):
    print(f"Step 2: Processing task {context.get('task_id')}")
    runtime = get_runtime()
    runtime.update_task_state(context["task_id"], TaskState.ANALYZING)
    return {"status": "analyzed"}

def step3(context):
    print(f"Step 3: Planning task {context.get('task_id')}")
    runtime = get_runtime()
    runtime.update_task_state(context["task_id"], TaskState.PLANNING)
    return {"status": "planned"}

def step4(context):
    print(f"Step 4: Executing task {context.get('task_id')}")
    runtime = get_runtime()
    runtime.update_task_state(context["task_id"], TaskState.READY)
    runtime.update_task_state(context["task_id"], TaskState.EXECUTING)
    return {"status": "executed"}

def step5(context):
    print(f"Step 5: Verifying task {context.get('task_id')}")
    runtime = get_runtime()
    runtime.update_task_state(context["task_id"], TaskState.VERIFYING)
    runtime.update_task_state(context["task_id"], TaskState.SUCCESS)
    return {"status": "verified"}

def step6(context):
    print(f"Step 6: Completing task {context.get('task_id')}")
    runtime = get_runtime()
    runtime.update_task_state(context["task_id"], TaskState.DONE, result="Workflow completed")
    return {"status": "done"}

# Обнови workflow
wf = Workflow(
    workflow_id="test_wf",
    name="Test Workflow",
    steps=[
        WorkflowStep("create", step1),
        WorkflowStep("analyze", step2),
        WorkflowStep("plan", step3),
        WorkflowStep("execute", step4),
        WorkflowStep("verify", step5),
        WorkflowStep("complete", step6)
    ]
)

# Создаём workflow
runtime = get_runtime()
wf = Workflow(
    workflow_id="test_wf",
    name="Test Workflow",
    steps=[
        WorkflowStep("create", step1),
        WorkflowStep("analyze", step2),
        WorkflowStep("complete", step3)
    ]
)
runtime.register_workflow(wf)

# Запускаем
result = runtime.run_workflow("test_wf")
print("\nResult:", result)