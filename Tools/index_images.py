from memories.indexer import MemoryIndexer
from pathlib import Path
from PIL import Image
import pytesseract

# Укажи путь к Tesseract (если установлен)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

idx = MemoryIndexer()
count = 0

for file in Path("memories").rglob("*.png"):
    try:
        img = Image.open(file)
        text = pytesseract.image_to_string(img, lang="rus+eng")
        if text.strip():
            idx.add_note(str(file), text[:5000])
            count += 1
            print(f"✅ {file.name} ({len(text)} chars)")
        else:
            print(f"⚠️ {file.name}: текст не найден")
    except Exception as e:
        print(f"❌ {file.name}: {e}")

print(f"\nВсего изображений: {count}")