"""
Self Debugging System — автономное исправление ошибок.
"""

import sys
import re
import ast
import subprocess
import json
import difflib
from pathlib import Path
from typing import Dict, List, Optional
from atlas_core.tools import create_backup

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.patch_engine import PatchEngine
from core.linter import Linter
from core.type_checker import TypeChecker
from core.symbol_resolver import SymbolResolver
from Config.llm_client import ask_llm

class SelfDebugger:
    def __init__(self):
        self.max_attempts = 3
        self.attempts = 0
        self.patch_engine = PatchEngine()
        self.linter = Linter()
        self.type_checker = TypeChecker()
        self.resolver = SymbolResolver()
        self.last_error = None
        self.fixes_applied = []
        self._last_full_content = None
        self.history_file = PROJECT_ROOT / "Memory" / "fixes_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> List[Dict]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding='utf-8'))
            except:
                return []
        return []

    def _save_to_history(self, entry: Dict):
        history = self._load_history()
        history.append(entry)
        self.history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding='utf-8')

    def _validate_diff(self, diff: str, filepath: str) -> bool:
        """Проверяет, что diff корректен и содержит изменения."""
        if not diff or not diff.strip():
            return False
        if "--- " not in diff or "+++ " not in diff:
            return False
        if not any(line.startswith("+") or line.startswith("-") for line in diff.splitlines()):
            return False
        # Проверяем, что diff применим к файлу (dry-run)
        try:
            result = self.patch_engine.apply_patch(filepath, diff, dry_run=True)
            return result.get("success", False)
        except Exception:
            return False

    def _check_error_fixed(self, error_info: Dict) -> bool:
        filepath = error_info.get("file")
        if not filepath:
            return False
        file_path = Path(filepath)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        if not file_path.exists():
            return False

        # Проверяем синтаксис
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False

        # Проверяем, что имя больше не вызывает ошибку
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True
        except Exception:
            return False

    def analyze_traceback(self, traceback_text: str) -> Dict:
        lines = traceback_text.splitlines()
        error_info = {
            "file": None,
            "line": None,
            "function": None,
            "error_type": None,
            "message": None,
            "context": [],
            "raw": traceback_text
        }
        file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_text)
        if file_match:
            error_info["file"] = file_match.group(1)
            error_info["line"] = int(file_match.group(2))
        func_match = re.search(r'in (\w+)', traceback_text)
        if func_match:
            error_info["function"] = func_match.group(1)
        error_type_match = re.search(r'(\w+Error): (.+)', traceback_text)
        if error_type_match:
            error_info["error_type"] = error_type_match.group(1)
            error_info["message"] = error_type_match.group(2)
        if error_info["file"] and error_info["line"]:
            try:
                file_path = Path(error_info["file"])
                if not file_path.is_absolute():
                    file_path = PROJECT_ROOT / file_path
                if file_path.exists():
                    lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
                    start = max(0, error_info["line"] - 3)
                    end = min(len(lines), error_info["line"] + 3)
                    error_info["context"] = lines[start:end]
            except Exception:
                pass
        return error_info

    def analyze_logs(self, log_file: str = "Storage/logs/atlas.log", lines: int = 50) -> List[Dict]:
        log_path = PROJECT_ROOT / log_file
        if not log_path.exists():
            return []
        content = log_path.read_text(encoding='utf-8', errors='ignore')
        log_lines = content.splitlines()[-lines:]
        errors = []
        for line in log_lines:
            if "ERROR" in line or "Exception" in line:
                errors.append({"line": line, "raw": log_lines})
        return errors

    def _extract_docstring_text(self, raw: str, func_name: str = None) -> str:
        """Достаёт чистый текст docstring из ответа модели.

        Некоторые модели (особенно локальные, вроде qwen2.5-coder через
        Ollama, если системный промпт проекта учит их отвечать в JSON)
        оборачивают простой текст в JSON вместо того, чтобы просто вернуть
        текст docstring — иногда с ключами вроде "description", а иногда
        используя само имя функции как ключ: {"func_name": "текст"}.
        Эта функция пытается достать полезный текст из любой такой обёртки,
        а если это обычный текст — просто чистит кавычки/markdown по краям.
        """
        text = raw.strip()

        # Убираем возможные markdown-ограждения ```...```
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()

        # Если похоже на JSON — пробуем достать осмысленное поле
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    # 1) Известные "стандартные" ключи
                    for key in ("docstring", "description", "doc", "text"):
                        if isinstance(data.get(key), str) and data[key].strip():
                            return data[key].strip()
                    # 2) Ключ — это имя самой функции
                    if func_name and isinstance(data.get(func_name), str) and data[func_name].strip():
                        return data[func_name].strip()
                    # 3) Словарь с единственным строковым значением — берём его,
                    #    независимо от того, как называется ключ
                    string_values = [v.strip() for v in data.values() if isinstance(v, str) and v.strip()]
                    if len(string_values) == 1:
                        return string_values[0]
            except Exception:
                pass  # не распарсилось — используем как обычный текст ниже

        return text.strip('"').strip("'").strip("`")

    def generate_fix(self, error_info: Dict, previous_attempts: List[str] = None) -> Optional[str]:
        self._last_full_content = None
        filepath = error_info.get("file")
        line = error_info.get("line")
        error_type = error_info.get("error_type")
        message = error_info.get("message")

        if not filepath:
            return None

        # === AST FIX ===
        try:
            from core.ast_editor import ASTEditor
            editor = ASTEditor(str(PROJECT_ROOT))
            if editor.load(filepath):
                original_source = editor.source  # содержимое ДО любых правок

                if error_type == "NameError":
                    match = re.search(r"name '(\w+)' is not defined", message)
                    if match:
                        func_name = match.group(1)
                        if func_name not in editor.get_functions():
                            # Добавляем функцию
                            func_code = f"def {func_name}():\n    pass"
                            if editor.add_function(func_code):
                                new_content = ast.unparse(editor.tree)
                                if editor.save():
                                    diff = difflib.unified_diff(
                                        original_source.splitlines(keepends=True),
                                        new_content.splitlines(keepends=True),
                                        fromfile=filepath,
                                        tofile=filepath
                                    )
                                    diff_str = "".join(diff)
                                    if diff_str.strip():
                                        print(f"[SelfDebug] ✅ AST: добавлена функция {func_name}")
                                        self._last_full_content = new_content
                                        return diff_str

                # === DOCSTRING FIX (задачи вида "добавь docstring для функции X") ===
                if message and "docstring" in message.lower():
                    func_match = (
                        re.search(r"функци[а-я]*\W+(\w+)", message, re.IGNORECASE)
                        or re.search(r"function\W+(\w+)", message, re.IGNORECASE)
                    )
                    if func_match:
                        func_name = func_match.group(1)
                        if func_name in editor.get_functions():
                            try:
                                doc_prompt = (
                                    f"Напиши краткий docstring (1-3 строки, на русском языке) "
                                    f"для функции {func_name} из файла {filepath}. "
                                    f"Ответь ТОЛЬКО текстом docstring, без кавычек и markdown."
                                )
                                raw_doc = ask_llm(
                                    [{"role": "user", "content": doc_prompt}],
                                    agent="executive"
                                ).strip()
                                doc_text = self._extract_docstring_text(raw_doc, func_name=func_name)
                                if doc_text and editor.set_docstring(func_name, doc_text):
                                    new_content = ast.unparse(editor.tree)
                                    if editor.save():
                                        diff = difflib.unified_diff(
                                            original_source.splitlines(keepends=True),
                                            new_content.splitlines(keepends=True),
                                            fromfile=filepath,
                                            tofile=filepath
                                        )
                                        diff_str = "".join(diff)
                                        if diff_str.strip():
                                            print(f"[SelfDebug] ✅ AST: добавлен docstring для {func_name}")
                                            self._last_full_content = new_content
                                            return diff_str
                            except Exception as e:
                                print(f"[SelfDebug] Docstring попытка: {e}")
        except Exception as e:
            print(f"[SelfDebug] AST попытка: {e}")

        # === LLM FALLBACK ===
        try:
            file_path = Path(filepath)
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / file_path
            if not file_path.exists():
                return None
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[SelfDebug] Ошибка чтения: {e}")
            return None

        import json as json_module
        content_escaped = json_module.dumps(content, ensure_ascii=False)

        prompt = f'''
Исправь ошибку в Python коде.

Файл: {filepath}
Ошибка: {error_type} - {message}

Текущий код:
{content_escaped}

Задача: исправить ошибку и вернуть ПОЛНЫЙ ИСПРАВЛЕННЫЙ КОД ФАЙЛА целиком.

Правила:
1. НЕ используй try/except без необходимости.
2. Если функция не определена - добавь её.
3. Сохрани все существующие функции.
4. Используй 4 пробела для отступов.
5. Убедись, что после def, if, for, try, except и т.д. есть правильный отступ (4 пробела).
6. Код должен быть валидным Python.

Ответ ТОЛЬКО в формате JSON:
{{"fixed_code": "ПОЛНЫЙ исправленный код файла", "explanation": "что исправлено"}}
'''

        messages = [{"role": "user", "content": prompt}]

        try:
            response = ask_llm(messages, agent="executive")
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            print(f"[SelfDebug] RAW RESPONSE:\n{response[:500]}")
            print(f"[SelfDebug] CLEANED:\n{clean[:500]}")
            data = json_module.loads(clean, strict=False)
            fixed_code = data.get("fixed_code")
            explanation = data.get("explanation", "")

            if not fixed_code:
                return None

            if len(fixed_code) < len(content) * 0.3:
                print("[SelfDebug] Код слишком короткий")
                return None

            # Нормализуем отступы ДО проверки синтаксиса
            fixed_code = self._normalize_code(fixed_code)
            
            try:
                compile(fixed_code, filepath, 'exec')
            except SyntaxError as e:
                print(f"[SelfDebug] Синтаксическая ошибка: {e}")
                return None

            fixed_code = self._normalize_code(fixed_code)
            content_normalized = self._normalize_code(content)

            if fixed_code.strip() == content_normalized.strip():
                return None

            diff = difflib.unified_diff(
                content.splitlines(keepends=True),
                fixed_code.splitlines(keepends=True),
                fromfile=filepath,
                tofile=filepath
            )
            diff_str = "".join(diff)

            if not diff_str.strip():
                return None

            print(f"[SelfDebug] ✅ LLM diff ({len(diff_str)} символов)")
            print(f"[SelfDebug] Объяснение: {explanation[:100]}...")
            # Сохраняем полный текст файла — именно его запишем в apply_fix,
            # не полагаясь на построчный patch_engine (источник рассинхронизации).
            self._last_full_content = fixed_code
            return diff_str

        except Exception as e:
            print(f"[SelfDebug] LLM ошибка: {e}")
            return None

    def _normalize_code(self, code: str) -> str:
        lines = code.splitlines()
        # Удаляем пустые строки в начале и конце
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        # Находим минимальный отступ у непустых строк
        min_indent = None
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if min_indent is None or indent < min_indent:
                    min_indent = indent

        if min_indent is None or min_indent == 0:
            return "\n".join(lines)

        # Убираем общий отступ
        normalized = []
        for line in lines:
            if line.strip():
                normalized.append(line[min_indent:])
            else:
                normalized.append(line)

        return "\n".join(normalized)

    def _generate_ast_fix(self, filepath: str, error_info: Dict) -> Optional[str]:
        """Исправляет ошибку через AST-редактирование."""
        try:
            from core.ast_editor import ASTEditor
            
            editor = ASTEditor(str(PROJECT_ROOT))
            if not editor.load(filepath):
                return None
            
            error_type = error_info.get("error_type")
            message = error_info.get("message")
            
            # Если NameError - добавляем недостающую функцию
            if error_type == "NameError":
                import re
                match = re.search(r"name '(\w+)' is not defined", message)
                if match:
                    func_name = match.group(1)
                    # Проверяем, есть ли уже такая функция
                    if func_name in editor.get_functions():
                        return None
                    
                    # Добавляем функцию
                    func_code = f"def {func_name}():\n    print('{func_name} called')"
                    if editor.add_function(func_code):
                        if editor.save():
                            # Читаем обновлённый файл и создаём diff
                            content = Path(filepath).read_text(encoding='utf-8')
                            # Создаём diff через патч-инжин
                            diff = f"""--- {filepath}
+++ {filepath}
@@ -1,1 +1,1 @@
-{content.splitlines()[0] if content else ''}
+{content.splitlines()[0] if content else ''}"""
                            # Простой diff через difflib
                            import difflib
                            original = Path(filepath).read_text(encoding='utf-8')
                            diff = difflib.unified_diff(
                                original.splitlines(keepends=True),
                                content.splitlines(keepends=True),
                                fromfile=filepath,
                                tofile=filepath
                            )
                            return "".join(diff)
            return None
        except Exception as e:
            print(f"[SelfDebug] AST fix error: {e}")
            return None

    def apply_fix(self, diff: str, filepath: str) -> bool:
        file_path = Path(filepath)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        if not file_path.exists():
            return False

        try:
            original = file_path.read_text(encoding='utf-8')
        except Exception:
            return False

        if self._last_full_content is not None:
            # Полный текст файла уже был сгенерирован моделью — пишем его
            # напрямую, не пропуская через patch_engine. Построчный патчер
            # ненадёжен при дублирующихся строках контекста (например,
            # несколько "def main():" в файле) и может потерять целые
            # функции при применении диффа — именно это вызывало баг
            # с пропаданием кода после "Код нормализован".
            new_content = self._last_full_content
            self._last_full_content = None  # используем один раз
        else:
            # Патч без готового полного текста (например, из AST-ветки) —
            # применяем как раньше, через patch_engine.
            result = self.patch_engine.apply_patch(filepath, diff, dry_run=False)
            if not result.get("success"):
                file_path.write_text(original, encoding='utf-8')
                return False
            try:
                new_content = file_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"[SelfDebug] Ошибка чтения после патча: {e}")
                file_path.write_text(original, encoding='utf-8')
                return False

        # Нормализуем код
        normalized = self._normalize_code(new_content)
        if normalized != new_content:
            print("[SelfDebug] Код нормализован")
            new_content = normalized

        # Отладка: выводим первые 200 символов
        print("[SelfDebug] Содержимое после нормализации:")
        print(repr(new_content[:200]))

        # Записываем
        try:
            file_path.write_text(new_content, encoding='utf-8')
        except Exception as e:
            print(f"[SelfDebug] Ошибка записи: {e}")
            file_path.write_text(original, encoding='utf-8')
            return False

        # Проверяем синтаксис
        try:
            import py_compile
            py_compile.compile(file_path, doraise=True)
        except Exception as e:
            print(f"[SelfDebug] Синтаксическая ошибка: {e}")
            file_path.write_text(original, encoding='utf-8')
            return False

        # Проверяем импорт
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception as e:
            print(f"[SelfDebug] Ошибка импорта: {e}")
            file_path.write_text(original, encoding='utf-8')
            return False

        self.fixes_applied.append({"file": filepath, "diff": diff})
        return True

    def run_checks(self) -> Dict[str, bool]:
        results = {}
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "atlas_core/agent.py"],
            capture_output=True
        )
        results["syntax"] = result.returncode == 0
        lint_result = self.linter.lint_project()
        results["lint"] = lint_result.get("success", False)
        type_result = self.type_checker.check_project()
        results["typecheck"] = type_result.get("success", False)
        try:
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                capture_output=True
            )
            results["tests"] = test_result.returncode == 0
        except:
            results["tests"] = False
        return results

    def debug_cycle(self, error_input: str) -> Dict:
        import time
        from atlas_core.tools import create_backup, tool_rollback

        self.attempts = 0
        self.fixes_applied = []
        previous_attempts = []

        # Делаем бэкап перед исправлением
        backup_name = f"before_debug_{int(time.time())}"
        create_backup(backup_name)
        print(f"[SelfDebug] Бэкап создан: {backup_name}")

        if error_input.startswith("Traceback") or "Error" in error_input:
            error_info = self.analyze_traceback(error_input)
        else:
            log_errors = self.analyze_logs(error_input)
            if not log_errors:
                return {"success": False, "message": "Ошибок в логах не найдено"}
            error_info = self.analyze_traceback(log_errors[-1]["line"])

        if not error_info.get("file"):
            return {"success": False, "message": "Не удалось определить файл с ошибкой"}

        print(f"[SelfDebug] Анализ ошибки в {error_info['file']}:{error_info.get('line')}")
        print(f"[SelfDebug] Тип: {error_info.get('error_type')}")
        print(f"[SelfDebug] Сообщение: {error_info.get('message')}")

        while self.attempts < self.max_attempts:
            self.attempts += 1
            print(f"[SelfDebug] Попытка {self.attempts}/{self.max_attempts}")

            diff = self.generate_fix(error_info, previous_attempts)
            if not diff:
                previous_attempts.append("Не удалось сгенерировать исправление")
                continue

            if not self._validate_diff(diff, error_info["file"]):
                previous_attempts.append("Diff не прошёл валидацию (неприменим или пуст)")
                continue

            if not self.apply_fix(diff, error_info["file"]):
                previous_attempts.append("Не удалось применить патч")
                continue

            # Проверяем, исправлена ли ошибка
            if self._check_error_fixed(error_info):
                print("[SelfDebug] ✅ Ошибка исправлена")
                self._log_fix(error_info, diff)
                self._save_to_history({
                    "file": error_info["file"],
                    "error_type": error_info["error_type"],
                    "message": error_info["message"],
                    "diff": diff,
                    "attempts": self.attempts,
                    "success": True
                })
                return {
                    "success": True,
                    "attempts": self.attempts,
                    "file": error_info["file"],
                    "diff": diff,
                    "checks": self.run_checks()
                }
            else:
                # Откатываем изменения
                tool_rollback({})
                print("[SelfDebug] Откат к бэкапу")
                previous_attempts.append("Ошибка не исправлена после применения патча")

        # После всех попыток
        self._save_to_history({
            "file": error_info.get("file"),
            "error_type": error_info.get("error_type"),
            "message": error_info.get("message"),
            "attempts": self.attempts,
            "success": False
        })
        return {"success": False, "message": "Превышено количество попыток", "attempts": self.attempts}

    def _log_fix(self, error_info: Dict, diff: str):
        from memories.indexer import MemoryIndexer
        idx = MemoryIndexer()
        note = f"""
Исправление ошибки:
- Файл: {error_info.get('file')}
- Тип: {error_info.get('error_type')}
- Сообщение: {error_info.get('message')}
- Исправление:
{diff}
"""
        idx.add_note(f"fix_{error_info.get('error_type')}", note)

if __name__ == "__main__":
    debugger = SelfDebugger()
    print("Self Debugger готов")