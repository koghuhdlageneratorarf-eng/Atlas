#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas GitHub Setup — автоматическая заливка на GitHub."""

import os
import sys
import subprocess
import json
import urllib.request
import urllib.error

def run_cmd(cmd, cwd=None):
    """Выполняет команду и возвращает stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0 and result.stderr:
        print(f"  [!] {result.stderr.strip()}")
    return result.stdout.strip(), result.returncode

def main():
    print("=" * 50)
    print("  ATLAS → GITHUB AUTO SETUP")
    print("=" * 50)
    print()

    # 1. Проверка Git
    print("[*] Проверка Git...")
    out, code = run_cmd("git --version")
    if code != 0:
        print("[!] Git не найден. Установи: https://git-scm.com/download/win")
        print("    После установки перезапусти терминал.")
        input("\nНажми Enter для выхода...")
        return
    print(f"    Git найден: {out}")

    # 2. Проверка папки
    atlas_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(atlas_dir, "main.py")):
        print(f"[!] Ошибка: запускай из папки Atlas (где main.py)")
        print(f"    Текущая папка: {atlas_dir}")
        input("\nНажми Enter для выхода...")
        return
    print(f"    Папка Atlas: {atlas_dir}")

    # 3. Ввод данных
    print()
    print("--- Настройка GitHub ---")
    print()
    print("Получи токен: github.com/settings/tokens → New token (classic)")
    print("Отметь галочку 'repo' → Generate → скопируй")
    print()

    token = input("GitHub Token: ").strip()
    if not token:
        print("[!] Токен обязателен.")
        input("Нажми Enter...")
        return

    repo_name = input("Имя репозитория [Atlas]: ").strip() or "Atlas"
    repo_desc = input("Описание [AI Digital Studio]: ").strip() or "AI Digital Studio"
    is_private = input("Приватный? (y/n) [n]: ").strip().lower() == "y"

    # 4. Получение username
    print()
    print("[*] Проверка токена...")
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            user_data = json.loads(resp.read().decode())
            username = user_data["login"]
            print(f"    Токен рабочий. Пользователь: {username}")
    except urllib.error.HTTPError as e:
        print(f"[!] Неверный токен. Код: {e.code}")
        input("Нажми Enter...")
        return
    except Exception as e:
        print(f"[!] Ошибка сети: {e}")
        input("Нажми Enter...")
        return

    # 5. Создание .gitignore
    print()
    print("[*] Создание .gitignore...")
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# Projects (generated sites)
Projects/*
!Projects/.gitkeep

# Memory backups
Memory/backups/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Secrets
.env
*.env
"""
    with open(os.path.join(atlas_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    print("    .gitignore создан")

    # 6. Создание репозитория
    print()
    print(f"[*] Создание репозитория '{repo_name}' на GitHub...")
    body = json.dumps({
        "name": repo_name,
        "description": repo_desc,
        "private": is_private,
        "auto_init": False
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=body,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            repo_data = json.loads(resp.read().decode())
            html_url = repo_data["html_url"]
            print(f"    Репозиторий создан!")
            print(f"    URL: {html_url}")
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print(f"    Репозиторий уже существует. Использую существующий.")
            html_url = f"https://github.com/{username}/{repo_name}"
        else:
            print(f"[!] Ошибка создания: {e.code}")
            input("Нажми Enter...")
            return

    # 7. Git init + commit + push
    print()
    print("[*] Инициализация Git и заливка кода...")

    os.chdir(atlas_dir)

    if not os.path.exists(os.path.join(atlas_dir, ".git")):
        run_cmd("git init")
        print("    Git инициализирован")
    else:
        print("    Git уже инициализирован")

    # Удаляем старый remote если есть
    run_cmd("git remote remove origin")
    run_cmd(f"git remote add origin https://{token}@github.com/{username}/{repo_name}.git")
    print("    Remote настроен")

    run_cmd("git add -A")
    out, code = run_cmd('git commit -m "Initial commit: Atlas Digital Studio v3.0"')
    if code != 0:
        print("    Нечего коммитить (возможно, уже закоммичено)")
    else:
        print("    Коммит создан")

    run_cmd("git branch -M main")
    out, code = run_cmd("git push -u origin main --force")
    if code != 0:
        print(f"[!] Ошибка пуша:\n{out}")
        print("    Попробуй вручную: git push -u origin main")
        input("Нажми Enter...")
        return

    # 8. Успех
    print()
    print("=" * 50)
    print("  УСПЕХ! Код залит на GitHub.")
    print("=" * 50)
    print()
    print(f"Ссылка: {html_url}")
    print()
    print("Что делать дальше:")
    print("  1. Открой чат с Kimi")
    print(f"  2. Дай ссылку: {html_url}")
    print("  3. Напиши: Продолжаем Atlas, текущий фокус — [шаг]")
    print()
    print("  Kimi прочитает README и код прямо с GitHub.")
    print()
    input("Нажми Enter для выхода...")

if __name__ == "__main__":
    main()
