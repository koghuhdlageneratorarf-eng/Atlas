"""
Autonomous Development Loop — полный цикл разработки без ручного управления.
"""

import sys
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.symbol_resolver import SymbolResolver
from core.dependency_analyzer import DependencyAnalyzer
from core.patch_engine import PatchEngine
from core.self_debug import SelfDebugger
from core.git_intelligence import GitIntelligence
from Config.llm_client import ask_llm


class DevelopmentLoop:
    def __init__(self):
        self.resolver = SymbolResolver()
        self.dep_analyzer = DependencyAnalyzer()
        self.patch_engine = PatchEngine()
        self.debugger = SelfDebugger()
        self.git = GitIntelligence()
        self.steps = []
        self.failed = False
        self.target_file = None

    def set_target_file(self, filepath: str):
        self.target_file = filepath

    def analyze(self, task: str) -> Dict:
        print("[Develop] 📊 Анализ проекта...")
        self.dep_analyzer.analyze_project()
        relevant = []
        if self.target_file:
            relevant = [self.target_file]
        else:
            for file, deps in self.dep_analyzer.dependencies.items():
                if any(word in file.lower() for word in task.lower().split()):
                    relevant.append(file)
        result = {
            "task": task,
            "relevant_files": relevant[:5],
            "dependencies": dict(list(self.dep_analyzer.dependencies.items())[:5])
        }
        self.steps.append(("Анализ", "✅" if relevant else "⚠️"))
        return result

    def plan(self, analysis: Dict) -> Dict:
        print("[Develop] 📝 Создание плана...")
        prompt = f"""
Ты — Planner Agent. Составь план изменений для задачи:

Задача: {analysis['task']}

Релевантные файлы: {analysis.get('relevant_files', [])}

План должен включать:
1. Какие файлы нужно изменить (только имена файлов, например test_error.py)
2. Что именно нужно изменить
3. Проверки после изменения

Ответ должен быть ТОЛЬКО в формате JSON:
{{
    "files": ["file1.py", "file2.py"],
    "changes": ["описание изменения 1", "описание изменения 2"],
    "validation": ["проверка 1", "проверка 2"]
}}
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = ask_llm(messages, agent="executive")
            print(f"[Develop] RAW PLAN RESPONSE:\n{response[:300]}...")

            # Очистка от markdown
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            plan = json.loads(clean)
            self.steps.append(("План", "✅"))
            return plan
        except Exception as e:
            print(f"[Develop] Ошибка планирования: {e}")
            self.steps.append(("План", "❌"))
            return {"files": [], "changes": [], "validation": []}

    def execute(self, plan: Dict) -> bool:
        print("[Develop] 🔧 Выполнение изменений...")
        if not plan.get("files"):
            self.steps.append(("Изменение", "❌"))
            return False

        for filepath in plan.get("files", []):
            filepath = filepath.strip()
            # Нормализуем имя файла
            if not filepath.endswith(".py"):
                filepath = f"{filepath}.py"

            full_path = PROJECT_ROOT / filepath
            print(f"[Develop] DEBUG: checking {full_path}")

            if not full_path.exists():
                print(f"[Develop] Файл не найден: {filepath}")
                self.steps.append(("Изменение", "❌"))
                return False

            print(f"[Develop] ✅ Файл найден: {full_path}")

            # Читаем содержимое
            try:
                original = full_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                print(f"[Develop] ⚠️ Файл {filepath} имеет бинарный формат, пропускаем")
                self.steps.append(("Изменение", "⚠️"))
                return False

            # Генерируем исправление через SelfDebugger
            error_info = {
                "file": filepath,
                "line": 1,
                "error_type": "DevelopmentTask",
                "message": f"Задача: {plan.get('changes', ['изменить код'])[0]}"
            }
            diff = self.debugger.generate_fix(error_info)
            if diff:
                if self.debugger.apply_fix(diff, filepath):
                    print(f"[Develop] ✅ Исправлен {filepath}")
                else:
                    print(f"[Develop] ❌ Не удалось применить патч к {filepath}")
                    self.steps.append(("Изменение", "❌"))
                    return False
            else:
                print(f"[Develop] ❌ Не удалось сгенерировать исправление для {filepath}")
                self.steps.append(("Изменение", "❌"))
                return False

        self.steps.append(("Изменение", "✅"))
        return True

    def validate(self) -> bool:
        print("[Develop] 🔍 Проверка изменений...")
        if self.target_file:
            full_path = PROJECT_ROOT / self.target_file
            if not full_path.exists():
                self.steps.append(("Проверка", "❌"))
                return False

            # Проверка синтаксиса
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(full_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[Develop] Синтаксическая ошибка в {self.target_file}")
                print(result.stderr)
                self.steps.append(("Проверка", "❌"))
                return False

            # Проверка импорта
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_module", full_path)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except Exception as e:
                print(f"[Develop] Ошибка импорта: {e}")
                self.steps.append(("Проверка", "❌"))
                return False

            self.steps.append(("Проверка", "✅"))
            return True

        checks = self.debugger.run_checks()
        all_ok = all(checks.values())
        self.steps.append(("Проверка", "✅" if all_ok else "❌"))
        return all_ok

    def commit(self, task: str) -> bool:
        print("[Develop] 💾 Commit...")
        try:
            result = self.git.commit(task)
            if result.get("status") == "success":
                self.steps.append(("Commit", "✅"))
                return True
            else:
                print(f"[Develop] Commit error: {result.get('message')}")
                self.steps.append(("Commit", "❌"))
                return False
        except Exception as e:
            print(f"[Develop] Commit exception: {e}")
            self.steps.append(("Commit", "❌"))
            return False

    def debug(self, error: str = None) -> bool:
        print("[Develop] 🛠️ Исправление ошибок...")
        if error:
            result = self.debugger.debug_cycle(error)
            if result.get("success"):
                self.steps.append(("Исправление", "✅"))
                return True
        self.steps.append(("Исправление", "⚠️"))
        return False

    def test(self) -> bool:
        print("[Develop] 🧪 Запуск тестов...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                capture_output=True,
                text=True
            )
            ok = result.returncode == 0
            self.steps.append(("Тесты", "✅" if ok else "❌"))
            return ok
        except:
            self.steps.append(("Тесты", "❌"))
            return False

    def report(self) -> str:
        lines = ["\n" + "=" * 50, "📋 ОТЧЁТ ПО РАЗРАБОТКЕ", "=" * 50]
        for step, status in self.steps:
            lines.append(f"  {status} {step}")
        lines.append("=" * 50)
        if self.failed:
            lines.append("❌ Разработка завершена с ошибками")
        else:
            lines.append("✅ Разработка завершена успешно")
        return "\n".join(lines)

    def run(self, task: str) -> str:
        print("\n" + "=" * 50)
        print("🚀 ЗАПУСК АВТОНОМНОГО ЦИКЛА РАЗРАБОТКИ")
        print("=" * 50)

        # Извлекаем имя файла из задачи
        for word in task.split():
            if word.endswith(".py"):
                self.target_file = word
                print(f"[Develop] Целевой файл: {self.target_file}")
                break

        analysis = self.analyze(task)
        if not analysis.get("relevant_files"):
            self.failed = True

        plan = self.plan(analysis)
        if not plan.get("files"):
            self.failed = True

        if not self.execute(plan):
            self.failed = True

        if not self.validate():
            self.failed = True

        if self.failed:
            self.debug("Ошибка при выполнении")

        if not self.test():
            self.failed = True

        if not self.failed:
            self.commit(task)

        return self.report()


if __name__ == "__main__":
    loop = DevelopmentLoop()
    loop.set_target_file("test_error.py")
    result = loop.run("исправить ошибку в test_error.py")
    print(result)