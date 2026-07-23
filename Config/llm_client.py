"""Atlas Brain Router — LLM client with Graphify context + multi-provider fallback."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sys
import json
import time
import requests
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Graphify bridge
sys.path.insert(0, str(Path(__file__).parent.parent / "Brain"))
try:
    from graphify_bridge import get_context as graphify_context
    GRAPHIFY_AVAILABLE = True
except ImportError:
    GRAPHIFY_AVAILABLE = False

# Load env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Config
CONFIG_PATH = Path(__file__).parent / "models.yaml"
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        MODELS_CONFIG = yaml.safe_load(f)
else:
    MODELS_CONFIG = {}

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:3b"

# API keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
CLOUDFLARE_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# Provider endpoints
PROVIDERS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
        "key": GEMINI_KEY,
        "header": lambda k: {"x-goog-api-key": k},
        "payload": lambda msg: {"contents": [{"role": m["role"], "parts": [{"text": m["content"]}]} for m in msg], "generationConfig": {"temperature": 0.3}},
        "extract": lambda r: r["candidates"][0]["content"]["parts"][0]["text"]
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key": CEREBRAS_KEY,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {"model": "llama-4-scout-17b-16e-instruct", "messages": msg, "temperature": 0.3},
        "extract": lambda r: r["choices"][0]["message"]["content"]
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_KEY,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {"model": "llama-3.3-70b-versatile", "messages": msg, "temperature": 0.3},
        "extract": lambda r: r["choices"][0]["message"]["content"]
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": OPENROUTER_KEY,
        "header": lambda k: {"Authorization": f"Bearer {k}", "HTTP-Referer": "https://atlas.local", "X-Title": "Atlas"},
        "payload": lambda msg: {"model": "openrouter/auto", "messages": msg, "temperature": 0.3},
        "extract": lambda r: r["choices"][0]["message"]["content"]
    },
    "cloudflare": {
        "url": f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID','')}/ai/run/@cf/meta/llama-3.1-8b-instruct",
        "key": CLOUDFLARE_TOKEN,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {"messages": msg},
        "extract": lambda r: r["result"]["response"]
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
        "key": HF_TOKEN,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {"inputs": msg[-1]["content"], "parameters": {"max_new_tokens": 1024}},
        "extract": lambda r: r[0]["generated_text"] if isinstance(r, list) else r.get("generated_text", "")
    }
}

def _call_provider(name: str, messages: list, timeout: int = 60) -> str:
    """Вызвать конкретного провайдера."""
    cfg = PROVIDERS[name]
    if not cfg["key"]:
        raise ValueError(f"No API key for {name}")

    headers = cfg["header"](cfg["key"])
    headers["Content-Type"] = "application/json"

    url = cfg["url"]
    if name == "gemini":
        url = f"{url}?key={cfg['key']}"
        headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=cfg["payload"](messages), timeout=timeout)
    response.raise_for_status()
    return cfg["extract"](response.json())

def _call_ollama(messages: list, model: str = DEFAULT_MODEL, timeout: int = 120) -> str:
    """Fallback на локальную Ollama."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": model, "messages": messages, "stream": False},
        timeout=timeout
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

def ask_llm(messages: list, agent: str = "developer", use_graph: bool = True, timeout: int = 120) -> str:
    """
    Умный роутер с авто-контекстом из Graphify.
    
    Args:
        messages: список сообщений
        agent: "executive", "brief", "developer", "self_upgrade"
        use_graph: подгружать ли контекст из Graphify
    """
    # 1. Подгружаем контекст из Graphify
    if use_graph and GRAPHIFY_AVAILABLE:
        task = messages[-1].get("content", "") if messages else ""
        context = graphify_context(task, max_nodes=12)
        if context:
            context_msg = {
                "role": "system",
                "content": f"=== КОНТЕКСТ ПРОЕКТА ATLAS ===\n{context}\n=== КОНЕЦ КОНТЕКСТА ===\n\nИспользуй эту информацию. Не предлагай создавать файлы/папки, которые уже существуют."
            }
            new_messages = []
            has_system = False
            for m in messages:
                if m["role"] == "system" and not has_system:
                    new_messages.append(m)
                    new_messages.append(context_msg)
                    has_system = True
                else:
                    new_messages.append(m)
            if not has_system:
                new_messages = [context_msg] + messages
            messages = new_messages

    # 2. Определяем приоритеты провайдеров для агента
    priorities = MODELS_CONFIG.get("agents", {}).get(agent, ["ollama"])
    ollama_models = MODELS_CONFIG.get("ollama_models", {})

    last_error = None
    for provider in priorities:
        if provider == "ollama":
            try:
                model = ollama_models.get(agent, DEFAULT_MODEL)
                print(f"[Brain] {agent} → Ollama ({model})")
                return _call_ollama(messages, model, timeout)
            except Exception as e:
                last_error = e
                print(f"[!] Ollama failed: {e}")
                continue

        if provider in PROVIDERS:
            try:
                print(f"[Brain] {agent} → {provider.upper()}")
                return _call_provider(provider, messages, timeout)
            except Exception as e:
                last_error = e
                print(f"[!] {provider} failed: {e}")
                continue

    raise RuntimeError(f"All providers failed. Last error: {last_error}")

def diagnose():
    """Проверяет всех провайдеров."""
    print("=" * 50)
    print("ATLAS BRAIN DIAGNOSTIC")
    print("=" * 50)

    print(f"\n[Graphify] Available: {GRAPHIFY_AVAILABLE}")
    if GRAPHIFY_AVAILABLE:
        from graphify_bridge import build_graph
        build_graph()
        ctx = graphify_context("skills web", max_nodes=5)
        print(f"Context sample:\n{ctx[:500]}...")

    print("\n[PROVIDERS]")
    for name, cfg in PROVIDERS.items():
        status = "✅ KEY OK" if cfg["key"] else "❌ NO KEY"
        print(f"  [{name.upper()}] {status}")

    print("\n[MODELS CONFIG]")
    if MODELS_CONFIG:
        print(f"  Agents: {list(MODELS_CONFIG.get('agents', {}).keys())}")
        print(f"  Ollama models: {MODELS_CONFIG.get('ollama_models', {})}")
    else:
        print("  ❌ models.yaml not found or empty")

    print("\n[OLLAMA]")
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  Models: {models}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test each provider
    test_msg = [{"role": "user", "content": "Say 'OK' only"}]
    print("\n[PROVIDER TESTS]")
    for name in PROVIDERS:
        if PROVIDERS[name]["key"]:
            try:
                start = time.time()
                result = _call_provider(name, test_msg, timeout=30)
                elapsed = time.time() - start
                print(f"  ✅ {name.upper()}: {result[:50]}... ({elapsed:.1f}s)")
            except Exception as e:
                print(f"  ❌ {name.upper()}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--test", choices=list(PROVIDERS.keys()) + ["ollama"])
    args = parser.parse_args()

    if args.diagnose:
        diagnose()
    elif args.test:
        msg = [{"role": "user", "content": "Привет, это тест Atlas Brain. Ответь кратко."}]
        if args.test == "ollama":
            print(_call_ollama(msg))
        else:
            print(_call_provider(args.test, msg))
    else:
        result = ask_llm(
            [{"role": "user", "content": "Какие skills доступны для создания сайтов?"}],
            agent="executive"
        )
        print(result)
