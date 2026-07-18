"""
Executive Agent — menedzher proekta Atlas.
Poluchaet zadachu ot polzovatelya, analiziruet cherez LLM (7B) i vozvrashchaet plan.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

SYSTEM_PROMPT = """Ty — Executive Agent v sisteme Atlas.
Tvoya zadacha: poluchit zapros ot polzovatelya i sostavit plan vypolneniya.
U tebya est komanda specialistov:
- Developer — pishet kod (HTML, CSS, JS, Python)
- Designer — otvechaet za vizual, stil, animatsii
- QA — proveryaet rezultat, ishchet oshibki
- Researcher — ishchet informatsiyu, analiziruet

Otvet strogo v formate JSON:
{
  "task": "kratkoe opisanie zadachi",
  "agents_needed": ["Developer", "Designer"],
  "plan": ["shag 1", "shag 2", "shag 3"],
  "notes": "dopolnitelnye zamechaniya"
}

Ne pishi kod. Tolko plan."""


def run_executive(task: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Zadacha: {task}"}
    ]

    print("Executive dumayet (7B)...")
    answer = ask_llm(messages, model="qwen2.5-coder:7b")

    try:
        cleaned = answer.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        plan = json.loads(cleaned)
        print("\nPlan vypolneniya:")
        print(f"   Zadacha: {plan.get('task', '—')}")
        print(f"   Agenty: {', '.join(plan.get('agents_needed', []))}")
        print(f"   Plan:")
        for i, step in enumerate(plan.get('plan', []), 1):
            print(f"      {i}. {step}")
        if plan.get('notes'):
            print(f"   Zametki: {plan['notes']}")
        return plan

    except json.JSONDecodeError:
        print("\nModel vernula ne JSON. Syroy otvet:")
        print(answer)
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Ispolzovanie: python Agents/executive.py "sdelay sayt dlya mastera manikyura"')
        sys.exit(1)

    task = sys.argv[1]
    run_executive(task)
