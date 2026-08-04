import pdfplumber
import pytesseract
from PIL import Image

# Укажи путь к Tesseract (если установлен)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH = PROJECT_ROOT / "Storage" / "chroma"
_instance = None


def get_memory_indexer():
    global _instance
    if _instance is None:
        _instance = MemoryIndexer()
    return _instance


class MemoryIndexer:
    def index_file(self, path: str) -> bool:
        """Индексирует файл любого типа."""
        path = Path(path)
        ext = path.suffix.lower()
        content = ""

        try:
            if ext in [
                ".md",
                ".txt",
                ".py",
                ".json",
                ".yaml",
                ".yml",
                ".html",
                ".css",
                ".js",
                ".csv",
                ".xml",
                ".log",
            ]:
                content = path.read_text(encoding="utf-8", errors="ignore")

            elif ext == ".docx":
                import docx

                doc = docx.Document(path)
                content = "\n".join([p.text for p in doc.paragraphs])

            elif ext == ".pdf":
                with pdfplumber.open(path) as pdf:
                    content = "\n".join(
                        [page.extract_text() or "" for page in pdf.pages]
                    )

            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
                image = Image.open(path)
                content = pytesseract.image_to_string(image, lang="rus+eng")

            else:
                return False

            if content and len(content.strip()) > 10:
                self.add_note(str(path), content[:5000])
                print(f"✅ {path.name} ({len(content)} chars)")
                return True
            return False

        except Exception as e:
            print(f"❌ {path.name}: {e}")
            return False

    def index_all_files(self, root_path: str = "."):
        """Индексирует все поддерживаемые файлы."""
        root = Path(root_path)
        extensions = [
            ".md",
            ".txt",
            ".py",
            ".json",
            ".yaml",
            ".yml",
            ".html",
            ".css",
            ".js",
            ".csv",
            ".xml",
            ".log",
            ".docx",
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
        ]
        count = 0
        for ext in extensions:
            for file in root.rglob(f"*{ext}"):
                if self.index_file(str(file)):
                    count += 1
        return count

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._init_collections()

    def _init_collections(self):
        self.sessions = self.client.get_or_create_collection(
            name="sessions", embedding_function=self.embedding_fn
        )
        self.decisions = self.client.get_or_create_collection(
            name="decisions", embedding_function=self.embedding_fn
        )
        self.notes = self.client.get_or_create_collection(
            name="notes", embedding_function=self.embedding_fn
        )

    def add_session(self, session_id: str, messages: list):
        text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        self.sessions.add(
            ids=[session_id],
            documents=[text],
            metadatas=[{"type": "session", "count": len(messages)}],
        )

    def add_note(self, path: str, content: str):
        note_id = f"note_{Path(path).stem}"
        self.notes.add(
            ids=[note_id],
            documents=[content],
            metadatas=[{"path": path, "type": "note"}],
        )

    def add_decision(self, context: str, decision: str, reason: str):
        text = f"Context: {context}\nDecision: {decision}\nReason: {reason}"
        self.decisions.add(
            ids=[f"dec_{len(self.decisions.get()['ids'])}"],
            documents=[text],
            metadatas=[{"type": "decision"}],
        )

    def search(self, query: str, collection: str = "notes", n: int = 3) -> list:
        coll = getattr(self, collection)
        results = coll.query(query_texts=[query], n_results=n)
        return results

    def remember(self, query: str) -> str:
        results = []
        for name in ["sessions", "decisions", "notes"]:
            coll = getattr(self, name)
            try:
                r = coll.query(query_texts=[query], n_results=2)
                if r.get("documents") and r["documents"][0]:
                    for doc in r["documents"][0]:
                        results.append(f"[{name}]\n{doc[:300]}")
            except:
                pass
        return "\n\n---\n\n".join(results) if results else "Nothing found."


if __name__ == "__main__":
    indexer = MemoryIndexer()
    print("Memory indexer ready")
    print("Collections:", indexer.client.list_collections())
