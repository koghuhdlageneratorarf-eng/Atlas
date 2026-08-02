"""
AST Editor — безопасное редактирование Python-кода через AST.

Согласно Roadmap v3.1 (P0+ — Safe Code Editing):
- Изменение кода без нарушения синтаксиса
- Переименование функций, классов, переменных
- Добавление/удаление функций, импортов
- Генерация корректного кода из AST
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class ASTEditor:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.tree: ast.Module | None = None
        self.source: str = ""
        self.filepath: Path | None = None

    def load(self, filepath: str) -> bool:
        """Загружает файл и строит AST."""
        full_path = self.root / filepath
        if not full_path.exists():
            print(f"❌ Файл не найден: {filepath}")
            return False
        try:
            self.source = full_path.read_text(encoding="utf-8")
            self.tree = ast.parse(self.source)
            self.filepath = full_path
            return True
        except SyntaxError as e:
            print(f"❌ Синтаксическая ошибка в {filepath}: {e}")
            return False

    def save(self, filepath: str = None) -> bool:
        """Сохраняет AST обратно в файл."""
        if self.tree is None:
            print("❌ Нет загруженного AST")
            return False
        target = self.filepath if filepath is None else self.root / filepath
        try:
            code = ast.unparse(self.tree)
            target.write_text(code, encoding="utf-8")
            print(f"✅ Сохранено: {target}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False

    def get_functions(self) -> list[str]:
        """Возвращает список имён функций."""
        if self.tree is None:
            return []
        return [
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        ]

    def get_classes(self) -> list[str]:
        """Возвращает список имён классов."""
        if self.tree is None:
            return []
        return [
            node.name for node in ast.walk(self.tree) if isinstance(node, ast.ClassDef)
        ]

    def get_imports(self) -> list[str]:
        """Возвращает список импортов."""
        if self.tree is None:
            return []
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(
                        f"from {node.module} import {', '.join([a.name for a in node.names])}"
                    )
        return imports

    def rename_function(self, old_name: str, new_name: str) -> bool:
        """Переименовывает функцию во всём файле."""
        if self.tree is None:
            return False
        renamed = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == old_name:
                node.name = new_name
                renamed = True
            # Переименовываем вызовы
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == old_name:
                    node.func.id = new_name
                    renamed = True
        return renamed

    def add_function(self, func_code: str) -> bool:
        """Добавляет новую функцию в конец файла."""
        if self.tree is None:
            return False
        try:
            new_node = ast.parse(func_code).body[0]
            if not isinstance(new_node, ast.FunctionDef):
                print("❌ Передан не FunctionDef")
                return False
            self.tree.body.append(new_node)
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления функции: {e}")
            return False

    def add_import(self, module: str, alias: str = None) -> bool:
        """Добавляет импорт."""
        if self.tree is None:
            return False
        # Проверяем, есть ли уже такой импорт
        existing = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == module:
                        existing = True
        if existing:
            return True
        import_node = ast.Import(names=[ast.alias(name=module, asname=alias)])
        self.tree.body.insert(0, import_node)
        return True

    def remove_function(self, func_name: str) -> bool:
        """Удаляет функцию по имени."""
        if self.tree is None:
            return False
        new_body = []
        removed = False
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                removed = True
                continue
            new_body.append(node)
        if removed:
            self.tree.body = new_body
        return removed

    def set_docstring(self, func_name: str, docstring: str) -> bool:
        """Добавляет docstring функции, если его ещё нет, либо заменяет существующий."""
        if self.tree is None:
            return False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                doc_node = ast.Expr(value=ast.Constant(value=docstring))
                ast.copy_location(doc_node, node)
                ast.fix_missing_locations(doc_node)
                if ast.get_docstring(node, clean=False) is not None:
                    # Первый statement функции — уже существующий docstring, заменяем его
                    node.body[0] = doc_node
                else:
                    node.body.insert(0, doc_node)
                return True
        return False

    def replace_function_body(self, func_name: str, new_body: str) -> bool:
        """Заменяет тело функции на новый код."""
        if self.tree is None:
            return False
        try:
            new_body_node = ast.parse(new_body).body[0]
            if not isinstance(new_body_node, ast.FunctionDef):
                return False
            for node in ast.walk(self.tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    node.body = new_body_node.body
                    return True
            return False
        except Exception as e:
            print(f"❌ Ошибка замены тела: {e}")
            return False

    def summary(self) -> str:
        if self.tree is None:
            return "AST не загружен"
        return f"""
AST Editor
─────────────────
Файл: {self.filepath.name if self.filepath else 'не загружен'}
Функций: {len(self.get_functions())}
Классов: {len(self.get_classes())}
Импортов: {len(self.get_imports())}
"""


if __name__ == "__main__":
    editor = ASTEditor()
    if editor.load("atlas_core/agent.py"):
        print(editor.summary())
        print("Функции:", editor.get_functions()[:10])

        # Тест: переименовать функцию
        if editor.rename_function("print_banner", "print_welcome"):
            print("✅ Функция переименована (dry-run)")
            # Откатываем: переименовываем обратно для теста
            editor.rename_function("print_welcome", "print_banner")