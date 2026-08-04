"""
Permission Engine — управление уровнями риска действий.

Согласно Конституции (Article VII) и Master Plan (Этап 10):
- SAFE → выполняется автоматически
- MEDIUM → требует подтверждения
- HIGH → только после ручного разрешения
- CRITICAL → запрещено
"""

from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionEngine:
    def __init__(self):
        # Правила: действие → уровень риска
        self.rules: dict[str, RiskLevel] = {
            # SAFE — автоматически
            "read_file": RiskLevel.SAFE,
            "list_directory": RiskLevel.SAFE,
            "search_files": RiskLevel.SAFE,
            "git_status": RiskLevel.SAFE,
            "git_diff": RiskLevel.SAFE,
            "get_symbols": RiskLevel.SAFE,
            "analyze": RiskLevel.SAFE,
            "plan": RiskLevel.SAFE,
            # MEDIUM — требуется подтверждение
            "write_file": RiskLevel.MEDIUM,
            "edit_file": RiskLevel.MEDIUM,
            "create_file": RiskLevel.MEDIUM,
            "git_commit": RiskLevel.MEDIUM,
            "backup_file": RiskLevel.MEDIUM,
            "rollback": RiskLevel.MEDIUM,
            "run_command": RiskLevel.MEDIUM,
            # HIGH — только после ручного разрешения
            "delete_file": RiskLevel.HIGH,
            "git_push": RiskLevel.HIGH,
            "install_package": RiskLevel.HIGH,
            "modify_config": RiskLevel.HIGH,
            # CRITICAL — запрещено
            "delete_project": RiskLevel.CRITICAL,
            "clear_memory": RiskLevel.CRITICAL,
            "modify_secrets": RiskLevel.CRITICAL,
            "modify_permissions": RiskLevel.CRITICAL,
            "modify_constitution": RiskLevel.CRITICAL,
            "dangerous_shell": RiskLevel.CRITICAL,
        }

        # Одобренные HIGH операции (временные)
        self.approved: list[str] = []

    def get_risk(self, action: str) -> RiskLevel:
        """Получить уровень риска для действия."""
        return self.rules.get(action, RiskLevel.MEDIUM)

    def can_execute(self, action: str) -> tuple:
        """
        Проверить, можно ли выполнить действие.
        Возвращает (разрешено, причина).
        """
        risk = self.get_risk(action)
        if risk == RiskLevel.SAFE:
            return True, "safe"
        if risk == RiskLevel.MEDIUM:
            return False, "needs_confirmation"
        if risk == RiskLevel.HIGH:
            return action in self.approved, f"needs_approval ({action})"
        if risk == RiskLevel.CRITICAL:
            return False, "critical_operation"
        return False, "unknown"

    def approve(self, action: str) -> None:
        """Одобрить HIGH операцию (временное разрешение)."""
        if action not in self.approved:
            self.approved.append(action)

    def revoke(self, action: str) -> None:
        """Отозвать разрешение."""
        if action in self.approved:
            self.approved.remove(action)

    def require_confirmation(self, action: str) -> str:
        """Вернуть сообщение для подтверждения."""
        risk = self.get_risk(action)
        if risk == RiskLevel.MEDIUM:
            return f"⚠️ Требуется подтверждение: {action} (medium risk)"
        if risk == RiskLevel.HIGH:
            return f"🔴 Требуется одобрение: {action} (high risk)"
        return f"❌ Запрещено: {action}"

    def status(self) -> str:
        return f"""
Permission Engine
────────────────
SAFE: {[a for a, r in self.rules.items() if r == RiskLevel.SAFE][:5]}...
MEDIUM: {[a for a, r in self.rules.items() if r == RiskLevel.MEDIUM][:5]}...
HIGH: {[a for a, r in self.rules.items() if r == RiskLevel.HIGH][:5]}...
CRITICAL: {[a for a, r in self.rules.items() if r == RiskLevel.CRITICAL]}
Approved HIGH: {self.approved or 'none'}
"""


# Singleton
_permission_engine = None


def get_permission_engine() -> PermissionEngine:
    global _permission_engine
    if _permission_engine is None:
        _permission_engine = PermissionEngine()
    return _permission_engine


if __name__ == "__main__":
    pe = get_permission_engine()
    print(pe.status())

    print("\n--- Тест ---")
    for action in ["read_file", "write_file", "delete_file", "modify_permissions"]:
        allowed, reason = pe.can_execute(action)
        print(f"{action}: {allowed} ({reason})")
