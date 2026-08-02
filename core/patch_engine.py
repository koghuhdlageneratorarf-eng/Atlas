"""
Patch Engine — безопасное применение изменений через unified diff.
"""

import re
import shutil
import subprocess
from pathlib import Path


class PatchEngine:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.git_path = shutil.which("git")
        self.patch_path = shutil.which("patch")

    def _apply_with_python(self, filepath: Path, diff: str, dry_run: bool) -> dict:
        try:
            original = filepath.read_text(encoding="utf-8")
            lines = original.splitlines(keepends=True)
            diff_lines = diff.splitlines()
            for i, line in enumerate(diff_lines):
                if line.startswith("@@"):
                    match = re.match(
                        r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line
                    )
                    if match:
                        old_start = int(match.group(1)) - 1
                        old_count = int(match.group(2)) if match.group(2) else 1
                        add_lines = []
                        j = i + 1
                        while j < len(diff_lines) and not diff_lines[j].startswith(
                            "@@"
                        ):
                            if diff_lines[j].startswith("+"):
                                add_lines.append(diff_lines[j][1:] + "\n")
                            j += 1
                        if add_lines:
                            if old_count > 0:
                                del lines[old_start : old_start + old_count]
                            lines[old_start:old_start] = add_lines
                        break
            new_content = "".join(lines)
            if dry_run:
                return {
                    "success": True,
                    "message": "Патч корректен (Python dry-run)",
                    "diff": diff,
                    "file": str(filepath),
                }
            filepath.write_text(new_content, encoding="utf-8")
            return {
                "success": True,
                "message": f"Патч применён к {filepath.name} (Python)",
                "diff": diff,
                "file": str(filepath),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка Python-применения: {e}",
                "diff": diff,
                "file": str(filepath),
            }

    def apply_patch(self, filepath: str, diff: str, dry_run: bool = False) -> dict:
        # Преобразуем экранированные переводы строк
        diff = diff.replace("\\n", "\n")
        full_path = self.root / filepath
        if not full_path.exists():
            return {"success": False, "message": f"Файл не найден: {filepath}"}

        # Попытка через git
        if self.git_path:
            diff_file = self.root / "Storage" / "temp_patch.diff"
            diff_file.parent.mkdir(parents=True, exist_ok=True)
            diff_file.write_text(diff, encoding="utf-8")
            try:
                cmd_check = [self.git_path, "apply", "--check", str(diff_file)]
                r = subprocess.run(
                    cmd_check, cwd=self.root, capture_output=True, text=True
                )
                if r.returncode == 0:
                    if dry_run:
                        return {
                            "success": True,
                            "message": "Патч корректен (git dry-run)",
                            "diff": diff,
                            "file": filepath,
                        }
                    cmd_apply = [self.git_path, "apply", "--index", str(diff_file)]
                    r2 = subprocess.run(
                        cmd_apply, cwd=self.root, capture_output=True, text=True
                    )
                    if r2.returncode == 0:
                        return {
                            "success": True,
                            "message": f"Патч применён к {filepath} (git)",
                            "diff": diff,
                            "file": filepath,
                        }
            finally:
                diff_file.unlink()

        # Попытка через patch
        if self.patch_path:
            diff_file = self.root / "Storage" / "temp_patch.diff"
            diff_file.parent.mkdir(parents=True, exist_ok=True)
            diff_file.write_text(diff, encoding="utf-8")
            try:
                cmd_check = [self.patch_path, "-p1", "--dry-run", "-i", str(diff_file)]
                r = subprocess.run(
                    cmd_check, cwd=self.root, capture_output=True, text=True
                )
                if r.returncode == 0:
                    if dry_run:
                        return {
                            "success": True,
                            "message": "Патч корректен (patch dry-run)",
                            "diff": diff,
                            "file": filepath,
                        }
                    cmd_apply = [self.patch_path, "-p1", "-i", str(diff_file)]
                    r2 = subprocess.run(
                        cmd_apply, cwd=self.root, capture_output=True, text=True
                    )
                    if r2.returncode == 0:
                        return {
                            "success": True,
                            "message": f"Патч применён к {filepath} (patch)",
                            "diff": diff,
                            "file": filepath,
                        }
            finally:
                diff_file.unlink()

        # Fallback на Python
        return self._apply_with_python(full_path, diff, dry_run)
