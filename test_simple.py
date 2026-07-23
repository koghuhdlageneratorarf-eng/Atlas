import sys
sys.path.insert(0, '.')
from atlas_core.agent import _load_env
from Config.llm_client import ask_llm
_load_env()

# Простой prompt без сложных инструкций
messages = [
    {'role':'system','content':'You are a coding assistant. When user asks to do something with files, reply in this exact JSON format: {"tools":[{"name":"TOOL_NAME","args":{}}],"response":"text"}. Available tools: list_directory, read_file, write_file.'},
    {'role':'user','content':'Show me files in current directory'}
]
r = ask_llm(messages, agent='executive')
print(r)
