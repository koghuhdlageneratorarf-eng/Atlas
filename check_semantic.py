from pathlib import Path

from core.semantic_search import SemanticSearch

ss = SemanticSearch(str(Path(".").absolute()))
print("1. Документов:", ss.collection.count())
results = ss.search("runtime engine", n_results=3)
print('2. Поиск "runtime engine":')
for r in results:
    print(f'  {r["file"]}: {r["content"][:80]}...')
