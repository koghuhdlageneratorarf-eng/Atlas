     1	# PATCH: agent.py changes for qwen3-coder-next
     2	# ==============================================
     3	# Apply these changes to atlas_core/agent.py
     4	
     5	## CHANGE 1: Update OLLAMA_MODEL default
     6	# In _load_env() or wherever model is set:
     7	- OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")
     8	+ OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-coder-next")
     9	
    10	## CHANGE 2: Use Function Calling API instead of JSON parsing
    11	# Qwen3-Coder-Next supports native function calling via Ollama API.
    12	# Replace _call_llm() or ask_llm() to use tools parameter.
    13	
    14	# OLD (JSON parsing):
    15	def _call_llm(messages, temperature=0.7):
    16	    response = ask_llm(messages, agent="developer", temperature=temperature)
    17	    return _parse_tool_response(response)
    18	
    19	# NEW (Function Calling):
    20	def _call_llm(messages, tools=None):
    21	    if tools:
    22	        # Use Ollama API with tools parameter
    23	        response = ollama.chat(
    24	            model=OLLAMA_MODEL,
    25	            messages=messages,
    26	            tools=tools,  # Native function calling!
    27	            options={"temperature": 1.0}  # Qwen3 recommends temp=1.0
    28	        )
    29	        return response["message"].get("tool_calls", [])
    30	    else:
    31	        response = ollama.chat(
    32	            model=OLLAMA_MODEL,
    33	            messages=messages,
    34	            options={"temperature": 1.0}
    35	        )
    36	        return response["message"]["content"]
    37	
    38	## CHANGE 3: Update SYSTEM_PROMPT path
    39	# In agent.py:
    40	- SYSTEM_PROMPT = open("Config/system_prompt.txt").read()
    41	+ SYSTEM_PROMPT = open("atlas_core/SYSTEM_PROMPT_v2.0_qwen3.md").read()
    42	
    43	## CHANGE 4: Remove temperature workaround
    44	# In llm_client.py or wherever temperature causes crash:
    45	- if provider == "ollama":
    46	-     data["options"] = {"temperature": temperature}  # CRASHES!
    47	+ if provider == "ollama":
    48	+     data["options"] = {}  # Qwen3 uses default temp=1.0
    49	
    50	## CHANGE 5: Increase context window awareness
    51	# Qwen3 has 256K context — Atlas can send much more code:
    52	- MAX_CONTEXT = 8000  # tokens
    53	+ MAX_CONTEXT = 32000  # tokens (safe for 256K)
    54	
    55	## CHANGE 6: Add non-thinking mode hint
    56	# In process() or _call_llm():
    57	+ messages.insert(0, {
    58	+     "role": "system",
    59	+     "content": "Reply in non-thinking mode. Use tools directly."
    60	+ })
    61	