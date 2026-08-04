"""
Semantic Code Search — поиск по коду на основе смысла.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import chromadb
    from chromadb.utils import embedding_functions

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("[SemanticSearch] ChromaDB не установлен. Установи: pip install chromadb")


class SemanticSearch:
    def __init__(self, root_path: str = None, collection_name: str = "code"):
        if not HAS_CHROMADB:
            raise ImportError("ChromaDB не установлен")

        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.collection_name = collection_name
        self.persist_path = str(self.root / "Storage" / "chroma_semantic")

        # Создаём папку, если её нет
        Path(self.persist_path).mkdir(parents=True, exist_ok=True)

        # Новый API ChromaDB
        self.client = chromadb.PersistentClient(path=self.persist_path)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=self.embedding_fn
        )
        self._indexed = self.collection.count() > 0

    def index_file(self, filepath: Path) -> bool:
        if not filepath.exists():
            return False
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(filepath.relative_to(self.root))

            # Пропускаем файлы короче 10 символов (пустые или почти пустые)
            if len(content.strip()) < 10:
                return False

            # Разбиваем на чанки по 500 символов
            chunks = [content[i : i + 500] for i in range(0, len(content), 500)]
            # Фильтруем пустые чанки
            chunks = [c for c in chunks if c.strip()]
            if not chunks:
                return False

            ids = [f"{rel_path}_{i}" for i in range(len(chunks))]
            metadatas = [{"file": rel_path, "chunk": i} for i in range(len(chunks))]

            self.collection.add(ids=ids, documents=chunks, metadatas=metadatas)
            return True
        except Exception as e:
            print(f"  ❌ {filepath.name}: {e}")
            return False

    def index_project(self, extensions: list[str] = [".py", ".md", ".txt"]) -> int:
        print("[SemanticSearch] Индексация...")
        count = 0
        for ext in extensions:
            for file in self.root.rglob(f"*{ext}"):
                if "__pycache__" in str(file) or "Storage" in str(file):
                    continue
                if self.index_file(file):
                    count += 1
                    if count % 10 == 0:
                        print(f"  Индексировано: {count} файлов")
        self._indexed = True
        print(f"[SemanticSearch] Индексировано {count} файлов")
        return count

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        if not self._indexed:
            return []
        results = self.collection.query(query_texts=[query], n_results=n_results)
        if not results.get("documents"):
            return []
        output = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            output.append(
                {
                    "file": meta.get("file", "unknown"),
                    "content": doc[:200] + "..." if len(doc) > 200 else doc,
                }
            )
        return output

    def status(self) -> str:
        return f"Semantic Search\n─────────────────\nДокументов: {self.collection.count()}\nИндексировано: {'✅' if self._indexed else '❌'}"


if __name__ == "__main__":
    ss = SemanticSearch(str(Path(__file__).parent.parent.absolute()))
    print(ss.status())
    ss.index_project()
    print(ss.status())
    print("\nПоиск: 'runtime'")
    for r in ss.search("runtime", n_results=3):
        print(f"  {r['file']}: {r['content'][:80]}...")
