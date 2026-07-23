import sys
sys.path.insert(0, '.')
from atlas_core.agent import _parse_tool_response

text = '{"thought":"test","tools":[{"name":"list_directory","args":{"path":"."}}],"response":"ok"}'
r = _parse_tool_response(text)
print('tools:', r.get('tools'))
print('thought:', r.get('thought'))
