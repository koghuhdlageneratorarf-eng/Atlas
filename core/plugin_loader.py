"""
Plugin Loader — загрузка плагинов из папки plugins/.

Согласно Roadmap P2 и Конституции (Article XII):
- Плагины расширяют Atlas без изменения ядра
- Каждый плагин — отдельный Python-модуль
"""

import importlib
import importlib.util
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent.parent / "plugins"


class PluginLoader:
    def __init__(self):
        self.plugins: dict[str, dict] = {}
        self.commands: dict[str, dict] = {}  # команда → {plugin, handler}
        self._loaded = False

    def load_all(self):
        """Загрузить все плагины из папки plugins/."""
        if self._loaded:
            return
        if not PLUGIN_DIR.exists():
            PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
            print("[PluginLoader] Папка plugins/ создана")

        for py_file in PLUGIN_DIR.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_plugin(py_file)

        self._loaded = True
        print(f"[PluginLoader] Загружено {len(self.plugins)} плагинов")

    def _load_plugin(self, filepath: Path):
        """Загрузить один плагин."""
        try:
            module_name = filepath.stem
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "register"):
                plugin_info = module.register()
                plugin_info["_module"] = module
                self.plugins[module_name] = plugin_info
                self._register_commands(module_name, plugin_info)
                print(
                    f"[PluginLoader] ✅ Загружен: {plugin_info.get('name', module_name)}"
                )
            else:
                print(f"[PluginLoader] ⚠️ {filepath.name}: нет функции register()")
        except Exception as e:
            print(f"[PluginLoader] ❌ Ошибка загрузки {filepath.name}: {e}")

    def _register_commands(self, plugin_name: str, plugin_info: dict):
        """Зарегистрировать команды из плагина."""
        for cmd in plugin_info.get("commands", []):
            handler_name = plugin_info.get("commands", {}).get(cmd)
            if handler_name:
                module = plugin_info.get("_module")
                if hasattr(module, handler_name):
                    self.commands[cmd] = {
                        "plugin": plugin_name,
                        "handler": getattr(module, handler_name),
                    }
                    print(
                        f"[PluginLoader]   Команда: {cmd} → {plugin_name}.{handler_name}"
                    )

    def execute_command(self, command: str, args: str = "") -> str | None:
        """Выполнить команду плагина."""
        if command not in self.commands:
            return None
        try:
            handler = self.commands[command]["handler"]
            return handler(args)
        except Exception as e:
            return f"❌ Ошибка выполнения команды {command}: {e}"

    def list_plugins(self) -> str:
        """Список плагинов и их команд."""
        if not self.plugins:
            return "Нет загруженных плагинов"
        lines = ["Загруженные плагины:"]
        for name, info in self.plugins.items():
            cmd_list = ", ".join(info.get("commands", {}).keys())
            lines.append(
                f"  • {info.get('name', name)} v{info.get('version', '1.0')} — {cmd_list}"
            )
        return "\n".join(lines)


# Singleton
_loader = None


def get_plugin_loader() -> PluginLoader:
    global _loader
    if _loader is None:
        _loader = PluginLoader()
        _loader.load_all()
    return _loader


if __name__ == "__main__":
    loader = get_plugin_loader()
    print(loader.list_plugins())
