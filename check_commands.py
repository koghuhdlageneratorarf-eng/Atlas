import re

content = open("atlas_core/agent.py", "r", encoding="utf-8").read()
commands = re.findall(r'elif command == "(.*?)":', content)
print("Команды:", commands)
