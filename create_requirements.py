python
# Улучшение управления зависимостями и окружением
import os
from pathlib import Path
import subprocess

# Создание файла requirements.txt для явного указания всех зависимостей проекта
def create_requirements_txt(project_root):
    # Определение пути к файлу requirements.txt
    requirements_file = os.path.join(project_root, 'requirements.txt')

    # Проверка существования файла requirements.txt и его удаление, если он существует
    if os.path.exists(requirements_file):
        os.remove(requirements_file)

    # Получение списка всех пакетов в проекте
    packages = set()
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file.endswith('.py') or file.endswith('.json'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Извлечение имён пакетов из содержимого файла
                    packages.update(re.findall(r'import ([a-zA-Z0-9_]+)', content))
                if file.endswith('.json') and 'dependencies' in content:
                    dependencies = eval(content)['dependencies']
                    packages.update(dependencies)

    # Запись списка пакетов в файл requirements.txt
    with open(requirements_file, 'w', encoding='utf-8') as f:
        for package in sorted(packages):
            f.write(package + '\n')

# Создание виртуального окружения (venv)
def create_venv(project_root):
    # Определение пути к директории для виртуального окружения
    venv_dir = os.path.join(project_root, 'venv')

    # Проверка существования директории venv и ее удаление, если она существует
    if os.path.exists(venv_dir):
        subprocess.run(['rm', '-rf', venv_dir])

    # Создание виртуального окружения
    subprocess.run(['python', '-m', 'venv', venv_dir])

# Установка зависимостей из файла requirements.txt
def install_requirements(project_root):
    # Определение пути к файлу requirements.txt
    requirements_file = os.path.join(project_root, 'requirements.txt')

    # Проверка существования файла requirements.txt и его установка
    if os.path.exists(requirements_file):
        subprocess.run([os.path.join(project_root, 'venv/bin/pip'), 'install', '-r', requirements_file])

# Пример использования функций
if __name__ == '__main__':
    project_root = Path(__file__).parent.parent  # Путь к корневой директории проекта
    create_requirements_txt(project_root)
    create_venv(project_root)
    install_requirements(project_root)
