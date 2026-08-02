"""Atlas Brain Router — LLM client with Graphify context + multi-provider fallback."""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
import json
import time
from pathlib import Path

import requests
import yaml
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
print(f"[DEBUG] Looking for .env at: {env_path}")
print(f"[DEBUG] .env exists: {env_path.exists()}")
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(
        f"[DEBUG] OPENROUTER_KEY loaded: {'yes' if os.getenv('OPENROUTER_API_KEY') else 'no'}"
    )
    print(f"[DEBUG] GROQ_KEY loaded: {'yes' if os.getenv('GROQ_API_KEY') else 'no'}")

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
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "key": GEMINI_KEY,
        "header": lambda k: {"x-goog-api-key": k},
        "payload": lambda msg: {
            "contents": [
                {"role": m["role"], "parts": [{"text": m["content"]}]} for m in msg
            ],
            "generationConfig": {"temperature": 0.3},
        },
        "extract": lambda r: r["candidates"][0]["content"]["parts"][0]["text"],
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key": CEREBRAS_KEY,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {
            "model": "llama-3.1-8b",
            "messages": msg,
            "temperature": 0.3,
        },
        "extract": lambda r: r["choices"][0]["message"]["content"],
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_KEY,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {
            "model": "llama-3.3-70b-versatile",
            "messages": msg,
            "temperature": 0.3,
        },
        "extract": lambda r: r["choices"][0]["message"]["content"],
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": OPENROUTER_KEY,
        "header": lambda k: {
            "Authorization": f"Bearer {k}",
            "HTTP-Referer": "https://atlas.local",
            "X-Title": "Atlas",
        },
        "payload": lambda msg: {
            "model": "openrouter/auto",
            "messages": msg,
            "temperature": 0.3,
        },
        "extract": lambda r: r["choices"][0]["message"]["content"],
    },
    "cloudflare": {
        "url": f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID','')}/ai/run/@cf/meta/llama-3.1-8b-instruct",
        "key": CLOUDFLARE_TOKEN,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {"messages": msg},
        "extract": lambda r: r["result"]["response"],
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
        "key": HF_TOKEN,
        "header": lambda k: {"Authorization": f"Bearer {k}"},
        "payload": lambda msg: {
            "inputs": msg[-1]["content"],
            "parameters": {"max_new_tokens": 1024},
        },
        "extract": lambda r: (
            r[0]["generated_text"]
            if isinstance(r, list)
            else r.get("generated_text", "")
        ),
    },
}


def _call_provider(name: str, messages: list, timeout: int = 60) -> str:
    """Call a specific provider."""
    cfg = PROVIDERS[name]
    if not cfg["key"]:
        raise ValueError(f"No API key for {name}")

    headers = cfg["header"](cfg["key"])
    headers["Content-Type"] = "application/json"

    url = cfg["url"]
    if name == "gemini":
        url = f"{url}?key={cfg['key']}"
        headers = {"Content-Type": "application/json"}

    response = requests.post(
        url, headers=headers, json=cfg["payload"](messages), timeout=timeout
    )
    response.raise_for_status()
    result = cfg["extract"](response.json())
    if isinstance(result, dict):
        result = json.dumps(result, ensure_ascii=False)
    return result


def _compress_messages(messages: list, max_chars: int = 6000) -> list:
    """Compress context for 3b models."""
    total = sum(len(m.get("content", "")) for m in messages)
    if total <= max_chars:
        return messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]
    return system_msgs + other_msgs[-3:]


