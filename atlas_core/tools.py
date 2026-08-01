"""
Atlas_Core/tools.py — Tool Execution Layer
Выполнение инструментов: файлы, git, команды, поиск.
"""
import os
import re
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent

def _safe_path(path_str: str) -> Path:
    """Преобразовать путь в безопасный относительный путь внутри проекта."""
    p = Path(path_str)
    if p.is_absolute():
        try:
            p.relative_to(PROJECT_ROOT)
        except ValueError:
            raise ValueError(f"Path {path_str} is outside project root")
    else:
        p = PROJECT_ROOT / p
    return p

WHITELISTED_PATHS = [
    PROJECT_ROOT / "Skills",
    PROJECT_ROOT / "Agent_Runtime",
    PROJECT_ROOT / "UI",
    PROJECT_ROOT / "Tool_Layer",
    PROJECT_ROOT / "Knowledge_Layer",
    PROJECT_ROOT / "Memory_Layer",
    PROJECT_ROOT / "Prompts",
]
PROTECTED_PATHS = [
    PROJECT_ROOT / "Config" / ".env",
    PROJECT_ROOT / "Config" / "models.yaml",
    PROJECT_ROOT / "Atlas_Core" / "session.py",
    PROJECT_ROOT / "Atlas_Core" / "context.py",
    PROJECT_ROOT / "Atlas_Core" / "tools.py",
    PROJECT_ROOT / "Model_Router" / "llm_client.py",
    PROJECT_ROOT / "Storage" / "memory_events.db",
]

def _is_protected(path: Path) -> bool:
    for protected in PROTECTED_PATHS:
        if path.resolve() == protected.resolve():
            return True
    return False

def _get_path_arg(args: Dict[str, Any]) -> str:
    """Fallback: LLM может использовать path, file_path или file."""
    return args.get("path") or args.get("file_path") or args.get("file", "")

def tool_list_directory(args: Dict[str, Any]) -> str:
    path = _safe_path(args.get("path", "."))
    if not path.exists():
        return f"❌ Path not found: {path}"
    lines = []
    for item in sorted(path.iterdir()):
        icon = "📁" if item.is_dir() else "📄"
        lines.append(f"{icon} {item.name}")
    return "\n".join(lines) if lines else "(empty)"

def tool_read_file(args: Dict[str, Any]) -> str:
    path = _safe_path(_get_path_arg(args))
    print(f"[WRITE DEBUG] path={path}")
    if not path.exists():
        return f"❌ File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        limit = args.get("limit", 200)
        if limit and len(content.splitlines()) > limit:
            lines = content.splitlines()[:limit]
            return "\n".join(lines) + f"\n\n... ({len(content.splitlines()) - limit} more lines)"
        return content
    except Exception as e:
        return f"❌ Error reading {path}: {e}"

