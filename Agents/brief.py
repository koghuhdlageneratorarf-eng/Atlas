"""
Brief Agent — sozdaet podrobnoe TZ dlya proekta.
Dva rezhima:
1. Korotkiy zapros (< 300 simvolov) → generiruet TZ cherez 7B
2. Gotovoe TZ (> 300 simvolov) → strukturiruet i sohranyaet kak est
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Config"))
from llm_client import ask_llm

SYSTEM_PROMPT = """Ty — Brief Agent v sisteme Atlas.
Tvoya zadacha: iz korotkogo zaprosa polzovatelya sostavit podrobnoe tekhnicheskoe zadanie (TZ) dlya veb-sayta.

TZ dolzhen soderzhat:
1. Nazvanie kompanii / proekta
2. Opisanie biznesa (2-3 predlozheniya)
3. Tselevaya auditoriya
4. Glavnye preimushchestva (3-5 punktov)
5. Uslugi / tovary s opisaniem i tsenami
6. Kontakty: telefon, email, adres, vremya raboty
7. Pozhelaniya po dizaynu (tsveta, stil, nastroenie)
8. Razdeli sayta (hero, uslugi, o nas, portfolio, kontakty, footer)

Otvet STROGO v formate Markdown (zagolovki, spiski).
Ne pishi kod. Tolko tekstovoe TZ."""


def structure_existing_tz(text: str):
    """Esli tekst uzhe pohozh na TZ, privodit k standartnomu formatu."""
    prompt = f"""Ty — Brief Agent. U tebya uzhe est gotovoe tekhnichaskoe zadanie ot klienta.
Pereformatiruy ego v chistyy Markdown s zagolovkami, ne menyaya soderzhanie.

ISKHODNYY TEKST:
{text}

PRAVILA:
- Sohrani VSE dannye (tseny, telefony, adresa, nazvaniya)
- Dobav zagolovki: ## Nazvanie, ## Opisanie, ## Uslugi, ## Kontakty, ## Dizayn
- Ne dobavlyay vymyshlennogo, chego ne bylo v iskhodnom tekste
- Ne pishi kod, tolko tekst

Rezultat:"""
    
    messages = [{"role": "user", "content": prompt}]
    return ask_llm(messages, model="qwen2.5-coder:3b")


def run_brief(task: str, project_dir: str):
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    brief_file = project_path / "brief.md"

    # Rezhim 2: gotovoe TZ (dlinnoe)
    if len(task) > 300:
        print(f"Brief Agent: obnaruzheno gotovoe TZ ({len(task)} simvolov)")
        print("   Strukturiruyu i sohranyayu...")
        tz = structure_existing_tz(task)
    else:
        # Rezhim 1: korotkiy zapros, generiruem TZ
        print(f"Brief Agent: sostavlyayu TZ dlya '{task[:50]}...'")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Zapros: {task}"}
        ]
        tz = ask_llm(messages, model="qwen2.5-coder:7b")

    brief_file.write_text(tz, encoding="utf-8")
    print(f"   TZ sohraneno: {brief_file}")
    print(f"   Razmer: {len(tz)} simvolov")
    return str(brief_file)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Ispolzovanie: python Agents/brief.py "zadacha" ./put_k_proektu')
        sys.exit(1)

    task_arg = sys.argv[1]
    project_dir_arg = sys.argv[2]
    run_brief(task_arg, project_dir_arg)
