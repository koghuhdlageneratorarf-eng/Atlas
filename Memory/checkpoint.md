# ATLAS CHECKPOINT v1.0
**Date:** 2026-07-18
**Status:** Working MVP. Creates sites from templates with briefs.
**Hardware:** GTX 1650 Ti 4GB -> hybrid 3B/7B.

---

## 1. Architecture

```
Atlas/
├── Config/
│   └── llm_client.py          # Ollama client (hybrid 3B/7B)
├── Agents/
│   ├── executive.py           # Planner (7B)
│   ├── brief.py               # Brief generator (7B/3B)
│   └── developer.py           # Developer (3B) + Skills + AOS
├── Tools/
│   ├── skills_manager.py      # Git-clone skills
│   └── self_upgrade.py        # Code analysis + backups
├── Skills/
│   ├── modern_landing/        # Own Tailwind template
│   └── agency/                # Bootstrap template from GitHub
├── Projects/                  # Finished sites
├── Memory/
│   ├── backups/               # Backups (excluded from self-backups)
│   ├── upgrade_suggestions.json
│   └── Ideas/
│       └── roadmap.md         # Roadmap
└── main.py                    # Orchestrator
```

---

## 2. System Principles (critical)

| # | Rule |
|---|------|
| 1 | **Hybrid models:** Executive/Self-Upgrade -> 7B. Developer -> 3B. |
| 2 | **Don't reinvent the wheel:** Search for open-source solution first. |
| 3 | **Skills-first:** Developer works through templates, not from scratch. |
| 4 | **Auto-AOS:** Every created site gets scroll animations automatically. |
| 5 | **Brief:** Short request (<300 chars) -> generate brief. Long -> use as brief. |
| 6 | **Max 3 active tasks** at once. |

---

## 3. System Files

### Config/llm_client.py
```python
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:3b"

def ask_llm(messages, model=None):
    use_model = model or DEFAULT_MODEL
    response = requests.post(
        OLLAMA_URL,
        json={"model": use_model, "messages": messages, "stream": False},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

if __name__ == "__main__":
    print(ask_llm([{"role": "user", "content": "Privet"}]))
```

### Agents/executive.py
```python
"""Executive Agent - project planner (7B)"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

SYSTEM_PROMPT = """Ty - Executive Agent v sisteme Atlas.
Tvoya zadacha: poluchit zapros ot polzovatelya i sostavit plan vypolneniya.
U tebya est komanda specialistov:
- Developer - pishet kod (HTML, CSS, JS, Python)
- Designer - otvechaet za vizual, stil, animatsii
- QA - proveryaet rezultat, ishchet oshibki
- Researcher - ishchet informatsiyu, analiziruet

Otvet strogo v formate JSON:
{
  "task": "kratkoe opisanie zadachi",
  "agents_needed": ["Developer", "Designer"],
  "plan": ["shag 1", "shag 2", "shag 3"],
  "notes": "dopolnitelnye zamechaniya"
}

Ne pishi kod. Tolko plan."""


def run_executive(task: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Zadacha: {task}"}
    ]

    print("Executive dumayet (7B)...")
    answer = ask_llm(messages, model="qwen2.5-coder:7b")

    try:
        cleaned = answer.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        plan = json.loads(cleaned)
        print("\nPlan vypolneniya:")
        print(f"   Zadacha: {plan.get('task', '-')}")
        print(f"   Agenty: {', '.join(plan.get('agents_needed', []))}")
        print(f"   Plan:")
        for i, step in enumerate(plan.get('plan', []), 1):
            print(f"      {i}. {step}")
        if plan.get('notes'):
            print(f"   Zametki: {plan['notes']}")
        return plan

    except json.JSONDecodeError:
        print("\nModel vernula ne JSON. Syroy otvet:")
        print(answer)
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Ispolzovanie: python Agents/executive.py "sdelay sayt dlya mastera manikyura"')
        sys.exit(1)

    task = sys.argv[1]
    run_executive(task)
```

