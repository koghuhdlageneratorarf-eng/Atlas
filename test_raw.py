import sys
sys.path.insert(0, '.')
from atlas_core.agent import _load_env
from Config.llm_client import ask_llm
_load_env()

messages = [
    {'role':'system','content':'You are Atlas Code Agent. Reply in JSON: {"thought":"t","tools":[{"name":"list_directory","args":{"path":"."}}],"response":"r"}'},
    {'role':'user','content':'Show files'}
]
r = ask_llm(messages, agent='executive')
print('---RAW---')
print(repr(r))
print('---END---')
