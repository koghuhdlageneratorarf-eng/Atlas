"""
Dependency Analyzer — анализ зависимостей между модулями.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class DependencyAnalyzer:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.dependencies: dict[str, set[str]] = {}
        self.reverse_deps: dict[str, set[str]] = {}

    def analyze_file(self, filepath: Path) -> set[str]:
        """Анализирует один файл — находит все импорты."""
        if not filepath.exists():
            return set()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except:
            return set()

        imports = set()
        module_dir = filepath.parent

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    imports.add(module_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    # Если импорт относительный
                    if node.level > 0:
                        # Ищем модуль в родительских папках
                        rel_path = module_dir / f"{module_name}.py"
                        if (
                            rel_path.exists()
                            or (module_dir / module_name / "__init__.py").exists()
                        ):
                            imports.add(module_name)
                    else:
                        imports.add(module_name)
                elif node.level > 0:
                    # Относительный импорт без имени модуля (from . import x)
                    imports.add(module_dir.name)

        return imports

    def analyze_project(self, extensions: list[str] = [".py"]) -> dict[str, set[str]]:
        self.dependencies = {}
        self.reverse_deps = {}

        std_lib = {
            "os",
            "sys",
            "json",
            "re",
            "time",
            "datetime",
            "pathlib",
            "typing",
            "dataclasses",
            "enum",
            "subprocess",
            "importlib",
            "requests",
            "yaml",
            "logging",
            "threading",
            "uuid",
            "ast",
            "inspect",
            "types",
            "collections",
            "itertools",
            "functools",
            "hashlib",
            "base64",
            "tempfile",
            "shutil",
            "glob",
            "socket",
        }

        for py_file in self.root.rglob("*"):
            if py_file.suffix in extensions and "__pycache__" not in str(py_file):
                rel_path = str(py_file.relative_to(self.root))
                imports = self.analyze_file(py_file)
                # Фильтруем только локальные модули
                local_imports = set()
                for imp in imports:
                    if imp in std_lib:
                        continue
                    # Проверяем, существует ли такой модуль в проекте
                    possible_path = self.root / f"{imp}.py"
                    possible_init = self.root / imp / "__init__.py"
                    if possible_path.exists() or possible_init.exists():
                        local_imports.add(imp)
                    else:
                        # Проверяем в подпапках (быстро, без rglob)
                        for subdir in self.root.iterdir():
                            if subdir.is_dir() and (subdir / f"{imp}.py").exists():
                                local_imports.add(imp)
                                break
                if local_imports:
                    self.dependencies[rel_path] = local_imports

        # Строим обратные зависимости
        for file, deps in self.dependencies.items():
            for dep in deps:
                if dep not in self.reverse_deps:
                    self.reverse_deps[dep] = set()
                self.reverse_deps[dep].add(file)

        return self.dependencies

    def find_cycles(self) -> list[list[str]]:
        """Находит циклические зависимости."""
        cycles = []
        visited = set()
        path = []

        def dfs(node: str):
            if node in path:
                cycle = path[path.index(node) :] + [node]
                cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for dep in self.dependencies.get(node, []):
                if dep in self.dependencies:
                    dfs(dep)
            path.pop()

        for file in self.dependencies:
            dfs(file)

        return cycles

    def get_dependents(self, module: str) -> set[str]:
        """Кто зависит от модуля."""
        return self.reverse_deps.get(module, set())

    def get_dependencies(self, module: str) -> set[str]:
        """От кого зависит модуль."""
        return self.dependencies.get(module, set())

    def status(self) -> str:
        total = len(self.dependencies)
        cycles = self.find_cycles()
        return f"""
Dependency Analyzer
─────────────────
Файлов с зависимостями: {total}
Циклических зависимостей: {len(cycles)}
"""


if __name__ == "__main__":
    analyzer = DependencyAnalyzer()
    analyzer.analyze_project()
    print(analyzer.status())
