import sys
sys.path.insert(0, '.')
from atlas_core.agent import _parse_tool_response

t = '`json\n{\n  "thought": "test",\n  "tools": [{"name": "run_command", "args": {"cmd": "ls"}}],\n  "response": "ok"\n}\n`'
r = _parse_tool_response(t)
print('tools:', r.get('tools'))
