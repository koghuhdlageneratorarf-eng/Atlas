"""
atlas_core/tools.py — Инструменты для Atlas Code Agent
LLM вызывает эти функции через Tool Use. Каждая функция возвращает
строку-результат, который LLM видит и решает что делать дальше.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict

# Корень проекта — родитель atlas_core/
PROJECT_ROOT = Path(__file__).parent.parent


def _safe_path(rel_path: str) -> Path:
    """Преобразовать относительный путь в абсолютный внутри проекта."""
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    full = (PROJECT_ROOT / rel_path).resolve()
    # Защита: путь должен быть внутри проекта
    try:
        full.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError(f"Путь выходит за пределы проекта: {rel_path}")
    return full


# ═══════════════════════════════════════════════════════════════
# TOOL: read_file
# ═══════════════════════════════════════════════════════════════
def read_file(path: str, offset: int = 0, limit: int = 0) -> str:
    """Прочитать файл. offset — с какой строки, limit — сколько строк (0 = все)."""
    try:
        full = _safe_path(path)
        if not full.exists():
            return f"[ERROR] Файл не найден: {path}"
        if not full.is_file():
            return f"[ERROR] Это не файл: {path}"

        with open(full, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]

        content = "".join(lines)
        total_lines = len(lines)

        result = f"=== {path} (строки {offset+1}-{offset+total_lines}) ===\n"
        result += content
        if not content.endswith("\n"):
            result += "\n"
        return result
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: write_file
# ═══════════════════════════════════════════════════════════════
def write_file(path: str, content: str, append: bool = False) -> str:
    """Записать (или дописать) файл. Создаёт директории при необходимости."""
    try:
        full = _safe_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(full, mode, encoding="utf-8") as f:
            f.write(content)

        action = "дописан" if append else "создан/перезаписан"
        return f"[OK] Файл {action}: {path} ({len(content)} символов)"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: edit_file
# ═══════════════════════════════════════════════════════════════
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Заменить old_string на new_string в файле. Точное совпадение."""
    try:
        full = _safe_path(path)
        if not full.exists():
            return f"[ERROR] Файл не найден: {path}"

        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if old_string not in content:
            return f"[ERROR] Строка не найдена в файле. Возможно, нужно уточнить."

        new_content = content.replace(old_string, new_string, 1)

        with open(full, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"[OK] Файл отредактирован: {path}"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: list_directory
# ═══════════════════════════════════════════════════════════════
def list_directory(path: str = ".") -> str:
    """Показать содержимое директории."""
    try:
        full = _safe_path(path)
        if not full.exists():
            return f"[ERROR] Директория не найдена: {path}"
        if not full.is_dir():
            return f"[ERROR] Это не директория: {path}"

        entries = sorted(full.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        lines = [f"=== Содержимое: {path} ==="]
        for e in entries:
            icon = "📁" if e.is_dir() else "📄"
            size = f" ({e.stat().st_size} bytes)" if e.is_file() else ""
            lines.append(f"{icon} {e.name}{size}")
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: run_command
# ═══════════════════════════════════════════════════════════════
def run_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
    """Выполнить shell-команду. cwd — относительно PROJECT_ROOT."""
    try:
        work_dir = PROJECT_ROOT if cwd is None else _safe_path(cwd)

        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )

        output = []
        if result.stdout:
            output.append(f"[STDOUT]\n{result.stdout}")
        if result.stderr:
            output.append(f"[STDERR]\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"[EXIT CODE] {result.returncode}")

        return "\n".join(output) if output else "[OK] Команда выполнена (нет вывода)"
    except subprocess.TimeoutExpired:
        return f"[ERROR] Таймаут ({timeout} сек)"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: search_files
# ═══════════════════════════════════════════════════════════════
def search_files(query: str, path: str = ".", file_pattern: str = "*") -> str:
    """Поиск строки в файлах проекта."""
    try:
        full = _safe_path(path)
        if not full.exists():
            return f"[ERROR] Путь не найден: {path}"

        matches = []
        q = query.lower()

        for fpath in full.rglob(file_pattern):
            if fpath.is_file() and fpath.stat().st_size < 500 * 1024:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        if q in line.lower():
                            rel = str(fpath.relative_to(PROJECT_ROOT)).replace("\\", "/")
                            matches.append(f"  {rel}:{i}: {line.strip()}")
                            if len(matches) >= 20:
                                break
                except Exception:
                    pass
            if len(matches) >= 20:
                break

        if not matches:
            return f"[INFO] Совпадений не найдено для '{query}'"

        return f"=== Поиск: '{query}' ===\n" + "\n".join(matches)
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: git_diff
# ═══════════════════════════════════════════════════════════════
def git_diff() -> str:
    """Показать git diff — что изменилось с последнего коммита."""
    return run_command("git diff --stat && echo '---' && git diff", timeout=10)


def git_status() -> str:
    """Git status."""
    return run_command("git status", timeout=10)


def git_add_commit(message: str) -> str:
    """git add -A && git commit -m 'message'."""
    return run_command(f'git add -A && git commit -m "{message}"', timeout=10)


# ═══════════════════════════════════════════════════════════════
# TOOL: backup
# ═══════════════════════════════════════════════════════════════
def create_backup(name: Optional[str] = None) -> str:
    """Создать бэкап проекта в Memory/backups/."""
    try:
        backup_dir = PROJECT_ROOT / "Memory" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{name}" if name else ""
        dest = backup_dir / f"atlas_backup_{timestamp}{suffix}"

        # Копируем всё кроме Memory/, .git/, node_modules/
        ignore = shutil.ignore_patterns(
            "Memory", ".git", "node_modules", "__pycache__",
            "*.pyc", "*.pyo", ".venv", "venv"
        )
        shutil.copytree(PROJECT_ROOT, dest, ignore=ignore)

        return f"[OK] Бэкап создан: {dest.name}"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# TOOL: delete_file
# ═══════════════════════════════════════════════════════════════
def delete_file(path: str) -> str:
    """Удалить файл."""
    try:
        full = _safe_path(path)
        if not full.exists():
            return f"[ERROR] Файл не найден: {path}"
        full.unlink()
        return f"[OK] Файл удалён: {path}"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ═══════════════════════════════════════════════════════════════
# РЕЕСТР ИНСТРУМЕНТОВ
# ═══════════════════════════════════════════════════════════════
TOOLS_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_directory": list_directory,
    "run_command": run_command,
    "search_files": search_files,
    "git_diff": git_diff,
    "git_status": git_status,
    "git_add_commit": git_add_commit,
    "create_backup": create_backup,
    "delete_file": delete_file,
}


def execute_tool(name: str, args: Dict) -> str:
    """Выполнить инструмент по имени с аргументами."""
    if name not in TOOLS_REGISTRY:
        return f"[ERROR] Неизвестный инструмент: {name}. Доступные: {list(TOOLS_REGISTRY.keys())}"

    tool = TOOLS_REGISTRY[name]
    try:
        return tool(**args)
    except TypeError as e:
        return f"[ERROR] Неверные аргументы для {name}: {str(e)}"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# --- CLI тест ---
if __name__ == "__main__":
    print("=== Тест инструментов ===")
    print(list_directory("atlas_core"))
    print("\n---")
    print(search_files("class SessionManager", "atlas_core"))
