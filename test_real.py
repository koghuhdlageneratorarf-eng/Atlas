import sys
sys.path.insert(0, '.')
from atlas_core.agent import _parse_tool_response

raw = '`json\n{\n  "thought": "I need to list all files in the current directory.",\n  "tools": [\n    {\n      "name": "list_directory",\n      "args": {\n        "path": "."\n      }\n    }\n  ],\n  "response": "r"\n}\n`'
r = _parse_tool_response(raw)
print('tools:', r.get('tools'))
print('thought:', r.get('thought')[:50])
print('response:', r.get('response'))
