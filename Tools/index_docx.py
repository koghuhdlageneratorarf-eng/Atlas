from memories.indexer import MemoryIndexer
from pathlib import Path
import docx

idx = MemoryIndexer()
count = 0
for file in Path(".").rglob("*.docx"):
    try:
        doc = docx.Document(file)
        content = "\n".join([p.text for p in doc.paragraphs])
        idx.add_note(str(file), content[:5000])
        count += 1
        print(f"✅ {file.name} ({len(content)} chars)")
    except Exception as e:
        print(f"❌ {file.name}: {e}")

print(f"\nВсего .docx: {count}")