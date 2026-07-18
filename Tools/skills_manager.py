import os
import json
import sys
import shutil
import subprocess
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "Skills"
REGISTRY_FILE = SKILLS_DIR / "registry.json"

def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {"skills": []}

def save_registry(registry):
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

def skill_exists(name):
    return (SKILLS_DIR / name).exists()

def add_skill(git_url, name=None):
    if not name:
        name = git_url.rstrip("/").split("/")[-1].replace(".git", "")
    
    target = SKILLS_DIR / name
    
    if skill_exists(name):
        print(f"[!] Skill '{name}' uzhe suschestvuet.")
        return False
    
    print(f"[*] Klonirovanie {git_url} -> Skills/{name} ...")
    try:
        subprocess.run(["git", "clone", git_url, str(target)], check=True)
    except subprocess.CalledProcessError:
        print(f"[!] Oshibka klonirovaniya.")
        return False
    except FileNotFoundError:
        print(f"[!] Git ne nayden.")
        return False
    
    skill_json = target / "skill.json"
    if not skill_json.exists():
        meta = {
            "name": name,
            "version": "1.0.0",
            "description": "Skill bez opisaniya",
            "entry": "main.py",
            "dependencies": []
        }
        skill_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[*] Sozdan bazovyy skill.json")
    else:
        meta = json.loads(skill_json.read_text(encoding="utf-8"))
        print(f"[*] Skill: {meta.get('description', 'bez opisaniya')}")
    
    registry = load_registry()
    registry["skills"].append({
        "name": name,
        "path": str(target.relative_to(SKILLS_DIR)),
        "source": git_url
    })
    save_registry(registry)
    
    print(f"[+] Skill '{name}' dobavlen!")
    return True

def remove_skill(name):
    target = SKILLS_DIR / name
    if not target.exists():
        print(f"[!] Skill '{name}' ne nayden.")
        return False
    
    shutil.rmtree(target)
    registry = load_registry()
    registry["skills"] = [s for s in registry["skills"] if s["name"] != name]
    save_registry(registry)
    print(f"[+] Skill '{name}' udalen.")
    return True

def list_skills():
    registry = load_registry()
    skills = registry.get("skills", [])
    if not skills:
        print("Net skillov.")
        return
    print(f"Skilly ({len(skills)}):")
    for s in skills:
        name = s["name"]
        skill_json = SKILLS_DIR / name / "skill.json"
        desc = "—"
        if skill_json.exists():
            meta = json.loads(skill_json.read_text(encoding="utf-8"))
            desc = meta.get("description", "—")
        print(f"  • {name}: {desc}")

def info_skill(name):
    target = SKILLS_DIR / name
    if not target.exists():
        print(f"[!] Skill '{name}' ne nayden.")
        return
    skill_json = target / "skill.json"
    if skill_json.exists():
        meta = json.loads(skill_json.read_text(encoding="utf-8"))
        print(f"Name: {meta.get('name')}")
        print(f"Version: {meta.get('version')}")
        print(f"Description: {meta.get('description')}")
        print(f"Entry: {meta.get('entry')}")
        print(f"Dependencies: {', '.join(meta.get('dependencies', []))}")

def install_dependencies(name):
    target = SKILLS_DIR / name
    skill_json = target / "skill.json"
    if not skill_json.exists():
        print(f"[!] skill.json ne nayden.")
        return
    meta = json.loads(skill_json.read_text(encoding="utf-8"))
    deps = meta.get("dependencies", [])
    if not deps:
        print("Zavisimostey net.")
        return
    print(f"[*] Ustanovka: {', '.join(deps)}")
    for dep in deps:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
            print(f"  [+] {dep}")
        except subprocess.CalledProcessError:
            print(f"  [!] Oshibka {dep}")

def main():
    if len(sys.argv) < 2:
        print("""Ispolzovanie:
  python Tools/skills_manager.py add <git_url> [name]
  python Tools/skills_manager.py remove <name>
  python Tools/skills_manager.py list
  python Tools/skills_manager.py info <name>
  python Tools/skills_manager.py install <name>""")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 3:
            print("Ukazhite git URL")
            sys.exit(1)
        add_skill(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "remove":
        remove_skill(sys.argv[2]) if len(sys.argv) > 2 else print("Ukazhite imya")
    elif cmd == "list":
        list_skills()
    elif cmd == "info":
        info_skill(sys.argv[2]) if len(sys.argv) > 2 else print("Ukazhite imya")
    elif cmd == "install":
        install_dependencies(sys.argv[2]) if len(sys.argv) > 2 else print("Ukazhite imya")
    else:
        print(f"Neizvestnaya komanda: {cmd}")

if __name__ == "__main__":
    main()
