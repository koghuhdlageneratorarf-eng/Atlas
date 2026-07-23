"""Graphify Bridge — адаптер между Atlas и Graphify knowledge graph."""
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).parent.parent
GRAPHIFY_OUT = BASE_DIR / "graphify-out"
GRAPH_JSON = GRAPHIFY_OUT / "graph.json"
GRAPH_REPORT = GRAPHIFY_OUT / "GRAPH_REPORT.md"

GRAPHIFY_EXE = r"C:\Users\diman\AppData\Local\Python\pythoncore-3.14-64\Scripts\graphify.exe"

class GraphifyBridge:
    def __init__(self):
        self._graph: Optional[Dict] = None
        self._report: Optional[str] = None

    def _needs_rebuild(self) -> bool:
        if not GRAPH_JSON.exists():
            return True
        graph_mtime = GRAPH_JSON.stat().st_mtime
        latest = 0
        for f in BASE_DIR.rglob("*"):
            if f.is_file() and ".git" not in str(f) and "graphify-out" not in str(f):
                try:
                    mtime = f.stat().st_mtime
                    if mtime > latest:
                        latest = mtime
                except:
                    pass
        return latest > graph_mtime

    def build(self, force: bool = False):
        if not force and not self._needs_rebuild():
            print("[Graphify] Граф актуален, пропускаю.")
            return

        print("[Graphify] Перестраиваю knowledge graph...")
        GRAPHIFY_OUT.mkdir(exist_ok=True)

        if not Path(GRAPHIFY_EXE).exists():
            print(f"[!] graphify.exe не найден: {GRAPHIFY_EXE}")
            self._build_fallback()
            return

        result = subprocess.run(
            [GRAPHIFY_EXE, ".", "--output", str(GRAPHIFY_OUT), "--code-only"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[!] Graphify ошибка: {result.stderr[:500]}")
            self._build_fallback()
        else:
            print("[Graphify] Граф построен.")
            self._load()

    def _build_fallback(self):
        print("[Graphify] Fallback: ручная индексация...")
        nodes = []
        edges = []

        for f in BASE_DIR.rglob("*.py"):
            rel = str(f.relative_to(BASE_DIR)).replace("\\", "/")
            parts = f.relative_to(BASE_DIR).parts
            nodes.append({
                "id": rel,
                "type": "file",
                "label": f.name,
                "community": parts[0] if parts else "root"
            })

        for node in nodes:
            fpath = BASE_DIR / node["id"]
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        parts = line.split()
                        if len(parts) >= 2:
                            target = parts[1].split(".")[0]
                            if not target.startswith(("os", "sys", "json", "time", "pathlib", "typing")):
                                for n in nodes:
                                    if target in n["label"].replace(".py", ""):
                                        edges.append({
                                            "source": node["id"],
                                            "target": n["id"],
                                            "relation": "imports",
                                            "confidence": "EXTRACTED"
                                        })
            except:
                pass

        self._graph = {"nodes": nodes, "edges": edges}
        GRAPHIFY_OUT.mkdir(exist_ok=True)
        GRAPH_JSON.write_text(json.dumps(self._graph, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self):
        if GRAPH_JSON.exists():
            self._graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        if GRAPH_REPORT.exists():
            self._report = GRAPH_REPORT.read_text(encoding="utf-8")

    def _read_json_safe(self, path: Path) -> dict:
        """Читает JSON с защитой от BOM."""
        try:
            # Сначала пробуем utf-8-sig (убирает BOM автоматически)
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except:
            # Fallback
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))

    def _get_skills_catalog(self) -> str:
        """Явно читает все skill.json и формирует каталог."""
        lines = ["=== ДОСТУПНЫЕ SKILLS ==="]
        skills_dir = BASE_DIR / "Skills"

        if skills_dir.exists():
            for skill_folder in sorted(skills_dir.iterdir()):
                if skill_folder.is_dir():
                    skill_json = skill_folder / "skill.json"
                    if skill_json.exists():
                        try:
                            data = self._read_json_safe(skill_json)
                            name = data.get("name", skill_folder.name)
                            desc = data.get("description", "Нет описания")
                            tech = data.get("technologies", "—")
                            entry = data.get("entry_point", "—")
                            lines.append(f"\n  • {name}")
                            lines.append(f"    Описание: {desc}")
                            lines.append(f"    Технологии: {tech}")
                            lines.append(f"    Entry point: {entry}")
                        except Exception as e:
                            lines.append(f"\n  • {skill_folder.name}: (ошибка чтения: {e})")
                    else:
                        tmpl = skill_folder / "template.html"
                        if tmpl.exists():
                            lines.append(f"\n  • {skill_folder.name}: HTML-шаблон")
                        else:
                            lines.append(f"\n  • {skill_folder.name}: (папка без skill.json)")

        return "\n".join(lines)

    def _get_agents_catalog(self) -> str:
        """Формирует каталог агентов."""
        lines = ["=== АГЕНТЫ ATLAS ==="]
        agents_dir = BASE_DIR / "Agents"
        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.py")):
                if f.name.startswith("__"):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    doc = ""
                    if '"""' in content:
                        parts = content.split('"""')
                        if len(parts) >= 3:
                            doc = parts[1].strip()[:100]
                    lines.append(f"  • {f.name}: {doc or 'агент'}")
                except:
                    lines.append(f"  • {f.name}")
        return "\n".join(lines)

    def get_context(self, query: str, max_nodes: int = 15) -> str:
        """Возвращает релевантный контекст из графа + каталоги для LLM."""
        if self._graph is None:
            self._load()
            if self._graph is None:
                return ""

        query_lower = query.lower()
        nodes = self._graph.get("nodes", [])
        edges = self._graph.get("edges", [])

        skills_catalog = ""
        if any(word in query_lower for word in ["skill", "скилл", "шаблон", "template", "landing", "сайт", "web"]):
            skills_catalog = self._get_skills_catalog()

        agents_catalog = ""
        if any(word in query_lower for word in ["agent", "агент", "executive", "developer", "brief"]):
            agents_catalog = self._get_agents_catalog()

        relevant = []
        for node in nodes:
            score = 0
            label = str(node.get("label", "")).lower()
            community_raw = node.get("community", "")
            community = str(community_raw).lower() if community_raw is not None else ""

            if any(word in label for word in query_lower.split()):
                score += 10
            if any(word in community for word in query_lower.split()):
                score += 5
            if "skill" in query_lower and "skill" in label:
                score += 8
            if "agent" in query_lower and "agent" in label:
                score += 8
            if "developer" in query_lower and "developer" in label:
                score += 8

            if score > 0:
                relevant.append((score, node))

        relevant.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [n for _, n in relevant[:max_nodes]]

        top_ids = {n["id"] for n in top_nodes}
        neighbor_edges = []
        for edge in edges:
            if edge.get("source") in top_ids or edge.get("target") in top_ids:
                neighbor_edges.append(edge)
                for node in nodes:
                    if node["id"] == edge.get("source") or node["id"] == edge.get("target"):
                        if node not in top_nodes:
                            top_nodes.append(node)

        lines = []
        if skills_catalog:
            lines.append(skills_catalog)
            lines.append("")
        if agents_catalog:
            lines.append(agents_catalog)
            lines.append("")

        lines.append("=== ATLAS PROJECT STRUCTURE (from Graphify) ===")
        lines.append("")

        communities = {}
        for node in top_nodes:
            comm_raw = node.get("community", "other")
            comm = str(comm_raw) if comm_raw is not None else "other"
            if comm not in communities:
                communities[comm] = []
            communities[comm].append(node)

        for comm, comm_nodes in sorted(communities.items()):
            lines.append(f"📁 {comm}/")
            for node in comm_nodes[:5]:
                lines.append(f"  • {node.get('label', node['id'])} ({node.get('type', 'file')})")
            if len(comm_nodes) > 5:
                lines.append(f"  ... и ещё {len(comm_nodes)-5}")
            lines.append("")

        if neighbor_edges:
            lines.append("=== КЛЮЧЕВЫЕ СВЯЗИ ===")
            for edge in neighbor_edges[:10]:
                lines.append(f"  {edge.get('source', '?')} --[{edge.get('relation', '?')}]--> {edge.get('target', '?')}")

        if self._report:
            lines.append("")
            lines.append("=== PROJECT WIKI ===")
            lines.append(self._report[:1500])
            lines.append("...")

        return "\n".join(lines)

    def find_skill(self, skill_name: str) -> Optional[Dict]:
        if self._graph is None:
            self._load()
        for node in self._graph.get("nodes", []):
            if skill_name.lower() in str(node.get("label", "")).lower():
                return node
        return None

    def get_file_neighbors(self, file_path: str) -> List[str]:
        if self._graph is None:
            self._load()
        neighbors = []
        for edge in self._graph.get("edges", []):
            if edge.get("source") == file_path:
                neighbors.append(f"{edge.get('relation')} -> {edge.get('target')}")
            elif edge.get("target") == file_path:
                neighbors.append(f"{edge.get('source')} -> {edge.get('relation')}")
        return neighbors

_bridge = GraphifyBridge()

def build_graph(force: bool = False):
    _bridge.build(force=force)

def get_context(query: str, max_nodes: int = 15) -> str:
    return _bridge.get_context(query, max_nodes)

def find_skill(skill_name: str) -> Optional[Dict]:
    return _bridge.find_skill(skill_name)

def get_file_neighbors(file_path: str) -> List[str]:
    return _bridge.get_file_neighbors(file_path)

if __name__ == "__main__":
    build_graph(force=True)
    print(get_context("skills web", max_nodes=10))
