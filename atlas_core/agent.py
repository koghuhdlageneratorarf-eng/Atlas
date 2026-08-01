"""
Atlas_Core/agent.py — Atlas Code Agent v1.3
REPL + цикл Tool Use. Фиксы: dict-guard, JSON format, dedup tools.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import os
import sys
import json
import yaml
import re
import textwrap
from pathlib import Path
from typing import List, Dict, Optional
from core.runtime.engine import get_runtime
from atlas_core.tools import TOOL_REGISTRY

_runtime = None
def get_atlas_runtime():
    global _runtime
    if _runtime is None:
        _runtime = get_runtime()
        for name, func in TOOL_REGISTRY.items():
            _runtime.register_tool(name, func)
    return _runtime

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

# Load SYSTEM_PROMPT from file
_SYSTEM_PROMPT_PATH = PROJECT_ROOT / "Prompts" / "SYSTEM_PROMPT_mini.md"
if _SYSTEM_PROMPT_PATH.exists():
    SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = """You are Atlas Code Agent. Reply ONLY in JSON.
FORMAT: {"thought":"...","tools":[{"name":"TOOL","args":{}}],"response":"..."}
RULES:
- For chat/greetings/questions without files: tools=[]
- For file operations, commands, or search: use tools
- Available: list_directory, read_file, write_file, edit_file, run_command, search_files, git_status, git_commit, backup_file
EXAMPLES:
User: "Hello" -> {"thought":"Greeting user","tools":[],"response":"Hello! How can I help?"}
"""

# ═══════════════════════════════════════════════════════════════
# LLM ВЫЗОВ
# ═══════════════════════════════════════════════════════════════
def _call_llm(messages: List[Dict], agent: str = "executive") -> Dict:
    """Вызвать LLM через Model Router."""
    if HAS_LLM_CLIENT:
        try:
            response = ask_llm(
                messages=messages,
                agent=agent
            )
            print(f"[DEBUG] Raw: {repr(response[:300])}")
            parsed = _parse_tool_response(response)
            print(f"[DEBUG] Parsed: tools={len(parsed.get('tools',[]))} response={repr(parsed.get('response','')[:80])}")
            return parsed
        except Exception as e:
            print(f"[WARN] Model Router ошибка: {e}")
            import traceback
            traceback.print_exc()
            return {
                "thought": f"Ошибка LLM: {e}",
                "tools": [],
                "response": f"Не удалось получить ответ от модели: {e}"
            }

    return {
        "thought": "LLM client не найден",
        "tools": [],
        "response": "Config.llm_client не импортирован."
    }

def _parse_tool_response(content) -> Dict:
    """Извлечь JSON из ответа LLM. Фиксит raw newlines внутри строк."""
    if isinstance(content, dict):
        return {
            "thought": content.get("thought", ""),
            "tools": content.get("tools", []) or [],
            "response": content.get("response", "")
        }
    if content is None:
        return {"thought": "", "tools": [], "response": ""}
    if not isinstance(content, str) or not content.strip():
        return {"thought": "", "tools": [], "response": str(content) if content else ""}

    cleaned = re.sub(r"```json\s*", "", content)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = re.sub(r"<think[^>]*>.*?</think\s*>", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {"thought": "", "tools": [], "response": content}

    raw = match.group()

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
    def __init__(self, session_name: str = "default", agent_type: str = "executive"):
        self.session = SessionManager(session_name)
        self.context = ProjectContext()
        self.agent_type = agent_type
        self.max_tool_iterations = 10

        # Авто-очистка если system prompt изменился
        history = self.session.get_history()
        if history and history[0].get("role") == "system":
            old_prompt = history[0].get("content", "")
            if old_prompt != SYSTEM_PROMPT:
                print("[INFO] SYSTEM_PROMPT изменился, очищаю историю")
                self.session.clear_history()
                history = []

        # Добавляем system prompt если сессия пустая
        if not history or history[0].get("role") != "system":
            self.session.add_message("system", SYSTEM_PROMPT)

    def _build_messages(self, user_input: str, iteration: int = 1) -> List[Dict]:
        """Собрать сообщения для LLM: system + history + user (с контекстом)."""
        messages = []
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

        history = self.session.get_history(limit=20)
        for msg in history:
            if msg["role"] == "system":
                continue
            if msg["role"] in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"][:4000]
                })
            elif msg["role"] == "tool":
                messages.append({
                    "role": "user",
                    "content": f"[РЕЗУЛЬТАТ] {msg['content'][:4000]}"
                })

        if iteration == 1:
            project_ctx = self.context.get_context(max_tokens=2000)
            full_input = f"=== КОНТЕКСТ ПРОЕКТА ===\n{project_ctx[:3000]}\n=== КОНЕЦ КОНТЕКСТА ===\n\nЗАДАЧА: {user_input}"
            messages.append({"role": "user", "content": full_input})
        elif user_input.strip():
            messages.append({"role": "user", "content": user_input})
        return messages

    def process(self, user_input: str) -> str:
        """Обработать запрос пользователя с циклом Tool Use."""
        self.session.add_message("user", user_input)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # CEO по умолчанию для всех запросов (заменяем системный промпт)
        try:
            import yaml
            ceo_config = yaml.safe_load(open("agents/ceo/agent.yaml", encoding="utf-8"))
            ceo_prompt = ceo_config.get("prompt", "")
            messages[0]["content"] = ceo_prompt
        except Exception as e:
            print(f"[WARN] Не удалось загрузить CEO промпт: {e}")

        history = self.session.get_history(limit=20)
        for msg in history:
            if msg["role"] == "system":
                continue
            if msg["role"] == "tool":
                messages.append({
                    "role": "user",
                    "content": f"[РЕЗУЛЬТАТ] {msg['content'][:4000]}"
                })
            else:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"][:4000]
                })

        project_ctx = self.context.get_context(max_tokens=2000)
        full_input = (
            f"=== КОНТЕКСТ ПРОЕКТА ===\n{project_ctx[:3000]}\n"
            f"=== КОНЕЦ КОНТЕКСТА ===\n\nЗАДАЧА: {user_input}"
        )
        messages.append({"role": "user", "content": full_input})

        iteration = 0
        seen_tools = set()
        while iteration < self.max_tool_iterations:
            iteration += 1

            text = user_input.lower()
            if any(x in text for x in ["создай", "измени", "открой", "напиши", "код", "папка", "удали", "файл", "проект"]):
                agent_type = "developer"
            else:
                agent_type = "executive"

            # Авто-поиск в памяти
            try:
                from memories.indexer import MemoryIndexer
                idx = MemoryIndexer()
                memory = idx.remember(user_input)
                if memory and "Nothing found" not in memory:
                    messages.append({
                        "role": "system",
                        "content": f"=== ПАМЯТЬ ПРОЕКТА ===\n{memory[:3000]}\n=== КОНЕЦ ПАМЯТИ ===\nИспользуй эту информацию для ответа."
                    })
            except Exception:
                pass

            parsed = _call_llm(messages, agent=agent_type)
            print("=" * 60)
            print(parsed)
            print("=" * 60)

            thought = parsed.get("thought", "")
            tools = parsed.get("tools", [])
            response = parsed.get("response", "")

            tool_sig = json.dumps(tools, sort_keys=True, ensure_ascii=False)
            if tool_sig in seen_tools and tools:
                print(f"[WARN] Повторяющийся tool call, останавливаю")
                self.session.add_message("assistant", response or "Зацикливание")
                return response or "Зацикливание инструментов"
            seen_tools.add(tool_sig)

            if not tools:
                self.session.add_message("assistant", response)
                return response

            assistant_msg = json.dumps(
                {"thought": thought, "tools": tools, "response": response},
                ensure_ascii=False
            )
            messages.append({"role": "assistant", "content": assistant_msg})

            for tool in tools:
                name = tool.get("name", "")
                args = tool.get("args", {})
                print(f"  {name}({json.dumps(args, ensure_ascii=False)})...")

                runtime = get_atlas_runtime()
                result = runtime.execute_tool(name, args).get("result", "Ошибка")

                tool_result = f"[РЕЗУЛЬТАТ ИНСТРУМЕНТА]\n{name}\n{result}"

                messages.append({
                    "role": "user",
                    "content": tool_result + "\n\nТеперь дай только финальный ответ пользователю. Не вызывай инструменты повторно."
                })

        limit_msg = "Достигнут лимит итераций инструментов. Попробуй уточнить запрос."
        self.session.add_message("assistant", limit_msg)
        return limit_msg


# ═══════════════════════════════════════════════════════════════
# REPL
# ═══════════════════════════════════════════════════════════════
def print_banner():
    print(r"""
    ╔═══════════════════════════════════════════╗
    ║        ATLAS CODE AGENT v1.3              ║
    ║    Автономная система разработки          ║
    ╚═══════════════════════════════════════════╝
    Команды: /help, /context, /history, /clear,
             /backup, /diff, /status, /exit
    """)


def handle_command(cmd: str, agent: AtlasCodeAgent) -> Optional[str]:
    """Обработать слэш-команду."""
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
        print("История очищена")

    elif command == "/backup":
        print(create_backup(arg or None))

    elif command == "/rollback":
        from atlas_core.tools import tool_rollback
        print(tool_rollback({}))

    elif command == "/diff":
        print(run_command("git diff --stat"))

    elif command == "/status":
        print(run_command("git status"))

    elif command == "/commit":
        if not arg:
            print("Укажи сообщение коммита: /commit обновление")
        else:
            print(run_command(f'git add -A && git commit -m "{arg}"'))

    elif command == "/sessions":
        for s in agent.session.list_sessions():
            print(f"  {s['id']}: {s['name']} (обновлён: {s['updated_at']})")

    elif command == "/switch":
        if not arg:
            print("Укажи имя сессии: /switch my_session")
        else:
            agent.session = SessionManager(arg)
            print(f"Переключено на сессию: {arg}")

    elif command in ("/exit", "/quit"):
        print("До встречи!")
        return "EXIT"

    elif command == "/test":
        import subprocess
        result = subprocess.run(["python", "-m", "py_compile", "atlas_core/agent.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Синтаксис OK")
        else:
            print(f"❌ Ошибка:\n{result.stderr}")

    elif command == "/ceo":
        from core.symbol_resolver import SymbolResolver
        from core.roadmap_engine import RoadmapEngine
        from evolution.suggester import Suggester
        from Config.llm_client import ask_llm
        import yaml
        import re

        ceo_config = yaml.safe_load(open("agents/ceo/agent.yaml", encoding="utf-8"))
        prompt = ceo_config.get("prompt", "")
        user_msg = arg or "Оцени текущее состояние проекта и предложи улучшения"

        # Добавляем контекст из памяти
        from memories.indexer import MemoryIndexer
        idx = MemoryIndexer()
        memory = idx.remember(user_msg)
        memory_context = f"\n\nПамять проекта:\n{memory[:1500]}" if memory and "Nothing found" not in memory else ""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg + memory_context}
        ]

        print("[CEO] Думаю...")
        response = ask_llm(messages, agent="executive")
        print(f"\n[CEO] {response}")

        # Если CEO предлагает применить — автоматически запускаем план
        if "применить" in response.lower() or "apply" in response.lower():
            print("\n[CEO] Обнаружено предложение применить изменения.")
            print("Создаю план...")

            # Берём первую задачу из roadmap
            engine = RoadmapEngine()
            task, _ = engine.get_next_task()
            if task:
                title = task.get('title', 'Улучшение')
                suggester = Suggester()
                suggester.suggestions.append({
                    "title": f"Roadmap: {title}",
                    "description": f"Реализовать: {title} (из roadmap, этап {task.get('stage', 'Unknown')})",
                    "why": "Предложено CEO в диалоге",
                    "priority": "high",
                    "effort": "medium",
                    "timestamp": "now",
                    "status": "new",
                    "files": [],
                    "_roadmap_task_id": task.get("id")
                })
                suggester.save()
                print(f"✅ Задача добавлена в предложения. Примени: /apply")
            else:
                print("✅ Все задачи выполнены!")

    elif command == "/apply_approved":
        from evolution.suggester import Suggester
        from core.roadmap_engine import RoadmapEngine
        
        s = Suggester()
        if not s.suggestions:
            print("❌ Нет предложений для применения")
            return
        
        idx = len(s.suggestions)
        result = s.apply(idx)
        print(result)
        
        if "✅ Применено" in result:
            task_id = s.suggestions[idx - 1].get("_roadmap_task_id")
            if task_id:
                engine = RoadmapEngine()
                for task in engine.tasks:
                    if task.get("id") == task_id:
                        task["status"] = "done"
                        print(f"✅ Отмечено в roadmap: {task.get('title')}")
                        break

    elif command == "/remember":
        from memories.indexer import MemoryIndexer
        indexer = MemoryIndexer()
        query = arg or "Что я делал вчера?"
        print(f"🔍 Ищу: {query}")
        result = indexer.remember(query)
        print(f"\n{result}")
    
    elif command == "/suggest":
        from evolution.suggester import Suggester
        s = Suggester()
        print("[Evolution] Думаю...")
        s.analyze()
        print("\n".join([f"• {sug['title']}: {sug['description'][:100]}..." for sug in s.suggestions[-5:]]))

    elif command == "/suggestions":
        from evolution.suggester import Suggester
        print(Suggester().list_suggestions())

    elif command == "/apply":
        from evolution.suggester import Suggester
        from core.roadmap_engine import RoadmapEngine
        try:
            idx = int(arg.strip())
            s = Suggester()
            result = s.apply(idx)
            print(result)

            # Если успешно — отмечаем задачу в roadmap
            if "✅ Применено" in result:
                task_id = s.suggestions[idx - 1].get("_roadmap_task_id")
                if task_id:
                    engine = RoadmapEngine()
                    for task in engine.tasks:
                        if task.get("id") == task_id:
                            task["status"] = "done"
                            print(f"✅ Отмечено в roadmap: {task.get('title')}")
                            break
        except ValueError:
            print("❌ Укажи номер предложения: /apply 1")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    elif command == "/core":
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        print(engine.status())
        print("Агенты:", engine.list_agents())

    elif command == "/add_task":
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        task = {"name": arg or "Новая задача", "priority": "medium"}
        engine.add_task(task)
        print(f"✅ Задача добавлена: {task['name']} (ID: {task['id']})")
    
    elif command == "/agents":
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        print("Агенты:")
        for name in engine.list_agents():
            agent = engine.get_agent(name)
            role = agent.get("role", "Без роли")
            tools = ", ".join(agent.get("tools", [])[:3])
            print(f"  • {name} — {role}")
            print(f"    Инструменты: {tools}...")

    elif command == "/architect":
        from core.runtime.engine import RuntimeEngine
        from Config.llm_client import ask_llm
        import yaml
        
        engine = RuntimeEngine()
        agent_config = engine.get_agent("architect")
        if not agent_config:
            print("❌ Агент Architect не найден")
            return
        
        prompt = agent_config.get("prompt", "")
        user_msg = arg or "Оцени текущую архитектуру проекта Atlas"
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg}
        ]
        print("[Architect] Думаю...")
        response = ask_llm(messages, agent="executive")
        print(f"\n[Architect] {response}")

    elif command == "/reviewer":
        from core.runtime.engine import RuntimeEngine
        from Config.llm_client import ask_llm
        import yaml
        
        engine = RuntimeEngine()
        agent_config = engine.get_agent("reviewer")
        if not agent_config:
            print("❌ Агент Reviewer не найден")
            return
        
        prompt = agent_config.get("prompt", "")
        user_msg = arg or "Проверь последние изменения в коде"
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg}
        ]
        print("[Reviewer] Думаю...")
        response = ask_llm(messages, agent="executive")
        print(f"\n[Reviewer] {response}")

    elif command == "/add_suggestion":
        from evolution.suggester import Suggester
        from Config.llm_client import ask_llm
        import json
        import re
        
        if not arg:
            print("❌ Опиши улучшение: /add_suggestion Сделать Plugin System")
            return
        
        print(f"[Evolution] Понял: {arg}")
        print("Генерирую структуру предложения...")
        
        prompt = f"""
    Ты — Evolution Engine. Преврати запрос пользователя в структурированное предложение для улучшения Atlas.

    Запрос: {arg}

    Верни JSON:
    {{
    "title": "Краткое название",
    "description": "Что сделать",
    "why": "Зачем это нужно",
    "priority": "high/medium/low",
    "effort": "small/medium/large",
    "code": "полный код файла (если применимо)",
    "files": ["путь/к/файлу.py"]
    }}
    """
        messages = [{"role": "user", "content": prompt}]
        response = ask_llm(messages, agent="executive")
        
        try:
            clean = re.sub(r"```json\s*", "", response)
            clean = re.sub(r"```\s*", "", clean)
            data = json.loads(clean)
            
            s = Suggester()
            data["timestamp"] = "now"
            data["status"] = "new"
            s.suggestions.append(data)
            s.save()
            
            print(f"\n✅ Добавлено предложение: {data['title']}")
            print(f"   {data['description'][:100]}...")
            print("\nПримени: /apply <номер>")
            print("Список: /suggestions")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    elif command == "/roadmap":
        from core.roadmap_engine import RoadmapEngine
        engine = RoadmapEngine()
        print(engine.status())
        task, stage = engine.get_next_task()
        if task:
            title = task.get('title', task.get('description', 'Без названия'))
            task_id = task.get('id', 'unknown')
            stage_name = task.get('stage', 'Unknown')
            print(f"\nСледующая задача: [{task_id}] {title}")
            print(f"  Этап: {stage_name}")
            print(f"  Приоритет: {task.get('priority', 'P2')}")
        else:
            print("\n✅ Все задачи выполнены!")

    elif command == "/roadmap_next":
        from core.roadmap_engine import RoadmapEngine
        from evolution.suggester import Suggester
        engine = RoadmapEngine()
        task, stage = engine.get_next_task()
        if not task:
            print("✅ Все задачи выполнены!")
            return
        title = task.get('title', task.get('description', 'Без названия'))
        task_id = task.get('id', 'unknown')
        print(f"🚀 Выполняю: {title}")
        suggester = Suggester()
        suggester.suggestions.append({
            "title": f"Roadmap: {title}",  # <-- теперь видно, что это из roadmap
            "description": f"Реализовать: {title} (из roadmap, этап {task.get('stage', 'Unknown')})",
            "why": f"По плану roadmap (приоритет {task.get('priority', 'P2')})",
            "priority": "high",
            "effort": "medium",
            "timestamp": "now",
            "status": "new",
            "files": [],
            "_roadmap_task_id": task.get("id")  # <-- сохраняем ID задачи
        })
        suggester.save()
        print(f"✅ Задача добавлена в предложения. Примени: /apply")

    elif command == "/roadmap_list":
        from core.roadmap_engine import RoadmapEngine
        engine = RoadmapEngine()
        print(engine.list_tasks())

    elif command == "/symbols":
        from core.symbol_resolver import SymbolResolver
        resolver = SymbolResolver()
        filepath = arg or "atlas_core/agent.py"
        symbols = resolver.get_symbols(filepath)
        print(f"📦 Символы в {filepath}:")
        print(f"  Функции: {', '.join(symbols.get('functions', []))}")
        print(f"  Классы: {', '.join(symbols.get('classes', []))}")

    elif command == "/plan":
        from core.symbol_resolver import SymbolResolver
        from Config.llm_client import ask_llm
        import yaml
        
        # Загружаем конфиг Planner
        planner_config = yaml.safe_load(open("agents/planner/agent.yaml", encoding="utf-8"))
        prompt = planner_config.get("prompt", "")
        
        # Анализируем символы в указанном файле
        filepath = arg or "atlas_core/agent.py"
        resolver = SymbolResolver()
        symbols = resolver.get_symbols(filepath)
        
        # Формируем запрос
        user_msg = f"""
    Проанализируй файл {filepath} и составь план изменений.

    Текущие символы:
    - Функции: {', '.join(symbols.get('functions', []))}
    - Классы: {', '.join(symbols.get('classes', []))}

    Что нужно сделать: (опиши задачу)
    """
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg}
        ]
        
        print("[Planner] Анализирую...")
        response = ask_llm(messages, agent="executive")
        print(f"\n{response}")

    elif command == "/review":
        from core.symbol_resolver import SymbolResolver
        from Config.llm_client import ask_llm
        import yaml
        import subprocess
        
        # Загружаем конфиг Reviewer
        reviewer_config = yaml.safe_load(open("agents/reviewer/agent.yaml", encoding="utf-8"))
        prompt = reviewer_config.get("prompt", "")
        
        # Получаем git diff
        diff = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True)
        diff_output = diff.stdout or "Нет изменений"
        
        # Анализируем символы в изменённых файлах
        files = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True)
        file_list = files.stdout.strip().split("\n") if files.stdout else []
        
        symbols_info = ""
        resolver = SymbolResolver()
        for f in file_list[:5]:
            if f.endswith(".py"):
                sym = resolver.get_symbols(f)
                if sym:
                    symbols_info += f"\n{f}:\n  Функции: {', '.join(sym.get('functions', []))}\n  Классы: {', '.join(sym.get('classes', []))}"
        
        user_msg = f"""
    Проверь изменения в коде.

    Изменённые файлы:
    {chr(10).join(file_list[:10])}

    Git diff:
    {diff_output[:2000]}

    Символы в изменённых файлах:
    {symbols_info}
    """
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg}
        ]
        
        print("[Reviewer] Проверяю...")
        response = ask_llm(messages, agent="executive")
        print(f"\n{response}")

    else:
        print(f"Неизвестная команда: {command}. Используй /help")

    return None


def main():
    print_banner()

    session_name = "default"
    agent = AtlasCodeAgent(session_name, agent_type="developer")

    print(f"Сессия: {session_name}")
    print(f"Проект: {PROJECT_ROOT}")
    print("Введи задачу или /help для справки\n")

    while True:
        try:
            user_input = input("atlas> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо встречи!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            result = handle_command(user_input, agent)
            if result == "EXIT":
                break
            continue

        print("Думаю...")
        try:
            response = agent.process(user_input)
            print(f"\n{response}\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")


if __name__ == "__main__":
    main()