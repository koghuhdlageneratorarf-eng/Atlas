"""
Change Explanation — объяснение изменений через LLM.

Согласно Roadmap v3.1 (P0+ — Safe Code Editing):
- Объяснение, что именно изменилось
- Почему это изменение было сделано
- Какие последствия
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from Config.llm_client import ask_llm


class Explainer:
    def __init__(self):
        self.last_diff = None
        self.last_file = None
    
    def explain_diff(self, diff: str, filepath: str = None) -> str:
        """Объясняет изменения из diff."""
        if not diff or len(diff.strip()) < 10:
            return "❌ Diff пустой или слишком короткий"
        
        context = f"Файл: {filepath if filepath else 'неизвестен'}\n"
        prompt = f"""
Ты — помощник по объяснению изменений в коде.

Проанализируй следующий diff и объясни:
1. Что именно изменилось
2. Какие строки были добавлены, удалены или изменены
3. Какова вероятная цель этого изменения
4. Есть ли потенциальные риски

Diff:
{diff}

Ответ должен быть кратким, структурированным, на русском языке.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = ask_llm(messages, agent="executive")
            # Сохраняем последний diff
            self.last_diff = diff
            self.last_file = filepath
            return response
        except Exception as e:
            return f"❌ Ошибка при объяснении: {e}"
    
    def explain_last(self) -> str:
        """Объясняет последний сохранённый diff."""
        if not self.last_diff:
            return "❌ Нет сохранённого diff для объяснения"
        return self.explain_diff(self.last_diff, self.last_file)

if __name__ == "__main__":
    e = Explainer()
    print("Explainer готов")