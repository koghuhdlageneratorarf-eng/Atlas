"""
Evolution Engine v2.0 — Atlas сам генерирует и применяет улучшения.
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent

class Suggester:
    def __init__(self):
        self.suggestions_file = PROJECT_ROOT / "Memory" / "suggestions.json"
        self._load()

    def _load(self):
        if self.suggestions_file.exists():
            self.suggestions = json.loads(self.suggestions_file.read_text(encoding='utf-8'))
        else:
            self.suggestions = []

    def save(self):
        self.suggestions_file.write_text(json.dumps(self.suggestions, indent=2, ensure_ascii=False), encoding='utf-8')

    def analyze(self, context: str = ""):
        """Анализирует проект и предлагает улучшения через LLM."""
        from Config.llm_client import ask_llm

        files = []
        for ext in ["*.py", "*.md", "*.yaml", "*.json"]:
            for f in PROJECT_ROOT.rglob(ext):
                if "Storage" in str(f) or "chroma" in str(f):
                    continue
                files.append(f"{f.name} ({f.stat().st_size} bytes)")

        file_list = "\n".join(files[:30])

        prompt = f"""
Ты — Evolution Engine Atlas. Проанализируй проект и предложи 3-5 улучшений.

Контекст: {context[:1000] if context else "Текущее состояние проекта"}

Файлы проекта:
{file_list}

Ответь в формате JSON:
{{
  "suggestions": [
    {{
      "title": "Название улучшения",
      "description": "Что сделать",
      "why": "Зачем это нужно",
      "priority": "high/medium/low",
      "effort": "small/medium/large",
      "code": "КОД, КОТОРЫЙ НУЖНО СОЗДАТЬ ИЛИ ИЗМЕНИТЬ (если применимо)",
      "files": ["список файлов для изменения"]
    }}
  ]
}}
"""
        messages = [{"role": "user", "content": prompt}]
        print("[Evolution] Анализирую проект...")
        response = ask_llm(messages, agent="executive")

        try:
            import re
            clean = re.sub(r"```json\s*", "", response)
            clean = re.sub(r"```\s*", "", clean)
            data = json.loads(clean)
            new_suggestions = data.get("suggestions", [])
            for s in new_suggestions:
                s["timestamp"] = datetime.now().isoformat()
                s["status"] = "new"
                self.suggestions.append(s)
            self.save()
            return new_suggestions
        except Exception as e:
            print(f"[Evolution] Ошибка парсинга: {e}")
            return []

    def list_suggestions(self):
        if not self.suggestions:
            return "Нет предложений"
        result = []
        for i, s in enumerate(self.suggestions, 1):
            status = s.get("status", "new")
            title = s.get("title", "Без названия")
            desc = s.get("description", "")[:80]
            result.append(f"{i}. [{status}] {title}\n   {desc}...")
        return "\n".join(result)

    def apply(self, index: int) -> str:
        if index < 1 or index > len(self.suggestions):
            return "❌ Неверный индекс"

        s = self.suggestions[index - 1]
        title = s.get("title", "")
        desc = s.get("description", "")
        code = s.get("code", "")
        files = s.get("files", [])

        # Если код уже есть — применяем
        if code and files:
            return self._apply_code(code, files, title)

        # Если кода нет — генерируем через LLM
        print("[Evolution] Генерирую код для улучшения...")
        max_retries = 2
        last_error = ""

        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"[Evolution] Перегенерация {attempt}/{max_retries}...")
                generated = self._generate_code(title, desc + f"\n\nОшибка: {last_error}")
                if not generated:
                    break
                code = generated.get("code", "")
                files = generated.get("files", [])

            result = self._apply_code(code, files, title)
            if "❌" not in result:
                return result
            last_error = result

        return f"❌ Не удалось применить {title} после {max_retries} попыток"

    def _generate_code(self, title: str, desc: str) -> dict:
        """Генерирует код через LLM."""
        from Config.llm_client import ask_llm

        prompt = f"""
Ты — инженер Atlas. Напиши код для улучшения:

Название: {title}
Описание: {desc}

Верни JSON:
{{
  "code": "полный код файла",
  "files": ["путь/к/файлу.py"]
}}
"""
        messages = [{"role": "user", "content": prompt}]
        response = ask_llm(messages, agent="developer")

        try:
            import re
            clean = re.sub(r"```json\s*", "", response)
            clean = re.sub(r"```\s*", "", clean)
            return json.loads(clean)
        except:
            return None

    def _apply_code(self, code: str, files: list, title: str) -> str:
        import ast
        results = []
        for filepath in files:
            path = PROJECT_ROOT / filepath
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                ast.parse(code)
            except SyntaxError as e:
                return f"❌ Синтаксическая ошибка в {filepath}: {e}"
            path.write_text(code, encoding='utf-8')
            results.append(f"✅ {path}")
        for s in self.suggestions:
            if s.get("title") == title:
                s["status"] = "applied"
                s["applied_at"] = datetime.now().isoformat()
                break
        self.save()
        return f"✅ Применено: {title}\n" + "\n".join(results)


if __name__ == "__main__":
    s = Suggester()
    print("=== EVOLUTION ENGINE v2.0 ===")
    print("1. Анализ и предложения")
    print("2. Список предложений")
    print("3. Применить предложение")
    choice = input("Выбери: ")
    if choice == "1":
        s.analyze()
        print("✅ Предложения созданы")
    elif choice == "2":
        print(s.list_suggestions())
    elif choice == "3":
        idx = int(input("Номер предложения: "))
        print(s.apply(idx))