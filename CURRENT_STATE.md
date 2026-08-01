# Current State of Atlas

**Date:** 2026-07-29

---

## Working

- Chat via Open WebUI (http://localhost:3000)
- API server on http://localhost:8000/v1
- Models: executive (OpenRouter) / developer (Ollama)
- Chat / file operations separation
- Read/write/edit files
- Project context (Graphify)
- Git commands via REPL (/status, /diff, /backup)
- /clear, /context, /help
- Model Router (OpenRouter + Ollama)
- SQLite session and episode memory
- Backup via /backup
- Skills system

---

## In Progress / Needs Work

- Self-Upgrade (code exists, not automated)
- Planner, Reviewer, Executor as separate components
- Tests (no automated testing after changes)
- Git rollback (backup exists, no automatic rollback)

---

## Not Yet Implemented (next stages)

- CEO Agent
- Chief Architect
- AI Company (departments)
- Task System (queue, statuses, dependencies)
- Memory 2.0 (vector DB, Obsidian, RAG)
- Evolution Engine (Self Learning/Upgrade/Healing/Expansion)
- Plugin SDK
- Agent Marketplace
- Desktop UI
- Browser Agent
- MCP / OpenClaw

---

## Milestone A (next)

Atlas can safely change files + Git rollback + tests

## Milestone B

Atlas CEO + Architect + Memory + Reviewer

## Milestone C

Atlas develops itself

---

## DeepSeek - main development brain until Milestone B

Current scheme:
- DeepSeek -> architecture analysis, code writing, refactoring, testing
- OpenRouter -> CEO/analytics
- Ollama -> local operations

After Milestone B, DeepSeek becomes a consultant.
