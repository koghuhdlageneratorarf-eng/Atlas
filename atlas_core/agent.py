"""
atlas_core/agent.py — Atlas Code Agent
REPL + цикл Tool Use.
"""

import os
import sys
import json
import yaml
import re
import textwrap
from pathlib import Path
from typing import List, Dict, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def _load_env(filepath=None):
    if filepath is None:
        filepath = PROJECT_ROOT / "Config" / ".env"
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

_load_env()

from atlas_core.session import SessionManager
from atlas_core.context import ProjectContext
from atlas_core.tools import execute_tool, create_backup, run_command

try:
    from Config.llm_client import ask_llm
    HAS_LLM_CLIENT = True
except ImportError:
    HAS_LLM_CLIENT = False
    print("[WARN] Config.llm_client не найден")

# Load SYSTEM_PROMPT from file for easy editing
_SYSTEM_PROMPT_PATH = Path(__file__).parent / "SYSTEM_PROMPT_mini.md"
if _SYSTEM_PROMPT_PATH.exists():
    SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = """You are Atlas Code Agent. Use tools. Reply ONLY in JSON format.
FORMAT: {"thought":"...","tools":[{"name":"TOOL","args":{}}],"response":"..."}
"""

# ═══════════════════════════════════════════════════════════════
# LLM ВЫЗОВ
# ═══════════════════════════════════════════════════════════════
def _call_llm(messages: List[Dict], agent: str = "executive") -> Dict:
    """Вызвать LLM через Model Router. Без fallback на OpenRouter."""
    if HAS_LLM_CLIENT:
        try:
            response = ask_llm(
                messages=messages,
                agent=agent
            )
            return _parse_tool_response(response)
        except Exception as e:
            print(f"[WARN] Model Router ошибка: {e}")
            return {
                "thought": f"Ошибка LLM: {e}",
                "tools": [],
                "response": f"❌ Не удалось получить ответ от модели: {e}"
            }

    return {
        "thought": "LLM client не найден",
        "tools": [],
        "response": "❌ Config.llm_client не импортирован."
    }

