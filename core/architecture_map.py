"""
Architecture Map — визуализация структуры проекта.

Согласно Roadmap v3.1 (P0+ — Project Intelligence):
- Понимание структуры проекта
- Визуализация модулей и их связей
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.dependency_analyzer import DependencyAnalyzer


class ArchitectureMap:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.modules: dict[str, set[str]] = {}
        self.module_types: dict[str, str] = {}

    def classify_module(self, name: str) -> str:
        if "atlas_core" in name or name == "core":
            return "core"
        if "agent" in name or "agents" in name:
            return "agent"
        if "evolution" in name:
            return "evolution"
        if "memory" in name or "memories" in name:
            return "memory"
        if "autopilot" in name:
            return "autopilot"
        if "plugin" in name:
            return "plugin"
        return "other"

    def build(self):

        analyzer = DependencyAnalyzer(str(self.root))
        analyzer.analyze_project()

        # Группируем по модулям (первая папка) и подпапкам
        for file, deps in analyzer.dependencies.items():
            parts = Path(file).parts
            if len(parts) >= 2:
                module = parts[0]
                submodule = "/".join(parts[:2]) if len(parts) >= 2 else module
            else:
                module = "root"
                submodule = "root"

            if submodule not in self.modules:
                self.modules[submodule] = set()
                self.module_types[submodule] = self.classify_module(submodule)

            for dep in deps:
                # Находим модуль зависимости (ищем среди существующих)
                dep_module = None
                for mod in self.modules.keys():
                    if dep in mod or mod in dep:
                        dep_module = mod
                        break
                if dep_module:
                    self.modules[submodule].add(dep_module)

    def summary(self) -> str:
        lines = ["Architecture Map", "────────────────"]
        by_type = defaultdict(list)
        for mod, typ in self.module_types.items():
            by_type[typ].append(mod)
        for typ, mods in sorted(by_type.items()):
            lines.append(f"\n📁 {typ.upper()} ({len(mods)})")
            for mod in sorted(mods):
                deps = self.modules.get(mod, set())
                dep_str = f" → {', '.join(deps)}" if deps else ""
                lines.append(f"  • {mod}{dep_str}")
        return "\n".join(lines)


if __name__ == "__main__":
    print("DEBUG: starting")
    am = ArchitectureMap(str(Path(".").absolute()))
    print("DEBUG: build start")
    am.build()
    print("DEBUG: build done")
    result = am.summary()
    print("DEBUG: summary length:", len(result))
    print(result)
