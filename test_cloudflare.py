# test_cloudflare.py
import sys
sys.path.insert(0, "C:/Users/diman/Atlas")
from Config.llm_client import _call_provider

msg = [{"role": "user", "content": "Say OK"}]
try:
    result = _call_provider("cloudflare", msg, timeout=30)
    print(f"Type: {type(result)}")
    print(f"Result: {result[:200] if isinstance(result, str) else result}")
except Exception as e:
    print(f"Error: {e}")