"""
Linter — статический анализ кода через Ruff.
"""

import subprocess
import sys
from pathlib import Path


class Linter:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
    
    def lint_file(self, filepath: str, fix: bool = False) -> dict:
        full_path = self.root / filepath
        if not full_path.exists():
            return {'success': False, 'message': f'Файл не найден: {filepath}'}
        
        try:
            cmd = [sys.executable, '-m', 'ruff', 'check']
            if fix:
                cmd.append('--fix')
            cmd.append(str(full_path))
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return {'success': True, 'message': f'✅ {filepath}: проблем не найдено'}
            else:
                return {'success': False, 'message': f'❌ {filepath}:\n{result.stdout or result.stderr}'}
        except FileNotFoundError:
            return {'success': False, 'message': 'Ruff не установлен. Установите: pip install ruff'}
    
    def lint_project(self, fix: bool = False) -> dict:
        try:
            cmd = [sys.executable, '-m', 'ruff', 'check', '.']
            if fix:
                cmd.append('--fix')
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return {'success': True, 'message': '✅ Проект: проблем не найдено'}
            else:
                return {'success': False, 'message': result.stdout or result.stderr}
        except FileNotFoundError:
            return {'success': False, 'message': 'Ruff не установлен'}

if __name__ == "__main__":
    l = Linter()
    print("Linter готов")