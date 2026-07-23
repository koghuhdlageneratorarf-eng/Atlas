"""Atlas Digital Studio — main orchestrator with Brain integration."""
import sys
import subprocess
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from pathlib import Path

# Инициализация Brain при старте
sys.path.insert(0, str(Path(__file__).parent / "Brain"))
try:
    from graphify_bridge import build_graph
    from memory_graph import log_episode
    BRAIN_READY = True
    build_graph()
except Exception as e:
    print(f"[!] Brain init error: {e}")
    BRAIN_READY = False

def run_subprocess(script_path, args, agent_name="unknown"):
    result = subprocess.run(
        [sys.executable, script_path] + args,
        capture_output=True, text=False
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    print(stdout)
    if stderr:
        print(stderr)
    
    if BRAIN_READY:
        log_episode(
            agent=agent_name,
            task=" ".join(args[:2]) if args else "unknown",
            action=f"run {Path(script_path).name}",
            result=stdout[:500],
            status="success" if result.returncode == 0 else "error"
        )
    
    return result.returncode == 0

def main():
    if len(sys.argv) < 2:
        print("Atlas Digital Studio with Brain")
        print('Usage: python main.py "task" [skill_name]')
        sys.exit(1)

    task = sys.argv[1]
    skill_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    task_lower = task.lower()
    if any(w in task_lower for w in ["brend", "brand", "logotip", "logo"]):
        product_type = "branding"
    elif any(w in task_lower for w in ["foto", "photo", "fotosessiya", "avatar"]):
        product_type = "media"
    elif any(w in task_lower for w in ["igra", "game", "play"]):
        product_type = "game"
    else:
        product_type = "web"

    words = task.replace('"', '').replace("'", "").split()[:3]
    project_name = "_".join(words).lower() + "_project"
    project_dir = f"./Projects/{project_name}"

    print("=" * 60)
    print("ATLAS DIGITAL STUDIO")
    if BRAIN_READY:
        print("[Brain] Graphify + Memory активны")
    print("=" * 60)
    print(f"\nTask: {task}")
    print(f"Type: {product_type}\n")

    if product_type == "branding":
        print("--- Branding Agent ---")
        run_subprocess("Agents/branding_agent.py", [task, project_dir], "branding")
    elif product_type == "media":
        print("--- Media Agent ---")
        run_subprocess("Agents/media_agent.py", [task, project_dir], "media")
    else:
        print("--- Executive ---")
        run_subprocess("Agents/executive.py", [task], "executive")
        
        print("\n--- Brief Agent ---")
        run_subprocess("Agents/brief.py", [task, project_dir], "brief")
        
        print("\n--- Image Generator ---")
        tasks_file = Path(project_dir) / "image_tasks.json"
        if tasks_file.exists():
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
            if tasks:
                run_subprocess("Agents/image_generator.py", [json.dumps(tasks), project_dir], "image_generator")
        
        print("\n--- Web Developer ---")
        skill = skill_name or "product_showcase"
        run_subprocess("Agents/developer.py", [task, project_dir, skill], "developer")

    print("\n" + "=" * 60)
    print("✅ ATLAS COMPLETE")
    print("=" * 60)
    print(f"\nProject: {Path(project_dir).absolute()}")

if __name__ == "__main__":
    main()
