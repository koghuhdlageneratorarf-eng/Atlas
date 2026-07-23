"""
atlas_core — Ядро Atlas Code Agent
Автономная система разработки: Tool Use + сессионная память + Self-Upgrade.
"""

from .session import SessionManager
from .context import ProjectContext
from .tools import execute_tool, TOOLS_REGISTRY

__all__ = [
    "SessionManager",
    "ProjectContext", 
    "execute_tool",
    "TOOLS_REGISTRY",
]
