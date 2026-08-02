import re
from pathlib import Path

with open('atlas_core/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('SYSTEM_PROMPT = """')
end = content.find('"""', start + 20)
old_block = content[start:end+3]

new_block = '# Load SYSTEM_PROMPT from file for easy editing' + "`n" +
'_SYSTEM_PROMPT_PATH = Path(__file__).parent / "SYSTEM_PROMPT_mini.md"' + "`n" +
'if _SYSTEM_PROMPT_PATH.exists():' + "`n" +
'    SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")' + "`n" +
'else:' + "`n" +
'    SYSTEM_PROMPT = """You are Atlas Code Agent. Use tools. Reply ONLY in JSON format.' + "`n" +
'FORMAT: {"thought":"...","tools":[{"name":"TOOL","args":{}}],"response":"..."}' + "`n" +
'"""'

content = content.replace(old_block, new_block)

with open('atlas_core/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK: agent.py patched")