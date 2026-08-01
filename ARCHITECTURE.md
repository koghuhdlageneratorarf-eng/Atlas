# Atlas Architecture (Current)

**Date:** 2026-07-29

---

## Structure

`
Atlas/
├── atlas_core/
│   ├── agent.py          # REPL + Tool Use loop
│   ├── session.py        # SQLite session memory
│   ├── context.py        # Project context (Graphify)
│   └── tools.py          # Tools (read/write/edit/run)
├── Config/
│   ├── llm_client.py     # Model Router (OpenRouter + Ollama)
│   ├── models.yaml       # Model priorities by agent
│   └── .env              # API keys
├── Brain/
│   ├── graphify_bridge.py
│   └── memory_graph.py
├── Agents/               # Legacy (brief/developer/executive)
├── Projects/             # Finished products
├── Skills/               # Templates
├── Memory/
│   ├── brain_memory.db
│   └── Ideas/
├── api_openai.py         # OpenAI-compatible server for WebUI
├── main.py               # Old pipeline
├── atlas.bat
└── Prompts/
    └── SYSTEM_PROMPT_mini.md
`

---

## Components

**atlas_core/agent.py** - main loop: user -> LLM -> tools -> result. Supports REPL and Tool Use.

**atlas_core/session.py** - SQLite session memory: message history, tool calls.

**atlas_core/context.py** - project context via Graphify (knowledge graph from code).

**atlas_core/tools.py** - tools: read_file, write_file, edit_file, list_directory, run_command, search_files, git_status, git_commit, backup_file.

**Config/llm_client.py** - Model Router: OpenRouter (Gemini/Claude/GPT) + Ollama (local) + Groq/Cloudflare as backup.

**Config/models.yaml** - model priorities for each agent (executive, developer, brief, self_upgrade).

**Brain/graphify_bridge.py** - Graphify adapter: builds project graph, answers structure queries.

**Brain/memory_graph.py** - SQLite memory: episodes, bugs, decisions.

**api_openai.py** - OpenAI-compatible server for Open WebUI on port 8000.

---

## Models

- **atlas-executive** - strategic tasks via OpenRouter (Gemini/Claude/GPT)
- **atlas-developer** - file operations via Ollama or OpenRouter
- **atlas-brief** - TZ generation

Router selects model by priorities from models.yaml.

---

## Interfaces

- **Open WebUI** - http://localhost:3000
- **API** - http://localhost:8000/v1
- **CLI** - python atlas_core/agent.py or atlas.bat

---

## Key Principles

1. Don't reinvent the wheel
2. Skills-first
3. Hybrid models (cloud + local)
4. Tool Use for files
5. Git + backups for rollback
6. Autonomy
7. Memory excluded from backups
