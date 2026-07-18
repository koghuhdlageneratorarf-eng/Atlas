"""
Developer Agent — universal. Ispolzuet lyuboy skill iz papki Skills/.
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
    """Avtomaticheski vstavlyaet AOS v HTML."""
    # CSS v <head>
    if "</head>" in html_code and AOS_CSS not in html_code:
        html_code = html_code.replace("</head>", f"    {AOS_CSS}\n</head>")
    
    # JS i init pered </body>
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
    
    prompt = f"""Ty — professionalnyy veb-razrabotchik.
U tebya est gotovyy shablon HTML-sayta.
Zapolni ego realnym kontentom.

{context}

SHABLON (zameni tekst, ne trogay strukturu i klassy, ne menyay puti k CSS/JS):
{template}

PRAVILA:
1. Zameni tekst, zagolovki, opisaniya na russkom yazyke.
2. Sohrani vse klassy CSS, strukturu HTML, skripty.
3. Sohrani puti k CSS i JS faylam.
4. Dobav k glavnym sektsiyam (section, header, div s klassom container) atribut: data-aos="fade-up"
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

    # Avtomaticheski dobavlyaem AOS
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
