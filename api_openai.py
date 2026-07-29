"""
api_openai.py - OpenAI-compatible API server for Atlas
Place in project root (next to main.py)

Run:
  cd C:/Users/diman/Atlas
  python api_openai.py

Open WebUI -> Settings -> Admin -> Connections -> Add OpenAI API:
  Base URL: http://localhost:8000/v1
  API Key: atlas-local (any string)
  Model: atlas-executive
"""
import os
import sys
import time
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import uvicorn

# ─── ATLAS IMPORTS (твоя текущая структура) ───
from atlas_core.agent import AtlasCodeAgent
from atlas_core.session import SessionManager
from atlas_core.context import ProjectContext
from atlas_core.tools import create_backup, run_command

app = FastAPI(title="Atlas AI OS API", version="11.2")

# CORS для Open WebUI (работает на другом порту)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── AGENT CACHE ───
agents: Dict[str, AtlasCodeAgent] = {}

ATLAS_MODELS = [
    {"id": "atlas-executive", "object": "model", "owned_by": "atlas"},
    {"id": "atlas-developer", "object": "model", "owned_by": "atlas"},
    {"id": "atlas-brief", "object": "model", "owned_by": "atlas"},
]

# ─── PYDANTIC MODELS ───
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "atlas-executive"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.3
    stream: Optional[bool] = False
    model_config = ConfigDict(extra="ignore")

# ─── ENDPOINTS ───

@app.get("/v1/models")
async def list_models():
    """Open WebUI запрашивает список моделей при подключении."""
    return {"object": "list", "data": ATLAS_MODELS}

@app.post("/v1/chat/completions")
async def chat_completion(req: ChatRequest):
    """
    Основной endpoint. Open WebUI шлёт сюда сообщения.
    Atlas выполняет Tool Use цикл и возвращает результат.
    """
    # Определяем агента
    agent_type = "executive"
    if req.model == "atlas-developer":
        agent_type = "developer"
    elif req.model == "atlas-brief":
        agent_type = "brief"

    # Извлекаем текст (последнее user-сообщение)
    user_messages = [m for m in req.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message")

    user_input = user_messages[-1].content

    # Слэш-команды Atlas
    if user_input.startswith("/"):
        return _handle_slash_command(user_input)

    # Session ID — stable для персистентности между запросами WebUI
    session_id = "webui_default"

    # Кэшируем агента
    if session_id not in agents:
        agents[session_id] = AtlasCodeAgent(session_name=session_id, agent_type=agent_type)

    agent = agents[session_id]

    # Tool Use цикл
    try:
        result = agent.process(user_input)
    except Exception as e:
        result = f"[Atlas Error] {str(e)}"

    # OpenAI-compatible response
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(str(req.messages)),
            "completion_tokens": len(result),
            "total_tokens": len(str(req.messages)) + len(result)
        }
    }

def _handle_slash_command(cmd: str) -> dict:
    """Обработка REPL-команд через API."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    result = ""
    if command == "/context":
        result = ProjectContext().get_tree()
    elif command == "/status":
        result = run_command("git status --short")
    elif command == "/diff":
        result = run_command("git diff --stat")
    elif command == "/backup":
        result = create_backup(arg or None)
    elif command == "/sessions":
        sessions = SessionManager().list_sessions()
        result = "\n".join([f"{s['id']}: {s['name']}" for s in sessions])
    elif command == "/help":
        result = """Atlas Commands:
/context — project tree
/status — git status  
/diff — git diff
/backup [name] — create backup
/sessions — list sessions
/help — this message"""
    else:
        result = f"Unknown: {command}. Use /help"

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "atlas-executive",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": result}, "finish_reason": "stop"}],
        "usage": {"total_tokens": len(result)}
    }

@app.get("/health")
async def health():
    return {"status": "ok", "version": "11.2", "agent": "atlas"}

# Legacy endpoints (без /v1)
@app.post("/chat/completions")
async def chat_legacy(req: ChatRequest):
    return await chat_completion(req)

@app.get("/models")
async def models_legacy():
    return await list_models()

if __name__ == "__main__":
    print("=" * 60)
    print("  ATLAS AI OS API Server v11.2")
    print("=" * 60)
    print("  Open WebUI Connection:")
    print("    Base URL: http://localhost:8000/v1")
    print("    API Key:  atlas-local")
    print("    Model:    atlas-executive")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