def _call_openrouter(messages: List[Dict]) -> Dict:
    """Fallback: прямой запрос к OpenRouter API."""
    import requests

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        # Пробуем прочитать из .env
        env_path = PROJECT_ROOT / "Config" / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("OPENROUTER_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

    if not api_key:
        return {
            "thought": "Нет API ключа OpenRouter",
            "tools": [],
            "response": "❌ Не найден OPENROUTER_API_KEY. Добавь ключ в Config/.env"
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/koghuhdlageneratorarf-eng/Atlas",
        "X-Title": "Atlas Code Agent"
    }

    payload = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4000
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_tool_response(content)
    except Exception as e:
        return {
            "thought": f"Ошибка API: {str(e)}",
            "tools": [],
            "response": f"❌ Ошибка OpenRouter: {str(e)}"
        }


def _parse_tool_response(content: str) -> Dict:
    """Извлечь JSON из ответа LLM. Фиксит raw newlines внутри строк."""
    if not content or not content.strip():
        return {"thought": "", "tools": [], "response": ""}

    cleaned = re.sub(r"```json\s*", "", content)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = re.sub(r"<think[^>]*>.*?</think\s*>", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {"thought": "", "tools": [], "response": content}

    raw = match.group()

    # Фикс: эскейпим "голые" переносы строк внутри JSON-строк
    in_string = False
    escape = False
    fixed_chars = []
    for ch in raw:
        if escape:
            fixed_chars.append(ch)
            escape = False
            continue
        if ch == "\\":
            fixed_chars.append(ch)
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            fixed_chars.append(ch)
            continue
        if in_string and ch == "\n":
            fixed_chars.append("\\n")
            continue
        if in_string and ch == "\r":
            continue
        fixed_chars.append(ch)

    fixed = "".join(fixed_chars)

    try:
        parsed = json.loads(fixed)
        return {
            "thought": parsed.get("thought", ""),
            "tools": parsed.get("tools", []) or [],
            "response": parsed.get("response", "")
        }
    except json.JSONDecodeError:
        pass

    # Fallback: regex extraction
    thought = ""
    response = content
    tools = []
    t = re.search(r'"thought"\s*:\s*"([^"]*)"', raw)
    if t:
        thought = t.group(1).replace("\\n", "\n")
    r = re.search(r'"response"\s*:\s*"([^"]*)"', raw)
    if r:
        response = r.group(1).replace("\\n", "\n")
    tr = re.search(r'"tools"\s*:\s*(\[[^\]]*\])', raw, re.DOTALL)
    if tr:
        try:
            tools = json.loads(tr.group(1))
        except Exception:
            pass

    return {"thought": thought, "tools": tools, "response": response}


# ═══════════════════════════════════════════════════════════════
# AGENT LOOP
# ═══════════════════════════════════════════════════════════════
class AtlasCodeAgent:
    def __init__(self, session_name: str = "default"):
        self.session = SessionManager(session_name)
        self.context = ProjectContext()
        self.max_tool_iterations = 10

        # Добавляем system prompt если сессия новая
        history = self.session.get_history()
        if not history or history[0].get("role") != "system":
            self.session.add_message("system", SYSTEM_PROMPT)

    def _build_messages(self, user_input: str) -> List[Dict]:
        """Собрать сообщения для LLM: system + context + history + user."""
        messages = []

        # System prompt
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

        # Контекст проекта (сокращённый, чтобы не перегружать)
        project_ctx = self.context.get_context(max_tokens=2000)
        messages.append({
            "role": "system",
            "content": f"=== КОНТЕКСТ ПРОЕКТА ===\n{project_ctx[:3000]}\n=== КОНЕЦ КОНТЕКСТА ==="
        })

        # История (последние 10 сообщений)
        history = self.session.get_history(limit=20)
        for msg in history:
            if msg["role"] in ("user", "assistant", "tool"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Текущий запрос
        messages.append({"role": "user", "content": user_input})
        return messages

    def process(self, user_input: str) -> str:
        """Обработать запрос пользователя с циклом Tool Use."""
        self.session.add_message("user", user_input)

        iteration = 0
        final_response = ""

        while iteration < self.max_tool_iterations:
            iteration += 1

            # Строим сообщения
            messages = self._build_messages(user_input if iteration == 1 else "Продолжи на основе результатов инструментов.")

            # Запрос к LLM
            parsed = _call_llm(messages, agent="executive")

            thought = parsed.get("thought", "")
            tools = parsed.get("tools", [])
            response = parsed.get("response", "")

            # Сохраняем thought
                      # Thought не сохраняем в сессию — мешает LLM
            pass

            # Если нет инструментов — возвращаем ответ
            if not tools:
                final_response = response
                self.session.add_message("assistant", final_response)
                return final_response

            # Выполняем инструменты
            tool_results = []
            for tool in tools:
                name = tool.get("name", "")
                args = tool.get("args", {})
                print(f"  🔧 {name}({json.dumps(args, ensure_ascii=False)})...")

                result = execute_tool(name, args)
                tool_results.append(f"=== Результат {name} ===\n{result}")

                # Сохраняем результат как tool-сообщение
                self.session.add_message(
                    "tool",
                    f"Инструмент: {name}\nРезультат:\n{result[:2000]}"
                )

            # Если response есть и это последняя итерация — показываем
            if response and iteration == self.max_tool_iterations - 1:
                final_response = response

            # Продолжаем цикл — LLM увидит результаты в следующей итерации
            user_input = "\n".join(tool_results)

        if not final_response:
            final_response = "⚠️ Достигнут лимит итераций инструментов. Попробуй уточнить запрос."

        self.session.add_message("assistant", final_response)
        return final_response


# ═══════════════════════════════════════════════════════════════
# REPL
# ═══════════════════════════════════════════════════════════════
def print_banner():
    print(r"""
    ╔═══════════════════════════════════════════╗
    ║        ATLAS CODE AGENT v1.0              ║
    ║    Автономная система разработки          ║
    ╚═══════════════════════════════════════════╝
    Команды: /help, /context, /history, /clear,
             /backup, /diff, /status, /exit
    """)


def handle_command(cmd: str, agent: AtlasCodeAgent) -> Optional[str]:
    """Обработать слэш-команду. Возвращает None если нужно продолжить REPL."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command == "/help":
        print(textwrap.dedent("""
        Команды:
          /help              — эта справка
          /context           — показать дерево проекта
          /history           — история сообщений
          /clear             — очистить историю сессии
          /backup [name]     — создать бэкап
          /diff              — git diff
          /status            — git status
          /commit <msg>      — git add -A && git commit
          /sessions          — список сессий
          /switch <name>     — переключить сессию
          /exit, /quit       — выход
        """))

    elif command == "/context":
        print(agent.context.get_tree())

    elif command == "/history":
        for msg in agent.session.get_history():
            role = msg["role"]
            content = msg["content"][:100]
            print(f"[{role}] {content}...")

    elif command == "/clear":
        agent.session.clear_history()
        print("✅ История очищена")

    elif command == "/backup":
        print(create_backup(arg or None))

    elif command == "/diff":
        print(run_command("git diff --stat"))

    elif command == "/status":
        print(run_command("git status"))

    elif command == "/commit":
        if not arg:
            print("❌ Укажи сообщение коммита: /commit обновление")
        else:
            print(run_command(f'git add -A && git commit -m "{arg}"'))

    elif command == "/sessions":
        for s in agent.session.list_sessions():
            print(f"  {s['id']}: {s['name']} (обновлён: {s['updated']})")

    elif command == "/switch":
        if not arg:
            print("❌ Укажи имя сессии: /switch my_session")
        else:
            agent.session = SessionManager(arg)
            print(f"✅ Переключено на сессию: {arg}")

    elif command in ("/exit", "/quit"):
        print("👋 До встречи!")
        return "EXIT"

    else:
        print(f"❌ Неизвестная команда: {command}. Используй /help")

    return None


def main():
    print_banner()

    session_name = "default"
    agent = AtlasCodeAgent(session_name)

    print(f"📁 Сессия: {session_name}")
    print(f"📂 Проект: {PROJECT_ROOT}")
    print("Введи задачу или /help для справки\n")

    while True:
        try:
            user_input = input("atlas> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 До встречи!")
            break

        if not user_input:
            continue

        # Слэш-команды
        if user_input.startswith("/"):
            result = handle_command(user_input, agent)
            if result == "EXIT":
                break
            continue

        # Основной цикл
        print("🤔 Думаю...")
        try:
            response = agent.process(user_input)
            print(f"\n{response}\n")
        except Exception as e:
            print(f"❌ Ошибка: {e}\n")


if __name__ == "__main__":
    main()
