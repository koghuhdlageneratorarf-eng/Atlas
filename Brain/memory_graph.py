"""Memory Graph — эпизодическая память Atlas поверх Graphify."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "Memory" / "brain_memory.db"

def _init_db():
    """Инициализация SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            agent TEXT,
            task TEXT,
            action TEXT,
            result TEXT,
            files_changed TEXT,
            status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            file TEXT,
            description TEXT,
            fix TEXT,
            fixed_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            context TEXT,
            decision TEXT,
            reason TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_episode(agent: str, task: str, action: str, result: str, files_changed: list = None, status: str = "success"):
    """Записать событие."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO episodes (timestamp, agent, task, action, result, files_changed, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), agent, task, action, result, json.dumps(files_changed or []), status)
    )
    conn.commit()
    conn.close()

def log_bug(file: str, description: str, fix: str = ""):
    """Записать баг."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO bugs (timestamp, file, description, fix, fixed_at) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), file, description, fix, datetime.now().isoformat() if fix else None)
    )
    conn.commit()
    conn.close()

def log_decision(context: str, decision: str, reason: str):
    """Записать архитектурное решение."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO decisions (timestamp, context, decision, reason) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), context, decision, reason)
    )
    conn.commit()
    conn.close()

def get_recent_context(agent: str = None, limit: int = 5) -> str:
    """Получить недавнюю историю для контекста LLM."""
    if not DB_PATH.exists():
        return ""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    if agent:
        c.execute("SELECT timestamp, task, action, result, status FROM episodes WHERE agent = ? ORDER BY id DESC LIMIT ?", (agent, limit))
    else:
        c.execute("SELECT timestamp, task, action, result, status FROM episodes ORDER BY id DESC LIMIT ?", (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return ""
    
    lines = ["=== НЕДАВНЯЯ ИСТОРИЯ ==="]
    for ts, task, action, result, status in rows:
        lines.append(f"[{ts[:10]}] {action}: {result[:100]} ({status})")
    
    # Нерешённые баги
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT file, description FROM bugs WHERE fixed_at IS NULL LIMIT 3")
    bugs = c.fetchall()
    conn.close()
    
    if bugs:
        lines.append("\n=== АКТИВНЫЕ БАГИ ===")
        for file, desc in bugs:
            lines.append(f"[!] {file}: {desc[:100]}")
    
    return "\n".join(lines)

if __name__ == "__main__":
    # Тест
    log_episode("developer", "лендинг кофейни", "создание", "успех", ["Projects/coffee/index.html"])
    log_bug("Agents/developer.py", "BOM в skill.json", "utf-8-sig")
    print(get_recent_context("developer"))
