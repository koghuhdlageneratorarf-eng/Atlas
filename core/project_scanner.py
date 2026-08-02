"""
Project Scanner — полноценный анализ структуры проекта.

Согласно Roadmap v3.1 (P0+ — Project Intelligence):
- Сканирование всех файлов с учётом .gitignore
- Анализ структуры папок и типов файлов
- Сбор метаданных: размер, строки, язык
- Экспорт в JSON и текстовый отчёт
"""

import fnmatch
import json
from datetime import datetime
from pathlib import Path


class ProjectScanner:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.ignore_patterns = self._load_gitignore()
        self.files: list[dict] = []
        self.stats: dict = {}

    def _load_gitignore(self) -> set[str]:
        """Загружает .gitignore и возвращает набор паттернов."""
        patterns = {
            ".git",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "venv",
            ".venv",
            "env",
            "ENV",
            "env.bak",
            "venv.bak",
            "Storage",
            "logs",
            "*.log",
            "*.tmp",
            ".idea",
            ".vscode",
            "*.swp",
            "*.swo",
            "node_modules",
            "dist",
            "build",
            "*.egg-info",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }
        gitignore_path = self.root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.add(line)
        return patterns

    def _is_ignored(self, path: Path) -> bool:
        """Проверяет, должен ли файл/папка быть проигнорирован."""
        rel = path.relative_to(self.root)
        parts = rel.parts
        for pattern in self.ignore_patterns:
            if pattern.startswith("/"):
                # Абсолютный паттерн от корня
                if fnmatch.fnmatch(str(rel), pattern[1:]):
                    return True
            else:
                # Относительный паттерн
                for part in parts:
                    if fnmatch.fnmatch(part, pattern):
                        return True
        return False

    def _get_language(self, ext: str) -> str:
        """Определяет язык по расширению."""
        mapping = {
            ".py": "Python",
            ".md": "Markdown",
            ".txt": "Text",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".html": "HTML",
            ".css": "CSS",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell",
            ".xml": "XML",
            ".csv": "CSV",
            ".toml": "TOML",
            ".ini": "INI",
            ".cfg": "Config",
            ".conf": "Config",
            ".docx": "Word",
            ".pdf": "PDF",
            ".jpg": "Image",
            ".png": "Image",
            ".svg": "Image",
            ".gif": "Image",
        }
        return mapping.get(ext.lower(), "Other")

    def scan(self, extensions: list[str] = None) -> dict:
        """
        Сканирует проект и возвращает структурированные данные.

        Args:
            extensions: список расширений для сканирования (по умолчанию все)
        """
        self.files = []
        self.stats = {
            "total_files": 0,
            "total_size": 0,
            "total_lines": 0,
            "languages": {},
            "extensions": {},
            "folders": set(),
        }

        for item in self.root.rglob("*"):
            if self._is_ignored(item):
                continue
            if not item.is_file():
                continue
            if extensions and item.suffix not in extensions:
                continue

            rel_path = str(item.relative_to(self.root))
            ext = item.suffix or "no_ext"
            lang = self._get_language(ext)
            size = item.stat().st_size
            lines = self._count_lines(item)

            file_info = {
                "path": rel_path,
                "name": item.name,
                "ext": ext,
                "language": lang,
                "size": size,
                "lines": lines,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
            }
            self.files.append(file_info)

            # Статистика
            self.stats["total_files"] += 1
            self.stats["total_size"] += size
            self.stats["total_lines"] += lines
            self.stats["languages"][lang] = self.stats["languages"].get(lang, 0) + 1
            self.stats["extensions"][ext] = self.stats["extensions"].get(ext, 0) + 1
            self.stats["folders"].add(str(item.parent.relative_to(self.root)))

        self.stats["folders"] = sorted(self.stats["folders"])
        return self.stats

    def _count_lines(self, filepath: Path) -> int:
        """Подсчитывает количество строк в файле."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except:
            return 0

    def get_report(self) -> str:
        """Возвращает текстовый отчёт."""
        lines = [
            "=" * 50,
            f"PROJECT SCAN REPORT — {self.root.name}",
            "=" * 50,
            f"Сканировано: {self.stats.get('total_files', 0)} файлов",
            f"Общий размер: {self.stats.get('total_size', 0) // 1024} KB",
            f"Общее количество строк: {self.stats.get('total_lines', 0)}",
            "",
            "📊 Языки:",
        ]
        for lang, count in sorted(
            self.stats.get("languages", {}).items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {lang}: {count} файлов")

        lines.append("")
        lines.append("📁 Папки:")
        for folder in self.stats.get("folders", [])[:20]:
            lines.append(f"  • {folder}")
        if len(self.stats.get("folders", [])) > 20:
            lines.append(f"  ... и ещё {len(self.stats['folders']) - 20} папок")

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)

    def to_json(self) -> str:
        """Возвращает JSON-представление."""
        data = {
            "root": str(self.root),
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "files": self.files[:100],  # ограничиваем для больших проектов
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def save_report(self, output_path: str = "project_report.txt"):
        """Сохраняет отчёт в файл."""
        Path(output_path).write_text(self.get_report(), encoding="utf-8")
        print(f"✅ Отчёт сохранён: {output_path}")


if __name__ == "__main__":
    scanner = ProjectScanner()
    scanner.scan()
    print(scanner.get_report())
    scanner.save_report()