### Agents/brief.py
```python
"""
Brief Agent - sozdaet podrobnoe TZ dlya proekta.
Dva rezhima:
1. Korotkiy zapros (< 300 simvolov) -> generiruet TZ cherez 7B
2. Gotovoe TZ (> 300 simvolov) -> strukturiruet i sohranyaet kak est
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

SYSTEM_PROMPT = """Ty - Brief Agent v sisteme Atlas.
Tvoya zadacha: iz korotkogo zaprosa polzovatelya sostavit podrobnoe tekhnicheskoe zadanie (TZ) dlya veb-sayta.

TZ dolzhen soderzhat:
1. Nazvanie kompanii / proekta
2. Opisanie biznesa (2-3 predlozheniya)
3. Tselevaya auditoriya
4. Glavnye preimushchestva (3-5 punktov)
5. Uslugi / tovary s opisaniem i tsenami
6. Kontakty: telefon, email, adres, vremya raboty
7. Pozhelaniya po dizaynu (tsveta, stil, nastroenie)
8. Razdeli sayta (hero, uslugi, o nas, portfolio, kontakty, footer)

Otvet STROGO v formate Markdown (zagolovki, spiski).
Ne pishi kod. Tolko tekstovoe TZ."""


def structure_existing_tz(text: str):
    prompt = f"""Ty - Brief Agent. U tebya uzhe est gotovoe tekhnichaskoe zadanie ot klienta.
Pereformatiruy ego v chistyy Markdown s zagolovkami, ne menyaya soderzhanie.

ISKHODNYY TEKST:
{text}

PRAVILA:
- Sohrani VSE dannye (tseny, telefony, adresa, nazvaniya)
- Dobav zagolovki: ## Nazvanie, ## Opisanie, ## Uslugi, ## Kontakty, ## Dizayn
- Ne dobavlyay vymyshlennogo, chego ne bylo v iskhodnom tekste
- Ne pishi kod, tolko tekst

Rezultat:"""

    messages = [{"role": "user", "content": prompt}]
    return ask_llm(messages, model="qwen2.5-coder:3b")


def run_brief(task: str, project_dir: str):
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    brief_file = project_path / "brief.md"

    if len(task) > 300:
        print(f"Brief Agent: obnaruzheno gotovoe TZ ({len(task)} simvolov)")
        print("   Strukturiruyu i sohranyayu...")
        tz = structure_existing_tz(task)
    else:
        print(f"Brief Agent: sostavlyayu TZ dlya '{task[:50]}...'")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Zapros: {task}"}
        ]
        tz = ask_llm(messages, model="qwen2.5-coder:7b")

    brief_file.write_text(tz, encoding="utf-8")
    print(f"   TZ sohraneno: {brief_file}")
    print(f"   Razmer: {len(tz)} simvolov")
    return str(brief_file)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Ispolzovanie: python Agents/brief.py "zadacha" ./put_k_proektu')
        sys.exit(1)

    task_arg = sys.argv[1]
    project_dir_arg = sys.argv[2]
    run_brief(task_arg, project_dir_arg)
```

