"""
Call Graph — анализ вызовов функций в проекте.

Согласно Roadmap v3.1 (P0+ — Project Intelligence):
- Понимание, какие функции вызывают другие
- Оценка влияния изменений
- Поиск неиспользуемых функций
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class CallGraph:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.calls: dict[str, set[str]] = {}
        self.callers: dict[str, set[str]] = {}
        self.functions: dict[str, str] = {}

    def analyze_file(self, filepath: Path) -> dict[str, set[str]]:
        if not filepath.exists():
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except:
            return {}

        calls = {}
        current_class = None
        current_func = None
        rel_path = str(filepath.relative_to(self.root))

        for node in ast.walk(tree):
            # Запоминаем класс
            if isinstance(node, ast.ClassDef):
                current_class = node.name
            # Запоминаем функцию (глобальную или внутри класса)
            elif isinstance(node, ast.FunctionDef):
                if current_class:
                    func_name = f"{current_class}.{node.name}"
                else:
                    func_name = node.name
                current_func = func_name
                calls[func_name] = set()
                self.functions[f"{rel_path}::{func_name}"] = rel_path
            # Обрабатываем вызовы внутри функций
            elif isinstance(node, ast.Call) and current_func:
                if isinstance(node.func, ast.Name):
                    calls[current_func].add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    # self.method() или Class.method()
                    calls[current_func].add(node.func.attr)
        return calls

    def analyze_project(self) -> dict[str, set[str]]:
        self.calls = {}
        self.callers = {}
        self.functions = {}

        for py_file in self.root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            file_calls = self.analyze_file(py_file)
            rel_path = str(py_file.relative_to(self.root))
            for func, called in file_calls.items():
                key = f"{rel_path}::{func}"
                self.calls[key] = called
                for c in called:
                    if c not in self.callers:
                        self.callers[c] = set()
                    self.callers[c].add(key)
        return self.calls

    def get_calls(self, func: str) -> set[str]:
        return self.calls.get(func, set())

    def get_callers(self, func: str) -> set[str]:
        return self.callers.get(func, set())

    def find_unused(self) -> list[str]:
        used = set()
        for callers in self.callers.values():
            used.update(callers)
        all_funcs = set(self.calls.keys())
        return list(all_funcs - used)

    def summary(self) -> str:
        return f"""
Call Graph
─────────────────
Функций: {len(self.calls)}
Вызовов: {sum(len(v) for v in self.calls.values())}
Неиспользуемых функций: {len(self.find_unused())}
"""


if __name__ == "__main__":
    cg = CallGraph(str(Path("Atlas").absolute()))
    cg.analyze_project()
    print(cg.summary())

    print("\nПример вызовов:")
    for func, calls in list(cg.calls.items())[:5]:
        print(f"  {func}: {calls}")
