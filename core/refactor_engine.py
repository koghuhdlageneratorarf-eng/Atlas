"""
Code Refactoring Engine — перемещение и изменение кода через AST.

Согласно Roadmap v3.1 (P0+ — Safe Code Editing):
- Перемещение функций между файлами
- Переименование классов с обновлением ссылок
- Изменение сигнатур функций
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.ast_editor import ASTEditor


class RefactorEngine:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent

    def move_function(self, src_file: str, dst_file: str, func_name: str) -> dict:
        """Перемещает функцию из одного файла в другой."""
        src_editor = ASTEditor(str(self.root))
        if not src_editor.load(src_file):
            return {"success": False, "message": f"Не удалось загрузить {src_file}"}

        dst_editor = ASTEditor(str(self.root))
        if not dst_editor.load(dst_file):
            return {"success": False, "message": f"Не удалось загрузить {dst_file}"}

        # Находим функцию в исходном файле
        func_node = None
        for node in src_editor.tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                func_node = node
                break

        if not func_node:
            return {
                "success": False,
                "message": f"Функция {func_name} не найдена в {src_file}",
            }

        # Удаляем из исходного
        src_editor.tree.body = [
            n
            for n in src_editor.tree.body
            if not (isinstance(n, ast.FunctionDef) and n.name == func_name)
        ]

        # Добавляем в целевой
        dst_editor.tree.body.append(func_node)

        # Сохраняем оба файла
        src_ok = src_editor.save()
        dst_ok = dst_editor.save()

        if src_ok and dst_ok:
            return {
                "success": True,
                "message": f"Функция {func_name} перемещена из {src_file} в {dst_file}",
            }
        else:
            return {"success": False, "message": "Ошибка сохранения после перемещения"}

    def rename_class(self, filepath: str, old_name: str, new_name: str) -> dict:
        """Переименовывает класс и обновляет все ссылки."""
        editor = ASTEditor(str(self.root))
        if not editor.load(filepath):
            return {"success": False, "message": f"Не удалось загрузить {filepath}"}

        renamed = False
        for node in ast.walk(editor.tree):
            if isinstance(node, ast.ClassDef) and node.name == old_name:
                node.name = new_name
                renamed = True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == old_name:
                    node.func.id = new_name
                    renamed = True
                elif (
                    isinstance(node.func, ast.Attribute) and node.func.attr == old_name
                ):
                    node.func.attr = new_name
                    renamed = True

        if not renamed:
            return {
                "success": False,
                "message": f"Класс {old_name} не найден в {filepath}",
            }

        if editor.save():
            return {
                "success": True,
                "message": f"Класс {old_name} → {new_name} переименован в {filepath}",
            }
        else:
            return {"success": False, "message": "Ошибка сохранения"}

    def change_function_signature(
        self, filepath: str, func_name: str, new_params: list[str]
    ) -> dict:
        """Изменяет сигнатуру функции."""
        editor = ASTEditor(str(self.root))
        if not editor.load(filepath):
            return {"success": False, "message": f"Не удалось загрузить {filepath}"}

        for node in ast.walk(editor.tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                # Создаём новые аргументы
                new_args = []
                for p in new_params:
                    # Если есть аннотация, сохраняем её
                    if ":" in p:
                        name, ann = p.split(":", 1)
                        new_args.append(
                            ast.arg(
                                arg=name.strip(), annotation=ast.Name(id=ann.strip())
                            )
                        )
                    else:
                        new_args.append(ast.arg(arg=p.strip()))
                node.args.args = new_args
                if editor.save():
                    return {
                        "success": True,
                        "message": f"Сигнатура {func_name} изменена в {filepath}",
                    }
                else:
                    return {"success": False, "message": "Ошибка сохранения"}

        return {
            "success": False,
            "message": f"Функция {func_name} не найдена в {filepath}",
        }


if __name__ == "__main__":
    ref = RefactorEngine()
    print("Refactor Engine готов")