def _call_ollama(messages: list, model: str = DEFAULT_MODEL, timeout: int = 120) -> str:
    """Ollama with JSON format guarantee."""
    compressed = _compress_messages(messages)
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": compressed,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 2048},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def _inject_graphify_context(messages: list, task: str = "") -> list:
    """
    Inject Graphify context into the LAST user message instead of adding a system message.
    This preserves the single-system-message pattern that works reliably with all models.
    """
    if not GRAPHIFY_AVAILABLE or not task:
        return messages

    context = graphify_context(task, max_nodes=10)
    if not context:
        return messages

    context_block = f"\n=== PROJECT CONTEXT ===\n{context}\n=== END CONTEXT ===\nUse this info. Don't create files/folders that already exist."

    # Find last user message and append context
    new_messages = []
    last_user_idx = -1
    for i, m in enumerate(messages):
        if m["role"] == "user":
            last_user_idx = i

    for i, m in enumerate(messages):
        if i == last_user_idx and last_user_idx >= 0:
            new_messages.append(
                {"role": "user", "content": m["content"] + "\n" + context_block}
            )
        else:
            new_messages.append(m)

    return new_messages


def ask_llm(
    messages: list, agent: str = "developer", use_graph: bool = True, timeout: int = 120
) -> str:
    """
    Smart router with Graphify context injected into user message (not system).

    Args:
        messages: list of messages
        agent: "executive", "brief", "developer", "self_upgrade"
        use_graph: whether to load Graphify context
    """
    # 1. Inject Graphify context into last user message (NOT as system message)
    if use_graph and GRAPHIFY_AVAILABLE:
        task = messages[-1].get("content", "") if messages else ""
        messages = _inject_graphify_context(messages, task)

    # 2. Provider priorities for agent
    priorities = MODELS_CONFIG.get("agents", {}).get(agent, ["ollama"])
    ollama_models = MODELS_CONFIG.get("ollama_models", {})

    last_error = None
    for provider in priorities:
        if provider == "ollama":
            try:
                model = ollama_models.get(agent, DEFAULT_MODEL)
                print(f"[Brain] {agent} -> Ollama ({model})")
                return _call_ollama(messages, model, timeout)
            except Exception as e:
                last_error = e
                print(f"[!] Ollama failed: {e}")
                continue

        if provider in PROVIDERS:
            try:
                print(f"[Brain] {agent} -> {provider.upper()}")
                return _call_provider(provider, messages, timeout)
            except Exception as e:
                last_error = e
                print(f"[!] {provider} failed: {e}")
                continue

    raise RuntimeError(f"All providers failed. Last error: {last_error}")


def diagnose():
    """Check all providers."""
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
        status = "OK" if cfg["key"] else "NO KEY"
        print(f"  [{name.upper()}] {status}")

    print("\n[MODELS CONFIG]")
    if MODELS_CONFIG:
        print(f"  Agents: {list(MODELS_CONFIG.get('agents', {}).keys())}")
        print(f"  Ollama models: {MODELS_CONFIG.get('ollama_models', {})}")
    else:
        print("  models.yaml not found or empty")

    print("\n[OLLAMA]")
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  Models: {models}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test each provider
    test_msg = [
        {"role": "system", "content": "You are Atlas."},
        {"role": "user", "content": "Say 'OK' only"},
    ]
    print("\n[PROVIDER TESTS]")
    for name in PROVIDERS:
        if PROVIDERS[name]["key"]:
            try:
                start = time.time()
                result = _call_provider(name, test_msg, timeout=30)
                elapsed = time.time() - start
                print(f"  OK {name.upper()}: {result[:50]}... ({elapsed:.1f}s)")
            except Exception as e:
                print(f"  FAIL {name.upper()}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--test", choices=list(PROVIDERS.keys()) + ["ollama"])
    args = parser.parse_args()

    if args.diagnose:
        diagnose()
    elif args.test:
        msg = [
            {"role": "system", "content": "You are Atlas coding agent."},
            {"role": "user", "content": "Say 'OK' only"},
        ]
        if args.test == "ollama":
            print(_call_ollama(msg))
        else:
            print(_call_provider(args.test, msg))
    else:
        result = ask_llm(
            [
                {
                    "role": "user",
                    "content": "What skills are available for building websites?",
                }
            ],
            agent="executive",
        )
        print(result)
