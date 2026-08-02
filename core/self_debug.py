"""
Self Debugging System — автономное исправление ошибок.
"""

import sys
import re
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

    def generate_fix(self, error_info: Dict, previous_attempts: List[str] = None) -> Optional[str]:
        filepath = error_info.get("file")
        line = error_info.get("line")
        error_type = error_info.get("error_type")
        message = error_info.get("message")

        if not filepath:
            return None

        try:
            file_path = Path(filepath)
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / file_path
            if not file_path.exists():
                return None
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[SelfDebug] Ошибка чтения файла: {e}")
            return None

        # Экранируем content для JSON
        import json as json_module
        content_escaped = json_module.dumps(content, ensure_ascii=False)

        prompt = f'''
Ты — инженер Atlas. Найди и исправь ошибку в коде.

Файл: {filepath}
Строка: {line}
Тип ошибки: {error_type}
Сообщение: {message}

Весь код файла:
{content_escaped}

Проанализируй ошибку и предложи исправление в виде полного исправленного кода файла.

Ответ должен быть ТОЛЬКО в формате JSON:
{{
    "fixed_code": "полный исправленный код файла",
    "explanation": "краткое объяснение"
}}

В исправленном коде:
- Сохрани все отступы и структуру
- Код должен быть валидным Python
- Экранируй все кавычки внутри fixed_code
'''
        if previous_attempts:
            prompt += "\n\nПредыдущие попытки не сработали:\n" + "\n".join(previous_attempts)
            prompt += "\nПопробуй другое исправление."

        messages = [{"role": "user", "content": prompt}]

        try:
            response = ask_llm(messages, agent="executive")

            # Очистка от markdown
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            data = json_module.loads(clean)
            fixed_code = data.get("fixed_code")
            explanation = data.get("explanation", "")

            if not fixed_code:
                print("[SelfDebug] LLM не вернула fixed_code")
                return None

            if fixed_code.strip() == content.strip():
                print("[SelfDebug] Код не изменился")
                return None

            diff = difflib.unified_diff(
                content.splitlines(keepends=True),
                fixed_code.splitlines(keepends=True),
                fromfile=filepath,
                tofile=filepath
            )
            diff_str = "".join(diff)

            if not diff_str.strip():
                print("[SelfDebug] Diff пустой")
                return None

            print(f"[SelfDebug] Сгенерирован diff ({len(diff_str)} символов)")
            print(f"[SelfDebug] Объяснение: {explanation[:100]}...")
            return diff_str

        except json_module.JSONDecodeError as e:
            print(f"[SelfDebug] Ошибка парсинга JSON: {e}")
            print(f"[SelfDebug] Ответ: {response[:200]}...")
            return None
        except Exception as e:
            print(f"[SelfDebug] Ошибка генерации: {e}")
            return None

    def apply_fix(self, diff: str, filepath: str) -> bool:
        # Проверяем, что файл существует
        file_path = Path(filepath)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        if not file_path.exists():
            return False

        # Сохраняем оригинальное содержимое
        try:
            original = file_path.read_text(encoding='utf-8')
        except:
            return False

        # Применяем патч
        result = self.patch_engine.apply_patch(filepath, diff, dry_run=False)
        if not result.get("success"):
            # Восстанавливаем оригинал
            file_path.write_text(original, encoding='utf-8')
            return False

        # Проверяем, что файл стал валидным
        try:
            import py_compile
            py_compile.compile(file_path, doraise=True)
        except Exception:
            # Восстанавливаем оригинал
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