### Agents/developer.py
```python
"""
Developer Agent - universal. Ispolzuet lyuboy skill iz papki Skills/.
Avtomaticheski dobavlyaet AOS.js dlya animatsiy.
"""

import sys
import re
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

SKILLS_DIR = Path(__file__).parent.parent / "Skills"
DEFAULT_SKILL = "modern_landing"

AOS_CSS = '<link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">'
AOS_JS = '<script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>'
AOS_INIT = '<script>AOS.init({duration:800,once:true});</script>'


def inject_aos(html_code: str):
    if "</head>" in html_code and AOS_CSS not in html_code:
        html_code = html_code.replace("</head>", f"    {AOS_CSS}\n</head>")

    if "</body>" in html_code:
        if AOS_JS not in html_code:
            html_code = html_code.replace("</body>", f"    {AOS_JS}\n    {AOS_INIT}\n</body>")
    elif "</html>" in html_code:
        html_code = html_code.replace("</html>", f"    {AOS_JS}\n    {AOS_INIT}\n</html>")

    return html_code


def load_skill(skill_name: str):
    skill_path = SKILLS_DIR / skill_name
    skill_json = skill_path / "skill.json"
    if not skill_json.exists():
        return None, None, None
    meta = json.loads(skill_json.read_text(encoding="utf-8"))
    entry_file = skill_path / meta.get("entry", "template.html")
    if not entry_file.exists():
        return None, None, None
    return entry_file.read_text(encoding="utf-8"), skill_path, entry_file


def copy_assets(skill_path: Path, entry_file: Path, project_path: Path):
    if not skill_path or not entry_file:
        return
    entry_dir = entry_file.parent
    src = entry_dir if entry_dir != skill_path else skill_path
    for item in src.rglob("*"):
        if item.is_file():
            if ".git" in str(item) or item.name == "skill.json":
                continue
            rel = item.relative_to(src)
            dest = project_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def fill_template(task: str, template: str, brief: str = None):
    context = f"ZAPROS POLZOVATELYA:\n{task}\n"
    if brief:
        context += f"\nTEKHNICHESKOE ZADANIE:\n{brief}\n"

    prompt = f"""Ty - professionalnyy veb-razrabotchik.
U tebya est gotovyy shablon HTML-sayta.
Zapolni ego realnym kontentom.

{context}

SHABLON (zameni tekst, ne trogay strukturu i klassy, ne menyay puti k CSS/JS):
{template}

PRAVILA:
1. Zameni tekst, zagolovki, opisaniya na russkom yazyke.
2. Sohrani vse klassy CSS, strukturu HTML, skripty.
3. Sohrani puti k CSS i JS faylam.
4. Dobav k glavnym sektsiyam (section, header, div s klassom container) atribut: data-aos=\"fade-up\"
5. Ispolzuy dannye iz TZ dlya tochnogo zapolneniya.
6. Ne ostavlyay placeholderov.
7. Verni TOLKO gotovyy HTML-kod, bez obyasneniy.

Gotovyy HTML:"""

    messages = [{"role": "user", "content": prompt}]
    print("   Zapolnenie shablona...")
    html_code = ask_llm(messages)

    html_code = html_code.strip()
    if html_code.startswith("```html"):
        html_code = html_code[7:]
    if html_code.startswith("```"):
        html_code = html_code[3:]
    if html_code.endswith("```"):
        html_code = html_code[:-3]
    html_code = html_code.strip()

    return html_code


