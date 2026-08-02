"""
Atlas_Core/agent.py — Atlas Code Agent v1.3
REPL + цикл Tool Use. Фиксы: dict-guard, JSON format, dedup tools.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from atlas_core.tools import TOOL_REGISTRY
from core.runtime.engine import get_runtime
_runtime = None
_server_pid = None

def get_atlas_runtime():
    """{
    "get_atlas_runtime": "Возвращает текущую версию Atlas Runtime, используемую в текущей сессии."
}"""
    global _runtime
    if _runtime is None:
        _runtime = get_runtime()
        for name, func in TOOL_REGISTRY.items():
            _runtime.register_tool(name, func)
    return _runtime
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def _load_env(filepath=None):
    if filepath is None:
        filepath = PROJECT_ROOT / 'Config' / '.env'
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
_load_env()
from atlas_core.context import ProjectContext
from atlas_core.session import SessionManager
from atlas_core.tools import create_backup, run_command
try:
    from Config.llm_client import ask_llm
    HAS_LLM_CLIENT = True
except ImportError:
    HAS_LLM_CLIENT = False
    print('[WARN] Config.llm_client не найден')
_SYSTEM_PROMPT_PATH = PROJECT_ROOT / 'Prompts' / 'SYSTEM_PROMPT_mini.md'
if _SYSTEM_PROMPT_PATH.exists():
    SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding='utf-8')
else:
    SYSTEM_PROMPT = 'You are Atlas Code Agent. Reply ONLY in JSON.\nFORMAT: {"thought":"...","tools":[{"name":"TOOL","args":{}}],"response":"..."}\nRULES:\n- For chat/greetings/questions without files: tools=[]\n- For file operations, commands, or search: use tools\n- Available: list_directory, read_file, write_file, edit_file, run_command, search_files, git_status, git_commit, backup_file\nEXAMPLES:\nUser: "Hello" -> {"thought":"Greeting user","tools":[],"response":"Hello! How can I help?"}\n'

def _call_llm(messages: list[dict], agent: str='executive') -> dict:
    """Вызвать LLM через Model Router."""
    if HAS_LLM_CLIENT:
        try:
            response = ask_llm(messages=messages, agent=agent)
            print(f'[DEBUG] Raw: {response[:300]!r}')
            parsed = _parse_tool_response(response)
            print(f"[DEBUG] Parsed: tools={len(parsed.get('tools', []))} response={parsed.get('response', '')[:80]!r}")
            return parsed
        except Exception as e:
            print(f'[WARN] Model Router ошибка: {e}')
            import traceback
            traceback.print_exc()
            return {'thought': f'Ошибка LLM: {e}', 'tools': [], 'response': f'Не удалось получить ответ от модели: {e}'}
    return {'thought': 'LLM client не найден', 'tools': [], 'response': 'Config.llm_client не импортирован.'}

def _parse_tool_response(content) -> dict:
    """Извлечь JSON из ответа LLM. Фиксит raw newlines внутри строк."""
    if isinstance(content, dict):
        return {'thought': content.get('thought', ''), 'tools': content.get('tools', []) or [], 'response': content.get('response', '')}
    if content is None:
        return {'thought': '', 'tools': [], 'response': ''}
    if not isinstance(content, str) or not content.strip():
        return {'thought': '', 'tools': [], 'response': str(content) if content else ''}
    cleaned = re.sub('```json\\s*', '', content)
    cleaned = re.sub('```\\s*', '', cleaned)
    cleaned = re.sub('<think[^>]*>.*?</think\\s*>', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()
    match = re.search('\\{[\\s\\S]*\\}', cleaned)
    if not match:
        return {'thought': '', 'tools': [], 'response': content}
    raw = match.group()
    in_string = False
    escape = False
    fixed_chars = []
    for ch in raw:
        if escape:
            fixed_chars.append(ch)
            escape = False
            continue
        if ch == '\\':
            fixed_chars.append(ch)
            escape = True
            continue
        if ch == '"' and (not escape):
            in_string = not in_string
            fixed_chars.append(ch)
            continue
        if in_string and ch == '\n':
            fixed_chars.append('\\n')
            continue
        if in_string and ch == '\r':
            continue
        fixed_chars.append(ch)
    fixed = ''.join(fixed_chars)
    try:
        parsed = json.loads(fixed)
        return {'thought': parsed.get('thought', ''), 'tools': parsed.get('tools', []) or [], 'response': parsed.get('response', '')}
    except json.JSONDecodeError:
        pass
    thought = ''
    response = content
    tools = []
    t = re.search('"thought"\\s*:\\s*"([^"]*)"', raw)
    if t:
        thought = t.group(1).replace('\\n', '\n')
    r = re.search('"response"\\s*:\\s*"([^"]*)"', raw)
    if r:
        response = r.group(1).replace('\\n', '\n')
    tr = re.search('"tools"\\s*:\\s*(\\[[^\\]]*\\])', raw, re.DOTALL)
    if tr:
        try:
            tools = json.loads(tr.group(1))
        except Exception:
            pass
    return {'thought': thought, 'tools': tools, 'response': response}

class AtlasCodeAgent:

    def __init__(self, session_name: str='default', agent_type: str='executive'):
        self.session = SessionManager(session_name)
        self.context = ProjectContext()
        self.agent_type = agent_type
        self.max_tool_iterations = 10
        history = self.session.get_history()
        if history and history[0].get('role') == 'system':
            old_prompt = history[0].get('content', '')
            if old_prompt != SYSTEM_PROMPT:
                print('[INFO] SYSTEM_PROMPT изменился, очищаю историю')
                self.session.clear_history()
                history = []
        if not history or history[0].get('role') != 'system':
            self.session.add_message('system', SYSTEM_PROMPT)

    def _build_messages(self, user_input: str, iteration: int=1) -> list[dict]:
        """Собрать сообщения для LLM: system + history + user (с контекстом)."""
        messages = []
        messages.append({'role': 'system', 'content': SYSTEM_PROMPT})
        history = self.session.get_history(limit=20)
        for msg in history:
            if msg['role'] == 'system':
                continue
            if msg['role'] in ('user', 'assistant'):
                messages.append({'role': msg['role'], 'content': msg['content'][:4000]})
            elif msg['role'] == 'tool':
                messages.append({'role': 'user', 'content': f"[РЕЗУЛЬТАТ] {msg['content'][:4000]}"})
        if iteration == 1:
            project_ctx = self.context.get_context(max_tokens=2000)
            full_input = f'=== КОНТЕКСТ ПРОЕКТА ===\n{project_ctx[:3000]}\n=== КОНЕЦ КОНТЕКСТА ===\n\nЗАДАЧА: {user_input}'
            messages.append({'role': 'user', 'content': full_input})
        elif user_input.strip():
            messages.append({'role': 'user', 'content': user_input})
        return messages

    def process(self, user_input: str) -> str:
        """Обработать запрос пользователя с циклом Tool Use."""
        self.session.add_message('user', user_input)
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        try:
            import yaml
            ceo_config = yaml.safe_load(open('agents/ceo/agent.yaml', encoding='utf-8'))
            ceo_prompt = ceo_config.get('prompt', '')
            messages[0]['content'] = ceo_prompt
        except Exception as e:
            print(f'[WARN] Не удалось загрузить CEO промпт: {e}')
        history = self.session.get_history(limit=20)
        for msg in history:
            if msg['role'] == 'system':
                continue
            if msg['role'] == 'tool':
                messages.append({'role': 'user', 'content': f"[РЕЗУЛЬТАТ] {msg['content'][:4000]}"})
            else:
                messages.append({'role': msg['role'], 'content': msg['content'][:4000]})
        project_ctx = self.context.get_context(max_tokens=2000)
        full_input = f'=== КОНТЕКСТ ПРОЕКТА ===\n{project_ctx[:3000]}\n=== КОНЕЦ КОНТЕКСТА ===\n\nЗАДАЧА: {user_input}'
        messages.append({'role': 'user', 'content': full_input})
        iteration = 0
        seen_tools = set()
        while iteration < self.max_tool_iterations:
            iteration += 1
            text = user_input.lower()
            if any((x in text for x in ['создай', 'измени', 'открой', 'напиши', 'код', 'папка', 'удали', 'файл', 'проект'])):
                agent_type = 'developer'
            else:
                agent_type = 'executive'
            try:
                from memories.indexer import MemoryIndexer
                idx = MemoryIndexer()
                memory = idx.remember(user_input)
                if memory and 'Nothing found' not in memory:
                    messages.append({'role': 'system', 'content': f'=== ПАМЯТЬ ПРОЕКТА ===\n{memory[:3000]}\n=== КОНЕЦ ПАМЯТИ ===\nИспользуй эту информацию для ответа.'})
            except Exception:
                pass
            parsed = _call_llm(messages, agent=agent_type)
            print('=' * 60)
            print(parsed)
            print('=' * 60)
            thought = parsed.get('thought', '')
            tools = parsed.get('tools', [])
            response = parsed.get('response', '')
            tool_sig = json.dumps(tools, sort_keys=True, ensure_ascii=False)
            if tool_sig in seen_tools and tools:
                print('[WARN] Повторяющийся tool call, останавливаю')
                self.session.add_message('assistant', response or 'Зацикливание')
                return response or 'Зацикливание инструментов'
            seen_tools.add(tool_sig)
            if not tools:
                self.session.add_message('assistant', response)
                return response
            assistant_msg = json.dumps({'thought': thought, 'tools': tools, 'response': response}, ensure_ascii=False)
            messages.append({'role': 'assistant', 'content': assistant_msg})
            for tool in tools:
                name = tool.get('name', '')
                args = tool.get('args', {})
                print(f'  {name}({json.dumps(args, ensure_ascii=False)})...')
                runtime = get_atlas_runtime()
                result = runtime.execute_tool(name, args).get('result', 'Ошибка')
                tool_result = f'[РЕЗУЛЬТАТ ИНСТРУМЕНТА]\n{name}\n{result}'
                messages.append({'role': 'user', 'content': tool_result + '\n\nТеперь дай только финальный ответ пользователю. Не вызывай инструменты повторно.'})
        limit_msg = 'Достигнут лимит итераций инструментов. Попробуй уточнить запрос.'
        self.session.add_message('assistant', limit_msg)
        return limit_msg

def print_welcome():
    print('\n    ╔═══════════════════════════════════════════╗\n    ║        ATLAS CODE AGENT v1.3              ║\n    ║    Автономная система разработки          ║\n    ╚═══════════════════════════════════════════╝\n    Команды: /help, /context, /history, /clear,\n             /backup, /diff, /status, /exit\n    ')

def handle_command(cmd: str, agent: AtlasCodeAgent) -> str | None:
    global _server_pid
    'Обработать слэш-команду.'
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ''
    if command == '/help':
        print(textwrap.dedent('\n        Команды:\n          /help              — эта справка\n          /context           — показать дерево проекта\n          /history           — история сообщений\n          /clear             — очистить историю сессии\n          /backup [name]     — создать бэкап\n          /diff              — git diff\n          /status            — git status\n          /commit <msg>      — git add -A && git commit\n          /sessions          — список сессий\n          /switch <name>     — переключить сессию\n          /exit, /quit       — выход\n        '))
    elif command == '/context':
        print(agent.context.get_tree())
    elif command == '/history':
        for msg in agent.session.get_history():
            role = msg['role']
            content = msg['content'][:100]
            print(f'[{role}] {content}...')
    elif command == '/clear':
        agent.session.clear_history()
        print('История очищена')
    elif command == '/backup':
        print(create_backup(arg or None))
    elif command == '/rollback':
        from atlas_core.tools import tool_rollback
        print(tool_rollback({}))
    elif command == '/diff':
        print(run_command('git diff --stat'))
    elif command == '/status':
        print(run_command('git status'))
    elif command == '/commit':
        if not arg:
            print('Укажи сообщение коммита: /commit обновление')
        else:
            print(run_command(f'git add -A && git commit -m "{arg}"'))
    elif command == '/sessions':
        for s in agent.session.list_sessions():
            print(f"  {s['id']}: {s['name']} (обновлён: {s['updated_at']})")
    elif command == '/switch':
        if not arg:
            print('Укажи имя сессии: /switch my_session')
        else:
            agent.session = SessionManager(arg)
            print(f'Переключено на сессию: {arg}')
    elif command in ('/exit', '/quit'):
        print('До встречи!')
        return 'EXIT'
    elif command == '/test':
        import subprocess
        result = subprocess.run(['python', '-m', 'py_compile', 'atlas_core/agent.py'], capture_output=True, text=True)
        if result.returncode == 0:
            print('✅ Синтаксис OK')
        else:
            print(f'❌ Ошибка:\n{result.stderr}')
    elif command == '/ceo':
        import re
        import yaml
        from Config.llm_client import ask_llm
        from core.roadmap_engine import RoadmapEngine
        from core.symbol_resolver import SymbolResolver
        from evolution.suggester import Suggester
        ceo_config = yaml.safe_load(open('agents/ceo/agent.yaml', encoding='utf-8'))
        prompt = ceo_config.get('prompt', '')
        user_msg = arg or 'Оцени текущее состояние проекта и предложи улучшения'
        from memories.indexer import MemoryIndexer
        idx = MemoryIndexer()
        memory = idx.remember(user_msg)
        memory_context = f'\n\nПамять проекта:\n{memory[:1500]}' if memory and 'Nothing found' not in memory else ''
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_msg + memory_context}]
        print('[CEO] Думаю...')
        response = ask_llm(messages, agent='executive')
        print(f'\n[CEO] {response}')
        if 'применить' in response.lower() or 'apply' in response.lower():
            print('\n[CEO] Обнаружено предложение применить изменения.')
            print('Создаю план...')
            engine = RoadmapEngine()
            task, _ = engine.get_next_task()
            if task:
                title = task.get('title', 'Улучшение')
                suggester = Suggester()
                suggester.suggestions.append({'title': f'Roadmap: {title}', 'description': f"Реализовать: {title} (из roadmap, этап {task.get('stage', 'Unknown')})", 'why': 'Предложено CEO в диалоге', 'priority': 'high', 'effort': 'medium', 'timestamp': 'now', 'status': 'new', 'files': [], '_roadmap_task_id': task.get('id')})
                suggester.save()
                print('✅ Задача добавлена в предложения. Примени: /apply')
            else:
                print('✅ Все задачи выполнены!')
    elif command == '/apply_approved':
        from core.roadmap_engine import RoadmapEngine
        from evolution.suggester import Suggester
        s = Suggester()
        if not s.suggestions:
            print('❌ Нет предложений для применения')
            return
        idx = len(s.suggestions)
        result = s.apply(idx)
        print(result)
        if '✅ Применено' in result:
            task_id = s.suggestions[idx - 1].get('_roadmap_task_id')
            if task_id:
                engine = RoadmapEngine()
                for task in engine.tasks:
                    if task.get('id') == task_id:
                        task['status'] = 'done'
                        print(f"✅ Отмечено в roadmap: {task.get('title')}")
                        break
    elif command == '/remember':
        from memories.indexer import MemoryIndexer
        indexer = MemoryIndexer()
        query = arg or 'Что я делал вчера?'
        print(f'🔍 Ищу: {query}')
        result = indexer.remember(query)
        print(f'\n{result}')
    elif command == '/suggest':
        from evolution.suggester import Suggester
        s = Suggester()
        print('[Evolution] Думаю...')
        s.analyze()
        print('\n'.join([f"• {sug['title']}: {sug['description'][:100]}..." for sug in s.suggestions[-5:]]))
    elif command == '/suggestions':
        from evolution.suggester import Suggester
        print(Suggester().list_suggestions())
    elif command == '/apply':
        from core.roadmap_engine import RoadmapEngine
        from evolution.suggester import Suggester
        try:
            idx = int(arg.strip())
            s = Suggester()
            result = s.apply(idx)
            print(result)
            if '✅ Применено' in result:
                task_id = s.suggestions[idx - 1].get('_roadmap_task_id')
                if task_id:
                    engine = RoadmapEngine()
                    for task in engine.tasks:
                        if task.get('id') == task_id:
                            task['status'] = 'done'
                            print(f"✅ Отмечено в roadmap: {task.get('title')}")
                            break
        except ValueError:
            print('❌ Укажи номер предложения: /apply 1')
        except Exception as e:
            print(f'❌ Ошибка: {e}')
    elif command == '/core':
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        print(engine.status())
        print('Агенты:', engine.list_agents())
    elif command == '/add_task':
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        task = {'name': arg or 'Новая задача', 'priority': 'medium'}
        engine.add_task(task)
        print(f"✅ Задача добавлена: {task['name']} (ID: {task['id']})")
    elif command == '/agents':
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        print('Агенты:')
        for name in engine.list_agents():
            agent = engine.get_agent(name)
            role = agent.get('role', 'Без роли')
            tools = ', '.join(agent.get('tools', [])[:3])
            print(f'  • {name} — {role}')
            print(f'    Инструменты: {tools}...')
    elif command == '/architect':
        import yaml
        from Config.llm_client import ask_llm
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        agent_config = engine.get_agent('architect')
        if not agent_config:
            print('❌ Агент Architect не найден')
            return
        prompt = agent_config.get('prompt', '')
        user_msg = arg or 'Оцени текущую архитектуру проекта Atlas'
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_msg}]
        print('[Architect] Думаю...')
        response = ask_llm(messages, agent='executive')
        print(f'\n[Architect] {response}')
    elif command == '/reviewer':
        import yaml
        from Config.llm_client import ask_llm
        from core.runtime.engine import RuntimeEngine
        engine = RuntimeEngine()
        agent_config = engine.get_agent('reviewer')
        if not agent_config:
            print('❌ Агент Reviewer не найден')
            return
        prompt = agent_config.get('prompt', '')
        user_msg = arg or 'Проверь последние изменения в коде'
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_msg}]
        print('[Reviewer] Думаю...')
        response = ask_llm(messages, agent='executive')
        print(f'\n[Reviewer] {response}')
    elif command == '/add_suggestion':
        import json
        import re
        from Config.llm_client import ask_llm
        from evolution.suggester import Suggester
        if not arg:
            print('❌ Опиши улучшение: /add_suggestion Сделать Plugin System')
            return
        print(f'[Evolution] Понял: {arg}')
        print('Генерирую структуру предложения...')
        prompt = f'\n    Ты — Evolution Engine. Преврати запрос пользователя в структурированное предложение для улучшения Atlas.\n\n    Запрос: {arg}\n\n    Верни JSON:\n    {{\n    "title": "Краткое название",\n    "description": "Что сделать",\n    "why": "Зачем это нужно",\n    "priority": "high/medium/low",\n    "effort": "small/medium/large",\n    "code": "полный код файла (если применимо)",\n    "files": ["путь/к/файлу.py"]\n    }}\n    '
        messages = [{'role': 'user', 'content': prompt}]
        response = ask_llm(messages, agent='executive')
        try:
            clean = re.sub('```json\\s*', '', response)
            clean = re.sub('```\\s*', '', clean)
            data = json.loads(clean)
            s = Suggester()
            data['timestamp'] = 'now'
            data['status'] = 'new'
            s.suggestions.append(data)
            s.save()
            print(f"\n✅ Добавлено предложение: {data['title']}")
            print(f"   {data['description'][:100]}...")
            print('\nПримени: /apply <номер>')
            print('Список: /suggestions')
        except Exception as e:
            print(f'❌ Ошибка: {e}')
    elif command == '/roadmap':
        from core.roadmap_engine import RoadmapEngine
        engine = RoadmapEngine()
        print(engine.status())
        task, stage = engine.get_next_task()
        if task:
            title = task.get('title', task.get('description', 'Без названия'))
            task_id = task.get('id', 'unknown')
            stage_name = task.get('stage', 'Unknown')
            print(f'\nСледующая задача: [{task_id}] {title}')
            print(f'  Этап: {stage_name}')
            print(f"  Приоритет: {task.get('priority', 'P2')}")
        else:
            print('\n✅ Все задачи выполнены!')
    elif command == '/roadmap_next':
        from core.roadmap_engine import RoadmapEngine
        from evolution.suggester import Suggester
        engine = RoadmapEngine()
        task, stage = engine.get_next_task()
        if not task:
            print('✅ Все задачи выполнены!')
            return
        title = task.get('title', task.get('description', 'Без названия'))
        task_id = task.get('id', 'unknown')
        print(f'🚀 Выполняю: {title}')
        suggester = Suggester()
        suggester.suggestions.append({'title': f'Roadmap: {title}', 'description': f"Реализовать: {title} (из roadmap, этап {task.get('stage', 'Unknown')})", 'why': f"По плану roadmap (приоритет {task.get('priority', 'P2')})", 'priority': 'high', 'effort': 'medium', 'timestamp': 'now', 'status': 'new', 'files': [], '_roadmap_task_id': task.get('id')})
        suggester.save()
        print('✅ Задача добавлена в предложения. Примени: /apply')
    elif command == '/roadmap_list':
        from core.roadmap_engine import RoadmapEngine
        engine = RoadmapEngine()
        print(engine.list_tasks())
    elif command == '/symbols':
        from core.symbol_resolver import SymbolResolver
        resolver = SymbolResolver()
        filepath = arg or 'atlas_core/agent.py'
        symbols = resolver.get_symbols(filepath)
        print(f'📦 Символы в {filepath}:')
        print(f"  Функции: {', '.join(symbols.get('functions', []))}")
        print(f"  Классы: {', '.join(symbols.get('classes', []))}")
    elif command == '/plan':
        import yaml
        from Config.llm_client import ask_llm
        from core.symbol_resolver import SymbolResolver
        planner_config = yaml.safe_load(open('agents/planner/agent.yaml', encoding='utf-8'))
        prompt = planner_config.get('prompt', '')
        filepath = arg or 'atlas_core/agent.py'
        resolver = SymbolResolver()
        symbols = resolver.get_symbols(filepath)
        user_msg = f"\n    Проанализируй файл {filepath} и составь план изменений.\n\n    Текущие символы:\n    - Функции: {', '.join(symbols.get('functions', []))}\n    - Классы: {', '.join(symbols.get('classes', []))}\n\n    Что нужно сделать: (опиши задачу)\n    "
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_msg}]
        print('[Planner] Анализирую...')
        response = ask_llm(messages, agent='executive')
        print(f'\n{response}')
    elif command == '/review':
        import subprocess
        import yaml
        from Config.llm_client import ask_llm
        from core.symbol_resolver import SymbolResolver
        reviewer_config = yaml.safe_load(open('agents/reviewer/agent.yaml', encoding='utf-8'))
        prompt = reviewer_config.get('prompt', '')
        diff = subprocess.run(['git', 'diff', '--stat'], capture_output=True, text=True)
        diff_output = diff.stdout or 'Нет изменений'
        files = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
        file_list = files.stdout.strip().split('\n') if files.stdout else []
        symbols_info = ''
        resolver = SymbolResolver()
        for f in file_list[:5]:
            if f.endswith('.py'):
                sym = resolver.get_symbols(f)
                if sym:
                    symbols_info += f"\n{f}:\n  Функции: {', '.join(sym.get('functions', []))}\n  Классы: {', '.join(sym.get('classes', []))}"
        user_msg = f'\n    Проверь изменения в коде.\n\n    Изменённые файлы:\n    {chr(10).join(file_list[:10])}\n\n    Git diff:\n    {diff_output[:2000]}\n\n    Символы в изменённых файлах:\n    {symbols_info}\n    '
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_msg}]
        print('[Reviewer] Проверяю...')
        response = ask_llm(messages, agent='executive')
        print(f'\n{response}')
    elif command == '/plugins':
        from core.plugin_loader import get_plugin_loader
        loader = get_plugin_loader()
        print(loader.list_plugins())
    elif command == '/apply_patch':
        from core.patch_engine import PatchEngine
        args = arg.split(maxsplit=1)
        if len(args) < 2:
            print('❌ Использование: /apply_patch <filepath> <diff>')
            return
        filepath, diff = (args[0], args[1])
        pe = PatchEngine()
        result = pe.apply_patch(filepath, diff, dry_run=False)
        print(result.get('message', 'Ошибка'))
    elif command == '/rename':
        from core.ast_editor import ASTEditor
        args = arg.split()
        if len(args) < 2:
            print('❌ Использование: /rename <old_name> <new_name>')
            return
        old_name, new_name = (args[0], args[1])
        editor = ASTEditor()
        if not editor.load('atlas_core/agent.py'):
            return
        if editor.rename_function(old_name, new_name):
            if editor.save():
                print(f'✅ Функция {old_name} → {new_name} переименована')
            else:
                print('❌ Ошибка сохранения')
        else:
            print(f'❌ Функция {old_name} не найдена')
    elif command == '/preview':
        from core.patch_engine import PatchEngine
        args = arg.split(maxsplit=1)
        if len(args) < 2:
            print('❌ Использование: /preview <filepath> <diff>')
            return
        filepath, diff = (args[0], args[1])
        pe = PatchEngine()
        result = pe.apply_patch(filepath, diff, dry_run=True)
        if result.get('success'):
            print('✅ Патч корректен. Можно применить через /apply_patch')
            print('\n--- DIFF ---')
            print(diff)
            print('--- END DIFF ---')
        else:
            print('❌ Патч не корректен:', result.get('message'))
    elif command == '/apply_multi':
        import json
        from core.patch_engine import PatchEngine
        pe = PatchEngine()
        try:
            data = json.loads(arg)
            if not isinstance(data, dict):
                print('❌ Ожидается JSON-объект: {"file1": "diff1", "file2": "diff2"}')
                return
            results = []
            for filepath, diff in data.items():
                result = pe.apply_patch(filepath, diff, dry_run=False)
                results.append(f"{filepath}: {result.get('message', 'Ошибка')}")
            print('\n'.join(results))
        except json.JSONDecodeError as e:
            print(f'❌ Ошибка парсинга JSON: {e}')
            print('Использование: /apply_multi {"file1": "diff1", "file2": "diff2"}')
    elif command == '/refactor':
        from core.refactor_engine import RefactorEngine
        ref = RefactorEngine()
        args = arg.split(maxsplit=3)
        if len(args) < 2:
            print('❌ Использование: /refactor <action> <params>')
            print('  Действия:')
            print('    rename_class <file> <old_name> <new_name>')
            print('    move_function <src> <dst> <func_name>')
            return
        action = args[0]
        if action == 'rename_class':
            if len(args) < 4:
                print('❌ Использование: /refactor rename_class <file> <old_name> <new_name>')
                return
            filepath, old_name, new_name = (args[1], args[2], args[3])
            result = ref.rename_class(filepath, old_name, new_name)
            print(result.get('message', 'Ошибка'))
        elif action == 'move_function':
            if len(args) < 4:
                print('❌ Использование: /refactor move_function <src> <dst> <func_name>')
                return
            src, dst, func_name = (args[1], args[2], args[3])
            result = ref.move_function(src, dst, func_name)
            print(result.get('message', 'Ошибка'))
        else:
            print(f'❌ Неизвестное действие: {action}')
    elif command == '/format':
        from core.formatter import Formatter
        f = Formatter()
        if arg:
            result = f.format_file(arg, check_only=False)
            print(result.get('message', 'Ошибка'))
        else:
            result = f.format_project(check_only=False)
            print(result.get('message', 'Ошибка'))
    elif command == '/explain':
        from core.explainer import Explainer
        e = Explainer()
        if arg:
            print('[Explainer] Анализирую изменения...')
            result = e.explain_diff(arg)
            print(result)
        else:
            result = e.explain_last()
            print(result)
    elif command == '/lint':
        from core.linter import Linter
        l = Linter()
        if arg:
            result = l.lint_file(arg, fix=False)
            print(result.get('message', 'Ошибка'))
        else:
            result = l.lint_project(fix=False)
            print(result.get('message', 'Ошибка'))
    elif command == '/typecheck':
        from core.type_checker import TypeChecker
        tc = TypeChecker()
        if arg:
            result = tc.check_file(arg)
            print(result.get('message', 'Ошибка'))
        else:
            result = tc.check_project()
            print(result.get('message', 'Ошибка'))
    elif command == '/test_run':
        import subprocess
        print('[Testing] Запуск pytest...')
        result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'], capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print('✅ Все тесты пройдены')
            print(result.stdout)
        else:
            print('❌ Тесты упали')
            print(result.stdout)
            print(result.stderr)
    elif command == '/run':
        import subprocess
        import time
        print('[Run] Запуск API-сервера...')
        try:
            proc = subprocess.Popen([sys.executable, 'api_openai.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            time.sleep(3)
            if proc.poll() is None:
                _server_pid = proc.pid
                print(f'✅ API-сервер запущен (PID: {_server_pid})')
                print('   Для остановки используй /stop')
            else:
                stdout, stderr = proc.communicate()
                print('❌ Сервер упал при запуске:')
                print(stderr or stdout)
        except Exception as e:
            print(f'❌ Ошибка запуска: {e}')
    elif command == '/stop':
        import subprocess
        if _server_pid is None:
            print('❌ Нет запущенного сервера')
            return
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(_server_pid)], capture_output=True, text=True)
            _server_pid = None
            print('✅ Сервер остановлен')
        except Exception as e:
            print(f'❌ Ошибка: {e}')
    elif command == '/logs':
        from pathlib import Path
        log_file = Path('Storage/logs/atlas.log')
        if not log_file.exists():
            print('❌ Лог-файл не найден. Запусти сервер через /run')
            return
        lines = log_file.read_text(encoding='utf-8').splitlines()
        tail = lines[-20:] if len(lines) > 20 else lines
        print('\n'.join(tail))
    elif command == '/debug':
        from core.self_debug import SelfDebugger
        if not arg:
            print('❌ Укажи traceback или путь к логу для анализа')
            print('Пример: /debug "Traceback (most recent call last):..."')
            print('Пример: /debug Storage/logs/atlas.log')
            return
        debugger = SelfDebugger()
        print('[SelfDebug] Запуск цикла самодиагностики...')
        result = debugger.debug_cycle(arg)
        if result.get('success'):
            print('\n✅ Ошибка исправлена!')
            print(f"   Попыток: {result.get('attempts')}")
            print(f"   Файл: {result.get('file')}")
            print(f"   Diff:\n{result.get('diff')}")
        else:
            print(f"\n❌ Ошибка не исправлена: {result.get('message')}")
    elif command == '/develop':
        from core.development_loop import DevelopmentLoop
        if not arg:
            print('❌ Укажи задачу для разработки')
            print('Пример: /develop добавить функцию логирования')
            return
        loop = DevelopmentLoop()
        result = loop.run(arg)
        print(result)
    else:
        from core.plugin_loader import get_plugin_loader
        loader = get_plugin_loader()
        result = loader.execute_command(command, arg)
        if result is not None:
            print(result)
            return
        print(f'Неизвестная команда: {command}. Используй /help')
    return None

def main():
    """Запускает основной цикл агента Atlas, обрабатывающий входные запросы и отвечая на них."""
    print_welcome()
    session_name = 'default'
    agent = AtlasCodeAgent(session_name, agent_type='developer')
    print(f'Сессия: {session_name}')
    print(f'Проект: {PROJECT_ROOT}')
    print('Введи задачу или /help для справки\n')
    while True:
        try:
            user_input = input('atlas> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nДо встречи!')
            break
        if not user_input:
            continue
        if user_input.startswith('/'):
            result = handle_command(user_input, agent)
            if result == 'EXIT':
                break
            continue
        print('Думаю...')
        try:
            response = agent.process(user_input)
            print(f'\n{response}\n')
        except Exception as e:
            print(f'Ошибка: {e}\n')
if __name__ == '__main__':
    main()