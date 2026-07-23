"""
atlas_core/context.py — Менеджер контекста проекта
Собирает дерево файлов, читает содержимое, формирует контекст для LLM.
Умное усечение: приоритет — skill.json, main.py, .py файлы агентов.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Set

# Исключаем из контекста
EXCLUDE_DIRS: Set[str] = {
    "__pycache__", ".git", "node_modules", "dist", "build",
    ".venv", "venv", ".pytest_cache", ".mypy_cache",
    "Memory", "backups", "graphify-out"
}
EXCLUDE_FILES: Set[str] = {
    ".env", ".gitignore", "package-lock.json", "yarn.lock",
    "*.pyc", "*.pyo", "*.log", "*.db", "*.sqlite", "*.sqlite3"
}

# Приоритетные файлы (идут первыми, не обрезаются)
HIGH_PRIORITY_PATTERNS = [
    "skill.json",
    "models.yaml",
    "main.py",
    "llm_client.py",
    "graphify_bridge.py",
    "memory_graph.py",
    "self_upgrade.py",
    "agent.py",
    "tools.py",
    "context.py",
    "session.py",
]


def _should_include(path: Path, root: Path) -> bool:
    """Проверить, нужно ли включать файл/папку в контекст."""
    rel = path.relative_to(root)
    parts = rel.parts

    # Проверка директорий
    for part in parts[:-1] if path.is_file() else parts:
        if part in EXCLUDE_DIRS:
            return False

    if path.is_dir():
        return path.name not in EXCLUDE_DIRS

    # Проверка файлов
    if path.name in EXCLUDE_FILES:
        return False
    for pat in ["*.pyc", "*.pyo", "*.log", "*.db"]:
        if path.match(pat):
            return False

    # Размер — макс 100KB на файл
    if path.stat().st_size > 100 * 1024:
        return False

    return True


def _priority_score(path: Path) -> int:
    """Чем меньше — тем выше приоритет."""
    name = path.name.lower()
    for i, pat in enumerate(HIGH_PRIORITY_PATTERNS):
        if pat.lower() in name:
            return i
    # .py выше остального
    if path.suffix == ".py":
        return 100
    if path.suffix in (".html", ".css", ".js", ".yaml", ".json"):
        return 200
    return 999


class ProjectContext:
    """Собирает и управляет контекстом проекта Atlas."""

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or Path(__file__).parent.parent
        self.file_cache: Dict[str, str] = {}
        self._build_cache()

    def _build_cache(self):
        """Проиндексировать все файлы проекта."""
        for path in sorted(self.root.rglob("*"), key=lambda p: str(p)):
            if not _should_include(path, self.root):
                continue
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rel = str(path.relative_to(self.root)).replace("\\", "/")
                    self.file_cache[rel] = content
                except Exception:
                    pass

    def get_tree(self) -> str:
        """Вернуть дерево файлов проекта."""
        lines = ["=== ДЕРЕВО ПРОЕКТА ATLAS ===", ""]

        def _tree(dir_path: Path, prefix: str = ""):
            try:
                entries = sorted(
                    [e for e in dir_path.iterdir() if _should_include(e, self.root)],
                    key=lambda e: (e.is_file(), e.name.lower())
                )
            except PermissionError:
                return

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    ext = "    " if is_last else "│   "
                    _tree(entry, prefix + ext)

        _tree(self.root)
        return "\n".join(lines)

    def read_file(self, rel_path: str) -> Optional[str]:
        """Прочитать файл по относительному пути."""
        rel_path = rel_path.replace("\\", "/")
        if rel_path in self.file_cache:
            return self.file_cache[rel_path]

        full = self.root / rel_path
        if full.exists() and full.is_file():
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def get_context(self, max_tokens: int = 8000) -> str:
        """Сформировать полный контекст проекта для LLM."""
        parts = []

        # 1. Дерево
        tree = self.get_tree()
        parts.append(tree)
        parts.append("")

        # 2. Приоритетные файлы
        sorted_files = sorted(
            self.file_cache.items(),
            key=lambda item: (_priority_score(self.root / item[0]), item[0])
        )

        # Оценка: ~4 символа = 1 токен
        current_len = len(tree)
        max_chars = max_tokens * 4

        for rel_path, content in sorted_files:
            if current_len >= max_chars:
                break

            header = f"\n=== FILE: {rel_path} ===\n"
            chunk = header + content

            if current_len + len(chunk) > max_chars:
                # Обрезаем с конца, но сохраняем структуру для .py
                remaining = max_chars - current_len - len(header)
                if remaining > 500:
                    if rel_path.endswith(".py"):
                        # Для Python — обрезаем тело функций, сохраняем сигнатуры
                        lines = content.split("\n")
                        truncated = []
                        total = 0
                        for line in lines:
                            if total + len(line) > remaining:
                                truncated.append("# ... (truncated)")
                                break
                            truncated.append(line)
                            total += len(line) + 1
                        chunk = header + "\n".join(truncated)
                    else:
                        chunk = header + content[:remaining] + "\n... (truncated)"
                else:
                    continue

            parts.append(chunk)
            current_len += len(chunk)

        return "\n".join(parts)

    def get_skills_catalog(self) -> List[Dict]:
        """Прочитать все skill.json из Skills/."""
        skills = []
        skills_dir = self.root / "Skills"
        if not skills_dir.exists():
            return skills

        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_json = skill_dir / "skill.json"
                if skill_json.exists():
                    try:
                        with open(skill_json, "r", encoding="utf-8-sig") as f:
                            data = json.load(f)
                        data["_path"] = str(skill_dir.relative_to(self.root)).replace("\\", "/")
                        skills.append(data)
                    except Exception:
                        pass
        return skills

    def search_in_files(self, query: str) -> List[Dict]:
        """Поиск строки по файлам проекта."""
        results = []
        q = query.lower()
        for rel_path, content in self.file_cache.items():
            if q in content.lower():
                lines = content.split("\n")
                matches = []
                for i, line in enumerate(lines, 1):
                    if q in line.lower():
                        matches.append({"line": i, "text": line.strip()})
                if matches:
                    results.append({
                        "file": rel_path,
                        "matches": matches[:5]  # макс 5 совпадений на файл
                    })
        return results


# --- CLI тест ---
if __name__ == "__main__":
    ctx = ProjectContext()
    print(ctx.get_tree()[:2000])
    print(f"\n--- Всего файлов в кэше: {len(ctx.file_cache)} ---")

    skills = ctx.get_skills_catalog()
    print(f"--- Skills найдено: {len(skills)} ---")
    for s in skills:
        print(f"  - {s.get('name', 'unknown')} ({s.get('_path', '')})")