def run_developer(task: str, project_dir: str, skill_name: str = None):
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    use_skill = skill_name or DEFAULT_SKILL
    print(f"Developer: skill '{use_skill}'")
    print(f"   Proekt: {project_path.absolute()}")

    brief = None
    brief_path = Path(project_dir) / "brief.md"
    if brief_path.exists():
        brief = brief_path.read_text(encoding="utf-8")
        print(f"   Brief nayden: {len(brief)} simvolov")

    template, skill_path, entry_file = load_skill(use_skill)
    if not template:
        print("   [!] Ne udalos zagruzit skill, generatsiya s nulya...")
        prompt = f"Sozday HTML-sayt dlya: {task}. Tolko kod."
        messages = [{"role": "user", "content": prompt}]
        html_code = ask_llm(messages)
    else:
        copy_assets(skill_path, entry_file, project_path)
        html_code = fill_template(task, template, brief)

    print("   Dobavlenie animatsiy AOS...")
    html_code = inject_aos(html_code)

    index_file = project_path / "index.html"
    index_file.write_text(html_code, encoding="utf-8")
    print(f"   Sohranen: {index_file}")

    print(f"\nGotovo! Otkroy fayl v brauzere:")
    print(f"   {index_file.absolute()}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Ispolzovanie: python Agents/developer.py "zadacha" ./put_k_proektu [skill_name]')
        sys.exit(1)

    task_arg = sys.argv[1]
    project_dir_arg = sys.argv[2]
    skill_arg = sys.argv[3] if len(sys.argv) > 3 else None
    run_developer(task_arg, project_dir_arg, skill_arg)
```

### Tools/skills_manager.py
```python
"""Skills Manager - ustanavlivaet navyki iz GitHub."""
import sys
import subprocess
import json
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "Skills"


def install_skill(repo_url: str, skill_name: str = None):
    if not skill_name:
        skill_name = repo_url.split("/")[-1].replace(".git", "")

    target = SKILLS_DIR / skill_name
    target.mkdir(parents=True, exist_ok=True)

    print(f"[*] Klonirovanie {repo_url} -> Skills/{skill_name} ...")
    result = subprocess.run(
        ["git", "clone", repo_url, str(target)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"[!] Oshibka klonirovaniya: {result.stderr}")
        return False

    skill_json = target / "skill.json"
    if not skill_json.exists():
        print("[*] Sozdan bazovyy skill.json")
        meta = {
            "name": skill_name,
            "version": "1.0.0",
            "description": f"Skill ustanovlen iz {repo_url}",
            "entry": "index.html",
            "dependencies": []
        }
        skill_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[+] Skill '{skill_name}' dobavlen!")
    return True


def list_skills():
    skills = []
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and (item / "skill.json").exists():
            skills.append(item.name)
    return skills


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ispolzovanie:")
        print("  python Tools/skills_manager.py add <repo_url> [name]")
        print("  python Tools/skills_manager.py list")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 3:
        install_skill(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "list":
        print("Ustanovlennye skills:", ", ".join(list_skills()) or "-")
    else:
        print("Neizvestnaya komanda")
```

### Tools/self_upgrade.py
```python
"""
Self-Upgrade - sistema samosovershenstvovaniya Atlas.
Chitaet svoy kod, analiziruet cherez LLM, delaet backup, sohranyaet predlozheniya.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "Memory"
BACKUP_DIR = MEMORY_DIR / "backups"
SUGGESTIONS_FILE = MEMORY_DIR / "upgrade_suggestions.json"

EXCLUDE_DIRS = {".git", "__pycache__", "Memory"}
EXCLUDE_FILES = {".pyc", ".log"}


def scan_files():
    files = []
    for root, dirs, filenames in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if any(fname.endswith(ext) for ext in EXCLUDE_FILES):
                continue
            fpath = Path(root) / fname
            rel_path = fpath.relative_to(BASE_DIR)
            try:
                content = fpath.read_text(encoding="utf-8")
                files.append({"path": str(rel_path), "content": content})
            except Exception:
                pass
    return files


def make_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)

    for item in BASE_DIR.iterdir():
        if item.name in EXCLUDE_DIRS:
            continue
        dest = backup_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"), dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    print(f"Backup sozdan: {backup_path}")
    return str(backup_path)


def analyze_system(files):
    summary = []
    for f in files:
        lines = f["content"].count("\n")
        summary.append(f"- {f['path']} ({lines} strok)")

    summary_text = "\n".join(summary)

    prompt = f"""Ty - arkhitektor programmnoy sistemy Atlas.
Proanaliziruy etu sistemu i predlozhi KONKRETNYE uluchsheniya.

Struktura faylov:
{summary_text}

Trebuyu otvet STROGO v formate JSON:
{{
  "ocenka": "kratkaya ocenka sistemy (1-2 predlozheniya)",
  "problemy": ["problema 1", "problema 2"],
  "predlozheniya": [
    {{
      "chto": "opisanie izmeneniya",
      "zachem": "pochemu eto nuzhno",
      "fayl": "kakoy fayl izmenit",
      "prioritet": "high/medium/low"
    }}
  ]
}}

Ne pishi kod. Tolko analiz i predlozheniya."""

    messages = [{"role": "user", "content": prompt}]
    print("Analiz sistemy...")
    return ask_llm(messages)


def save_suggestion(raw_answer, backup_path):
    SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    suggestions = []
    if SUGGESTIONS_FILE.exists():
        suggestions = json.loads(SUGGESTIONS_FILE.read_text(encoding="utf-8"))

    entry = {
        "timestamp": datetime.now().isoformat(),
        "backup": backup_path,
        "raw_answer": raw_answer
    }

    try:
        cleaned = raw_answer.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        entry["parsed"] = parsed
        print(f"Ocenka: {parsed.get('ocenka', '-')}")
        print(f"Problem: {len(parsed.get('problemy', []))}")
        print(f"Predlozheniy: {len(parsed.get('predlozheniya', []))}")
    except json.JSONDecodeError:
        print("Model vernula ne JSON. Syroy otvet sohranen.")
        entry["parsed"] = None

    suggestions.append(entry)
    SUGGESTIONS_FILE.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Sokhraneno v: {SUGGESTIONS_FILE}")


def main():
    print("=" * 50)
    print("ATLAS SELF-UPGRADE")
    print("=" * 50)

    print("\nShag 1: Sozdanie backup...")
    backup = make_backup()

    print("\nShag 2: Skanirovanie faylov...")
    files = scan_files()
    print(f"Naydeno faylov: {len(files)}")

    print("\nShag 3: Analiz cherez LLM...")
    answer = analyze_system(files)

    print("\nShag 4: Sokhranenie predlozheniy...")
    save_suggestion(answer, backup)

    print("\n" + "=" * 50)
    print("GOTOV!")
    print("=" * 50)
    print(f"Backup: {backup}")
    print(f"Predlozheniya: {SUGGESTIONS_FILE}")


if __name__ == "__main__":
    main()
```

### main.py
```python
"""
Atlas - glavnyy orkestrator.
Zapuskaet tsikl: zadacha -> Executive -> Brief -> Developer -> rezultat
"""

import sys
import subprocess
from pathlib import Path


def run_subprocess(script_path, args):
    result = subprocess.run(
        [sys.executable, script_path] + args,
        capture_output=True, text=False
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    print(stdout)
    if stderr:
        print(stderr)
    return result.returncode == 0


def main():
    if len(sys.argv) < 2:
        print('Ispolzovanie: python main.py "sdelay sayt dlya mastera manikyura"')
        sys.exit(1)

    task = sys.argv[1]

    words = task.replace('"', '').replace("'", "").split()[:3]
    project_name = "_".join(words).lower() + "_project"
    project_dir = f"./Projects/{project_name}"

    print("=" * 50)
    print("ATLAS ZAPUSHCHEN")
    print("=" * 50)
    print(f"\nZadacha: {task}\n")

    print("--- Executive ---")
    if not run_subprocess("Agents/executive.py", [task]):
        print("\n❌ Executive ne spravilsya")
        sys.exit(1)

    print("\n--- Brief Agent ---")
    if not run_subprocess("Agents/brief.py", [task, project_dir]):
        print("\n❌ Brief Agent ne spravilsya")
        sys.exit(1)

    print("\n--- Developer ---")
    if not run_subprocess("Agents/developer.py", [task, project_dir]):
        print("\n❌ Developer ne spravilsya")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ ATLAS ZAVERSHIL RABOTU")
    print("=" * 50)
    print(f"\n📁 Proekt sohranen: {Path(project_dir).absolute()}")
    print(f"📋 TZ: {Path(project_dir) / 'brief.md'}")
    print(f"🌐 Sayt: {Path(project_dir) / 'index.html'}")


if __name__ == "__main__":
    main()
```

---

## 4. Roadmap (short)

**Active:**
- [x] Brief Agent (two modes)
- [x] Universal Developer with Skills
- [ ] QA Agent (Playwright + screenshots)
- [ ] Auto-Deploy to GitHub Pages

**Planned (after first sales):**
- Web dashboard
- Telegram bot for orders
- Browser Agent (competitor parsing)
- RAG memory (ChromaDB)
- MCP (Model Context Protocol)

---

## 5. Recovery Commands

```powershell
# 1. Check Ollama
ollama list

# 2. Full cycle
python main.py "Sdelay lending dlya kofeyni..."

# 3. Specific skill
python Agents/developer.py "Zadacha" ./Projects/name agency

# 4. Add skill from GitHub
python Tools/skills_manager.py add <url> <name>

# 5. Self-Upgrade
python Tools/self_upgrade.py
```

---

## 6. Context Limit Rule (for AI assistant)

> **When dialogue accumulates >15-20 messages** - must say:
> *"Approaching context limit. Recommend checkpoint: save current Memory/Ideas/roadmap.md + summary of changes, and I will continue fresh, loading this checkpoint."*

---

*Checkpoint created: 2026-07-18*
