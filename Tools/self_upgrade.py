"""
Self-Upgrade — sistema samosovershenstvovaniya Atlas.
Chitaet svoy kod, analiziruet cherez LLM, delaet backup, sohranyaet predlozheniya.
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "Memory"
BACKUP_DIR = MEMORY_DIR / "backups"
SUGGESTIONS_FILE = MEMORY_DIR / "upgrade_suggestions.json"

# ISKLYUCHAEM Memory iz backup, inache rekurziya
EXCLUDE_DIRS = {".git", "__pycache__", "Memory"}
EXCLUDE_FILES = {".pyc", ".log"}


def scan_files():
    """Skaniruet vse fayly proekta."""
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
                files.append({
                    "path": str(rel_path),
                    "content": content
                })
            except Exception:
                pass
    return files


def make_backup():
    """Sozdaet backup vsego proekta (bez Memory)."""
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
    """Otpravlyaet kod v LLM dlya analiza."""
    summary = []
    for f in files:
        lines = f["content"].count("\n")
        summary.append(f"- {f['path']} ({lines} strok)")
    
    summary_text = "\n".join(summary)
    
    prompt = f"""Ty — arkhitektor programmnoy sistemy Atlas.
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
    answer = ask_llm(messages)
    return answer


def save_suggestion(raw_answer, backup_path):
    """Sokhranyaet predlozhenie v Memory."""
    SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    suggestions = []
    if SUGGESTIONS_FILE.exists():
        suggestions = json.loads(SUGGESTIONS_FILE.read_text(encoding="utf-8"))
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "backup": backup_path,
        "raw_answer": raw_answer
    }
    
    # Pitaemsya izvlech JSON iz otveta
    try:
        cleaned = raw_answer.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        entry["parsed"] = parsed
        print(f"Ocenka: {parsed.get('ocenka', '—')}")
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
    
    # Shag 1: Backup
    print("\nShag 1: Sozdanie backup...")
    backup = make_backup()
    
    # Shag 2: Scan
    print("\nShag 2: Skanirovanie faylov...")
    files = scan_files()
    print(f"Naydeno faylov: {len(files)}")
    
    # Shag 3: Analiz
    print("\nShag 3: Analiz cherez LLM...")
    answer = analyze_system(files)
    
    # Shag 4: Save
    print("\nShag 4: Sokhranenie predlozheniy...")
    save_suggestion(answer, backup)
    
    print("\n" + "=" * 50)
    print("GOTOV!")
    print("=" * 50)
    print(f"Backup: {backup}")
    print(f"Predlozheniya: {SUGGESTIONS_FILE}")


if __name__ == "__main__":
    main()
