import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:3b"

def ask_llm(messages, model=None):
    use_model = model or DEFAULT_MODEL
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": use_model,
            "messages": messages,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]

if __name__ == "__main__":
    result = ask_llm([{"role": "user", "content": "Privet"}])
    print(result)
