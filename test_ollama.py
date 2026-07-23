import sys
sys.path.insert(0, '.')
from atlas_core.agent import _load_env
from Config.llm_client import ask_llm
_load_env()
r = ask_llm([{'role':'system','content':'You are Atlas Code Agent. Reply with JSON only.'},{'role':'user','content':'List files in current directory using tool list_directory'}], agent='executive')
print('--- RAW RESPONSE ---')
print(r)
print('--- END ---')
