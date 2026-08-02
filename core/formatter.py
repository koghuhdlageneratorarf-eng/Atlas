"""
Automatic Formatting — форматирование Python-кода через black.

Согласно Roadmap v3.1 (P0+ — Safe Code Editing):
- Автоматическое форматирование файлов
- Проверка синтаксиса перед форматированием
"""

import subprocess
import sys
from pathlib import Path


class Formatter:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent

    def format_file(self, filepath: str, check_only: bool = False) -> dict:
        """Форматирует один файл через black."""
        full_path = self.root / filepath
        if not full_path.exists():
            return {"success": False, "message": f"Файл не найден: {filepath}"}
        if not full_path.suffix == ".py":
            return {"success": False, "message": f"Не Python-файл: {filepath}"}

        try:
            cmd = [sys.executable, "-m", "black"]
            if check_only:
                cmd.append("--check")
            cmd.append(str(full_path))
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if check_only:
                    return {
                        "success": True,
                        "message": f"Файл {filepath} уже отформатирован",
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Файл {filepath} отформатирован",
                    }
            else:
                if check_only:
                    return {
                        "success": False,
                        "message": f"Файл {filepath} требует форматирования",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Ошибка форматирования: {result.stderr}",
                    }
        except FileNotFoundError:
            return {
                "success": False,
                "message": "Black не установлен. Установите: pip install black",
            }

    def format_project(self, check_only: bool = False) -> dict:
        """Форматирует все Python-файлы проекта."""
        py_files = list(self.root.rglob("*.py"))
        if not py_files:
            return {"success": False, "message": "Python-файлы не найдены"}
        results = []
        for f in py_files:
            if "__pycache__" in str(f):
                continue
            rel = str(f.relative_to(self.root))
            res = self.format_file(rel, check_only)
            results.append(f"{rel}: {res.get('message', 'Ошибка')}")
        return {"success": True, "message": "\n".join(results)}


if __name__ == "__main__":
    f = Formatter()
    print("Formatter готов")
