from memories.indexer import MemoryIndexer
from pathlib import Path
from PIL import Image
import pytesseract
import docx
import pdfplumber

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

idx = MemoryIndexer()
count = 0

# Все файлы в папке memories и подпапках
for file in Path("memories").rglob("*"):
    if not file.is_file():
        continue
    
    ext = file.suffix.lower()
    content = ""
    
    try:
        if ext in [".md", ".txt", ".py", ".json", ".yaml", ".yml", ".html", ".css", ".js", ".csv", ".xml", ".log"]:
            content = file.read_text(encoding='utf-8', errors='ignore')
        
        elif ext == ".docx":
            doc = docx.Document(file)
            content = "\n".join([p.text for p in doc.paragraphs])
        
        elif ext == ".pdf":
            with pdfplumber.open(file) as pdf:
                content = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            img = Image.open(file)
            content = pytesseract.image_to_string(img, lang="rus+eng")
        
        if content and len(content.strip()) > 10:
            idx.add_note(str(file), content[:5000])
            count += 1
            print(f"✅ {file.name} ({len(content)} chars)")
        elif content:
            print(f"⚠️ {file.name}: слишком короткий текст")
            
    except Exception as e:
        print(f"❌ {file.name}: {e}")

print(f"\nВсего файлов: {count}")