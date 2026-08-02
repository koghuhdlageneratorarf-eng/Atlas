"""
Git History Analysis — анализ истории изменений проекта.

Согласно Roadmap v3.1 (P0+ — Project Intelligence):
- Просмотр истории коммитов
- Анализ изменений по файлам
- Статистика авторов
"""

import subprocess
from pathlib import Path


class GitHistoryAnalyzer:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent

    def _run_git(self, args: list[str]) -> str:
        """Выполнить git команду и вернуть вывод."""
        result = subprocess.run(
            ["git"] + args, cwd=self.root, capture_output=True, text=True
        )
        return result.stdout

    def get_commits(self, limit: int = 10, file: str = None) -> list[dict]:
        """Получить список последних коммитов."""
        cmd = [
            "log",
            f"--max-count={limit}",
            "--pretty=format:%h|%an|%ad|%s",
            "--date=short",
        ]
        if file:
            cmd.append("--")
            cmd.append(file)
        output = self._run_git(cmd)
        commits = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    }
                )
        return commits

    def get_file_history(self, filepath: str) -> list[dict]:
        """История изменений конкретного файла."""
        return self.get_commits(limit=20, file=filepath)

    def get_commit_diff(self, commit_hash: str) -> str:
        """Показать diff для конкретного коммита."""
        return self._run_git(["show", "--stat", commit_hash])

    def get_authors(self) -> list[dict]:
        """Статистика по авторам."""
        output = self._run_git(["shortlog", "-s", "-n", "--all"])
        authors = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                authors.append({"commits": int(parts[0]), "name": parts[1]})
        return authors

    def summary(self) -> str:
        authors = self.get_authors()
        recent = self.get_commits(limit=5)
        lines = [
            "Git History Analysis",
            "───────────────────",
            f"Всего авторов: {len(authors)}",
            "Топ авторов:",
        ]
        for a in authors[:3]:
            lines.append(f"  {a['name']} — {a['commits']} коммитов")
        lines.append("\nПоследние коммиты:")
        for c in recent:
            lines.append(
                f"  {c['hash']} {c['date']} {c['author']}: {c['message'][:50]}..."
            )
        return "\n".join(lines)


if __name__ == "__main__":
    gh = GitHistoryAnalyzer()
    print(gh.summary())
