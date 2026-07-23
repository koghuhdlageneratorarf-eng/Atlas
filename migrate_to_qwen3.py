     1	#!/usr/bin/env python3
     2	"""
     3	ATLAS MIGRATION SCRIPT: qwen2.5-coder:3b → qwen3-coder-next
     4	============================================================
     5	Запускать из корня проекта Atlas.
     6	
     7	Что делает:
     8	1. Проверяет наличие Ollama
     9	2. Скачивает qwen3-coder-next (если нет)
    10	3. Тестирует базовый ответ
    11	4. Тестирует JSON-формат Tool Use
    12	5. Обновляет .env (OLLAMA_MODEL)
    13	6. Создаёт бэкап старого .env
    14	"""
    15	
    16	import os
    17	import sys
    18	import subprocess
    19	import json
    20	import time
    21	
    22	# === КОНФИГУРАЦИЯ ===
    23	NEW_MODEL = "qwen3-coder-next"
    24	OLD_MODEL = "qwen2.5-coder:3b"
    25	ENV_FILE = ".env"
    26	ENV_BACKUP = ".env.backup.qwen2.5"
    27	
    28	# === ЦВЕТА ===
    29	GREEN = "\033[92m"
    30	RED = "\033[91m"
    31	YELLOW = "\033[93m"
    32	BLUE = "\033[94m"
    33	RESET = "\033[0m"
    34	
    35	def log(msg, color=RESET):
    36	    print(f"{color}[Atlas Migration]{RESET} {msg}")
    37	
    38	def run_cmd(cmd, timeout=60):
    39	    """Выполнить команду с таймаутом."""
    40	    try:
    41	        result = subprocess.run(
    42	            cmd, shell=True, capture_output=True, text=True, timeout=timeout
    43	        )
    44	        return result.returncode == 0, result.stdout, result.stderr
    45	    except subprocess.TimeoutExpired:
    46	        return False, "", "Timeout"
    47	
    48	def check_ollama():
    49	    """Проверить, что Ollama установлен и работает."""
    50	    log("Проверка Ollama...", BLUE)
    51	    ok, out, err = run_cmd("ollama --version")
    52	    if not ok:
    53	        log(f"Ollama не найден! Установите: https://ollama.com", RED)
    54	        return False
    55	    log(f"Ollama найден: {out.strip()}", GREEN)
    56	    return True
    57	
    58	def check_model():
    59	    """Проверить, скачана ли модель."""
    60	    log(f"Проверка модели {NEW_MODEL}...", BLUE)
    61	    ok, out, err = run_cmd(f"ollama list | grep {NEW_MODEL}")
    62	    if ok:
    63	        log(f"Модель {NEW_MODEL} уже скачана", GREEN)
    64	        return True
    65	    log(f"Модель не найдена. Скачиваем...", YELLOW)
    66	    return False
    67	
    68	def pull_model():
    69	    """Скачать модель."""
    70	    log(f"Скачивание {NEW_MODEL}...", BLUE)
    71	    log("Это может занять 5-15 минут (3.8 GB)...", YELLOW)
    72	    ok, out, err = run_cmd(f"ollama pull {NEW_MODEL}", timeout=900)
    73	    if not ok:
    74	        log(f"Ошибка скачивания: {err}", RED)
    75	        return False
    76	    log(f"Модель {NEW_MODEL} скачана!", GREEN)
    77	    return True
    78	
    79	def test_basic():
    80	    """Тест 1: Базовый ответ."""
    81	    log("Тест 1: Базовый ответ...", BLUE)
    82	    prompt = "Say hello in one word."
    83	    ok, out, err = run_cmd(
    84	        f'ollama run {NEW_MODEL} -- "{prompt}"', timeout=30
    85	    )
    86	    if not ok:
    87	        log(f"Базовый тест провален: {err}", RED)
    88	        return False
    89	    log(f"Ответ: {out.strip()}", GREEN)
    90	    return True
    91	
    92	def test_json_tool_use():
    93	    """Тест 2: JSON-формат с инструментами."""
    94	    log("Тест 2: JSON Tool Use...", BLUE)
    95	
    96	    system_prompt = """You are Atlas Code Agent. Reply ONLY in JSON format.
    97	Available tools: list_directory, read_file, write_file, edit_file, run_command, search_files.
    98	
    99	Format:
   100	{
   101	  "thought": "your reasoning",
   102	  "tools": [{"name": "tool_name", "args": {"key": "value"}}],
   103	  "response": "human-readable response"
   104	}
   105	
   106	Task: List files in current directory."""
   107	
   108	    ok, out, err = run_cmd(
   109	        f'ollama run {NEW_MODEL} -- "{system_prompt}"', timeout=30
   110	    )
   111	    if not ok:
   112	        log(f"JSON тест провален: {err}", RED)
   113	        return False
   114	
   115	    # Пытаемся распарсить JSON
   116	    try:
   117	        # Очистка от markdown
   118	        cleaned = out.strip()
   119	        if cleaned.startswith("```json"):
   120	            cleaned = cleaned[7:]
   121	        if cleaned.endswith("```"):
   122	            cleaned = cleaned[:-3]
   123	        cleaned = cleaned.strip()
   124	
   125	        data = json.loads(cleaned)
   126	        if "tools" in data:
   127	            log(f"✅ JSON Tool Use работает! tools={data['tools']}", GREEN)
   128	            return True
   129	        else:
   130	            log(f"⚠️ JSON есть, но нет поля 'tools': {cleaned[:200]}", YELLOW)
   131	            return False
   132	    except json.JSONDecodeError:
   133	        log(f"❌ Не JSON: {out[:200]}", RED)
   134	        return False
   135	
   136	def test_function_calling():
   137	    """Тест 3: Нативный function calling (если поддерживается)."""
   138	    log("Тест 3: Function Calling...", BLUE)
   139	
   140	    # Qwen3-Coder-Next поддерживает function calling через Ollama
   141	    # Проверяем через API
   142	    import urllib.request
   143	
   144	    payload = json.dumps({
   145	        "model": NEW_MODEL,
   146	        "messages": [
   147	            {"role": "system", "content": "You are a helpful coding assistant."},
   148	            {"role": "user", "content": "List files in current directory"}
   149	        ],
   150	        "tools": [
   151	            {
   152	                "type": "function",
   153	                "function": {
   154	                    "name": "list_directory",
   155	                    "description": "List files in a directory",
   156	                    "parameters": {
   157	                        "type": "object",
   158	                        "properties": {
   159	                            "path": {"type": "string", "description": "Directory path"}
   160	                        },
   161	                        "required": ["path"]
   162	                    }
   163	                }
   164	            }
   165	        ],
   166	        "stream": False
   167	    }).encode()
   168	
   169	    try:
   170	        req = urllib.request.Request(
   171	            "http://localhost:11434/api/chat",
   172	            data=payload,
   173	            headers={"Content-Type": "application/json"},
   174	            method="POST"
   175	        )
   176	        with urllib.request.urlopen(req, timeout=30) as resp:
   177	            result = json.loads(resp.read().decode())
   178	            msg = result.get("message", {})
   179	            if "tool_calls" in msg:
   180	                log(f"✅ Function Calling работает! tool_calls={msg['tool_calls']}", GREEN)
   181	                return True
   182	            else:
   183	                log(f"⚠️ Нет tool_calls в ответе", YELLOW)
   184	                return False
   185	    except Exception as e:
   186	        log(f"⚠️ Ollama API недоступен ({e}). Function calling не проверен.", YELLOW)
   187	        return False
   188	
   189	def update_env():
   190	    """Обновить .env файл."""
   191	    log("Обновление .env...", BLUE)
   192	
   193	    if not os.path.exists(ENV_FILE):
   194	        log(f"Файл {ENV_FILE} не найден! Создаём...", YELLOW)
   195	        with open(ENV_FILE, "w") as f:
   196	            f.write(f"OLLAMA_MODEL={NEW_MODEL}\n")
   197	        log(f"Создан {ENV_FILE} с {NEW_MODEL}", GREEN)
   198	        return True
   199	
   200	    # Бэкап
   201	    if os.path.exists(ENV_FILE):
   202	        with open(ENV_FILE, "r") as f:
   203	            old_content = f.read()
   204	        with open(ENV_BACKUP, "w") as f:
   205	            f.write(old_content)
   206	        log(f"Бэкап создан: {ENV_BACKUP}", GREEN)
   207	
   208	    # Обновляем OLLAMA_MODEL
   209	    new_lines = []
   210	    model_updated = False
   211	    with open(ENV_FILE, "r") as f:
   212	        for line in f:
   213	            if line.startswith("OLLAMA_MODEL="):
   214	                new_lines.append(f"OLLAMA_MODEL={NEW_MODEL}\n")
   215	                model_updated = True
   216	            else:
   217	                new_lines.append(line)
   218	
   219	    if not model_updated:
   220	        new_lines.append(f"OLLAMA_MODEL={NEW_MODEL}\n")
   221	
   222	    with open(ENV_FILE, "w") as f:
   223	        f.writelines(new_lines)
   224	
   225	    log(f"OLLAMA_MODEL обновлён на {NEW_MODEL}", GREEN)
   226	    return True
   227	
   228	def main():
   229	    log("=" * 60, BLUE)
   230	    log("ATLAS MIGRATION: qwen2.5-coder:3b → qwen3-coder-next", BLUE)
   231	    log("=" * 60, BLUE)
   232	
   233	    # 1. Проверка Ollama
   234	    if not check_ollama():
   235	        sys.exit(1)
   236	
   237	    # 2. Проверка/скачивание модели
   238	    if not check_model():
   239	        if not pull_model():
   240	            sys.exit(1)
   241	
   242	    # 3. Тесты
   243	    basic_ok = test_basic()
   244	    json_ok = test_json_tool_use()
   245	    func_ok = test_function_calling()
   246	
   247	    # 4. Результаты
   248	    log("=" * 60, BLUE)
   249	    log("РЕЗУЛЬТАТЫ ТЕСТОВ:", BLUE)
   250	    log(f"  Базовый ответ:     {'✅ PASS' if basic_ok else '❌ FAIL'}", GREEN if basic_ok else RED)
   251	    log(f"  JSON Tool Use:     {'✅ PASS' if json_ok else '❌ FAIL'}", GREEN if json_ok else RED)
   252	    log(f"  Function Calling:  {'✅ PASS' if func_ok else '⚠️ SKIP/FAIL'}", GREEN if func_ok else YELLOW)
   253	
   254	    if basic_ok and json_ok:
   255	        log("\n🎉 Модель готова к работе!", GREEN)
   256	        update_env()
   257	        log("\nСледующий шаг: запустите atlas.bat и проверьте цикл Tool Use", BLUE)
   258	        log("Команда: atlas> добавь модуль логирования", BLUE)
   259	    else:
   260	        log("\n⚠️ Модель работает, но JSON Tool Use не пройден.", YELLOW)
   261	        log("Попробуйте обновить SYSTEM_PROMPT (см. updated_system_prompt.txt)", YELLOW)
   262	        log("Или используйте Function Calling API вместо JSON-парсинга.", YELLOW)
   263	
   264	    log("=" * 60, BLUE)
   265	
   266	if __name__ == "__main__":
   267	    main()
   268	