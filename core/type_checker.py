"""
Type Checker — статическая проверка типов через Pyright.

Согласно Roadmap v3.1 (P0+ — Validation Pipeline):
- Проверка типов Python
- Выявление несоответствий типов
- Интеграция с проектом
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict

class TypeChecker:
    def __init__(self, root_path: str = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
    
    def check_file(self, filepath: str) -> Dict:
        """Проверяет один файл через pyright."""
        full_path = self.root / filepath
        if not full_path.exists():
            return {'success': False, 'message': f'Файл не найден: {filepath}'}
        
        try:
            cmd = [sys.executable, '-m', 'pyright', str(full_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return {'success': True, 'message': f'✅ {filepath}: типы корректны'}
            else:
                return {'success': False, 'message': f'❌ {filepath}:\n{result.stdout or result.stderr}'}
        except FileNotFoundError:
            return {'success': False, 'message': 'Pyright не установлен. Установите: pip install pyright'}
    
    def check_project(self) -> Dict:
        """Проверяет весь проект."""
        try:
            cmd = [sys.executable, '-m', 'pyright', '.']
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return {'success': True, 'message': '✅ Проект: типы корректны'}
            else:
                return {'success': False, 'message': result.stdout or result.stderr}
        except FileNotFoundError:
            return {'success': False, 'message': 'Pyright не установлен'}

if __name__ == "__main__":
    tc = TypeChecker()
    print("TypeChecker готов")