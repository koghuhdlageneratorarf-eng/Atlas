"""
Atlas — glavnyy orkestrator.
Zapuskaet tsikl: zadacha → Executive → Brief → Developer → rezultat
"""

import sys
import subprocess
from pathlib import Path


def run_subprocess(script_path, args):
    """Zapuskaet Python-skript i vozvrashchaet vyvod."""
    result = subprocess.run(
        [sys.executable, script_path] + args,
        capture_output=True,
        text=False
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
    
    # Imya papki proekta
    words = task.replace('"', '').replace("'", "").split()[:3]
    project_name = "_".join(words).lower() + "_project"
    project_dir = f"./Projects/{project_name}"

    print("=" * 50)
    print("ATLAS ZAPUSHCHEN")
    print("=" * 50)
    print(f"\nZadacha: {task}\n")

    # Shag 1: Executive planiruet
    print("--- Executive ---")
    if not run_subprocess("Agents/executive.py", [task]):
        print("\n❌ Executive ne spravilsya")
        sys.exit(1)

    # Shag 2: Brief Agent sozdaet TZ
    print("\n--- Brief Agent ---")
    if not run_subprocess("Agents/brief.py", [task, project_dir]):
        print("\n❌ Brief Agent ne spravilsya")
        sys.exit(1)

    # Shag 3: Developer pishet kod
    print("\n--- Developer ---")
    if not run_subprocess("Agents/developer.py", [task, project_dir]):
        print("\n❌ Developer ne spravilsya")
        sys.exit(1)

    # Itog
    print("\n" + "=" * 50)
    print("✅ ATLAS ZAVERSHIL RABOTU")
    print("=" * 50)
    print(f"\n📁 Proekt sohranen: {Path(project_dir).absolute()}")
    print(f"📋 TZ: {Path(project_dir) / 'brief.md'}")
    print(f"🌐 Sayt: {Path(project_dir) / 'index.html'}")


if __name__ == "__main__":
    main()
