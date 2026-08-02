"""
Project Knowledge Base — единая база знаний о проекте.

Согласно Roadmap v3.1 (P0+ — Project Intelligence):
- Объединяет все компоненты Project Intelligence
- Предоставляет единый интерфейс для получения знаний о проекте
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.architecture_map import ArchitectureMap
from core.call_graph import CallGraph
from core.dependency_analyzer import DependencyAnalyzer
from core.git_history import GitHistoryAnalyzer
from core.semantic_search import SemanticSearch
from core.symbol_resolver import SymbolResolver


class ProjectKnowledgeBase:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.dep_analyzer = DependencyAnalyzer(str(self.root))
        self.call_graph = CallGraph(str(self.root))
        self.arch_map = ArchitectureMap(str(self.root))
        self.semantic = SemanticSearch(str(self.root))
        self.git = GitHistoryAnalyzer(str(self.root))
        self.symbol_resolver = SymbolResolver(str(self.root))

        # Кэшируем результаты
        self._deps = None
        self._calls = None
        self._arch = None
        self._symbols = None

    def refresh(self):
        """Обновить все данные."""
        print("[KnowledgeBase] Обновление...")
        self._deps = self.dep_analyzer.analyze_project()
        self._calls = self.call_graph.analyze_project()
        self.arch_map.build()
        self._arch = self.arch_map.modules
        self._symbols = (
            self.symbol_resolver.symbols
            if hasattr(self.symbol_resolver, "symbols")
            else {}
        )
        print("[KnowledgeBase] Готово")

    def get_summary(self) -> str:
        """Полная сводка по проекту."""
        lines = [
            "=" * 50,
            "PROJECT KNOWLEDGE BASE",
            "=" * 50,
            "",
            "📁 Project Structure",
            f"  Корень: {self.root}",
            "",
            "📊 Statistics",
            f"  Файлов с зависимостями: {len(self._deps) if self._deps else 0}",
            f"  Функций: {len(self._calls) if self._calls else 0}",
            "",
            "🏗️ Architecture",
        ]
        if self._arch:
            for module in list(self._arch.keys())[:5]:
                lines.append(f"  • {module}")

        lines.append("")
        lines.append("📜 Git History")
        git_summary = self.git.summary().split("\n")[:5]
        lines.extend(git_summary)

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)

    def search(self, query: str) -> list[dict]:
        """Семантический поиск по всей базе знаний."""
        return self.semantic.search(query, n_results=5)

    def get_dependencies(self, file: str) -> set:
        """Получить зависимости файла."""
        if self._deps:
            return self._deps.get(file, set())
        return set()

    def get_callers(self, func: str) -> set:
        """Кто вызывает функцию."""
        if self._calls:
            return self._calls.get(func, set())
        return set()


# Singleton
_kb = None


def get_knowledge_base() -> ProjectKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = ProjectKnowledgeBase()
        _kb.refresh()
    return _kb


if __name__ == "__main__":
    kb = get_knowledge_base()
    print(kb.get_summary())
    print("\n🔍 Поиск 'runtime':")
    for r in kb.search("runtime"):
        print(f"  {r['file']}: {r['content'][:80]}...")
