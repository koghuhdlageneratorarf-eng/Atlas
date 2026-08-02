# fix_api.py
with open("api_openai.py", "r", encoding="utf-8") as f:
    content = f.read()

# Убираем определение agent_type
old_block = """    # Определяем агента по model name
    agent_type = "executive"
    if req.model == "atlas-developer":
        agent_type = "developer"
    elif req.model == "atlas-brief":
        agent_type = "brief"
    
    # Извлекаем текст запроса (последнее user-сообщение)"""

new_block = """    # Извлекаем текст запроса (последнее user-сообщение)"""

content = content.replace(old_block, new_block)

# Убираем agent_type из вызова
content = content.replace(
    "agents[session_id] = AtlasCodeAgent(session_name=session_id, agent_type=agent_type)",
    "agents[session_id] = AtlasCodeAgent(session_name=session_id)",
)

with open("api_openai.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed api_openai.py")
