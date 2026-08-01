"""
Symbol Resolver для Atlas на основе Jedi.
"""
import jedi
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

class SymbolResolver:
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else PROJECT_ROOT
        self.script = None

    def index_file(self, filepath: str):
        """Индексирует файл для поиска символов."""
        full_path = self.project_path / filepath
        if not full_path.exists():
            return None
        with open(full_path, 'r', encoding='utf-8') as f:
            code = f.read()
        self.script = jedi.Script(code, path=str(full_path))
        return self.script

    def get_symbols(self, filepath: str) -> dict:
        """Возвращает все функции и классы в файле."""
        script = self.index_file(filepath)
        if not script:
            return {}
        names = script.get_names()
        symbols = {"functions": [], "classes": [], "imports": []}
        for n in names:
            if n.type == "function":
                symbols["functions"].append(n.name)
            elif n.type == "class":
                symbols["classes"].append(n.name)
            elif n.type == "import" or n.type == "from_import":
                symbols["imports"].append(n.name)
        return symbols

    def find_references(self, filepath: str, symbol_name: str) -> list:
        """Находит все использования символа в файле."""
        script = self.index_file(filepath)
        if not script:
            return []
        names = script.get_names()
        for n in names:
            if n.name == symbol_name:
                return [ref.module_path for ref in n.goto()]
        return []

    def get_definition(self, filepath: str, symbol_name: str):
        """Находит определение символа."""
        script = self.index_file(filepath)
        if not script:
            return None
        names = script.get_names()
        for n in names:
            if n.name == symbol_name:
                return n
        return None

if __name__ == "__main__":
    resolver = SymbolResolver()
    symbols = resolver.get_symbols("atlas_core/agent.py")
    print("Символы в agent.py:", symbols)