def tool_write_file(args: Dict[str, Any]) -> str:
    path = _safe_path(_get_path_arg(args))
    if _is_protected(path):
        return f"🚫 Protected file: {path}. Use manual edit."
    content = args.get("content", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ Written {path} ({len(content)} chars)"

def tool_edit_file(args: Dict[str, Any]) -> str:
    path = _safe_path(_get_path_arg(args))
    if _is_protected(path):
        return f"🚫 Protected file: {path}. Use manual edit."
    if not path.exists():
        return f"❌ File not found: {path}"
    old = args.get("old_string", "")
    new = args.get("new_string", "")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        return f"❌ old_string not found in {path}"
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ Edited {path}"

def tool_run_command(args: Dict[str, Any]) -> str:
    cmd = args.get("command", "")
    cwd = args.get("cwd", str(PROJECT_ROOT))
    timeout = args.get("timeout", 30)
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout or ""
        err = result.stderr or ""
        if result.returncode != 0:
            return f"⚠️ Exit code {result.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout}s"
    except Exception as e:
        return f"❌ Error: {e}"

def tool_search_files(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    path = _safe_path(args.get("path", "."))
    results = []
    for root, _, files in os.walk(path):
        for fname in files:
            if fname.endswith(".pyc") or ".git" in root:
                continue
            fpath = Path(root) / fname
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if query in content:
                    lines = [i+1 for i, line in enumerate(content.splitlines()) if query in line]
                    results.append(f"{fpath.relative_to(PROJECT_ROOT)}: lines {lines}")
            except Exception:
                pass
    return "\n".join(results[:20]) if results else "(no matches)"

def tool_git_status(args: Dict[str, Any]) -> str:
    return tool_run_command({"command": "git status --short", "cwd": str(PROJECT_ROOT)})

def tool_git_commit(args: Dict[str, Any]) -> str:
    msg = args.get("message", "Atlas update")
    r1 = tool_run_command({"command": "git add -A", "cwd": str(PROJECT_ROOT)})
    r2 = tool_run_command({"command": f'git commit -m "{msg}"', "cwd": str(PROJECT_ROOT)})
    return f"{r1}\n{r2}"

def tool_backup_file(args: Dict[str, Any]) -> str:
    path = _safe_path(_get_path_arg(args))
    if not path.exists():
        return f"❌ File not found: {path}"
    backup_dir = PROJECT_ROOT / "Storage" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    backup_path = backup_dir / f"{path.name}.{ts}.bak"
    shutil.copy2(path, backup_path)
    return f"💾 Backup: {backup_path}"

def tool_rollback(args: Dict[str, Any]) -> str:
    """Откат к последнему бэкапу."""
    backup_dir = PROJECT_ROOT / "Storage" / "backups"
    if not backup_dir.exists():
        return "❌ Нет бэкапов"
    backups = sorted(backup_dir.glob("*.tar.gz"), key=os.path.getmtime, reverse=True)
    if not backups:
        return "❌ Нет бэкапов"
    latest = backups[0]
    import tarfile
    with tarfile.open(latest, "r:gz") as tar:
        tar.extractall(path=PROJECT_ROOT)
    return f"✅ Откат к {latest.name}"
    
TOOL_REGISTRY = {
    "list_directory": tool_list_directory,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "create_file": tool_write_file,
    "edit_file": tool_edit_file,
    "run_command": tool_run_command,
    "search_files": tool_search_files,
    "git_status": tool_git_status,
    "git_commit": tool_git_commit,
    "backup_file": tool_backup_file,
    "rollback": tool_rollback, 
}

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    if name not in TOOL_REGISTRY:
        return f"❌ Unknown tool: {name}. Available: {list(TOOL_REGISTRY.keys())}"
    try:
        return TOOL_REGISTRY[name](args)
    except Exception as e:
        return f"❌ Tool error ({name}): {e}"

def create_backup(name: Optional[str] = None) -> str:
    backup_dir = PROJECT_ROOT / "Storage" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    label = name or f"auto_{ts}"
    backup_path = backup_dir / label
    import tarfile
    archive = backup_path.with_suffix(".tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        for item in PROJECT_ROOT.iterdir():
            if item.name in (".git", "Storage", "__pycache__", ".venv", "venv"):
                continue
            tar.add(item, arcname=item.name)
    return f"💾 Full backup: {archive}"

def run_command(cmd: str, cwd: Optional[str] = None) -> str:
    return tool_run_command({"command": cmd, "cwd": cwd or str(PROJECT_ROOT)})

def tool_rollback(args: Dict[str, Any]) -> str:
    """Откат к последнему бэкапу."""
    backup_dir = PROJECT_ROOT / "Storage" / "backups"
    if not backup_dir.exists():
        return "❌ Нет бэкапов"
    backups = sorted(backup_dir.glob("*.tar.gz"), key=os.path.getmtime, reverse=True)
    if not backups:
        return "❌ Нет бэкапов"
    latest = backups[0]
    import tarfile
    with tarfile.open(latest, "r:gz") as tar:
        tar.extractall(path=PROJECT_ROOT)
    return f"✅ Откат к {latest.name}"