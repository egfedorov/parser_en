from __future__ import annotations
import sys
import subprocess
from pathlib import Path

def find_backend_dir(start: Path) -> Path:
    """
    Ищем папку 'backend' рядом с generate.py.
    Если её нет — пробуем вариант когда архив распакован как ./backend/backend.
    """
    cand1 = start / "backend"
    cand2 = cand1 / "backend"
    if cand1.is_dir():
        return cand1
    if cand2.is_dir():
        return cand2
    raise SystemExit("❌ Не найдена папка 'backend' рядом с generate.py")

def list_scripts(backend_dir: Path) -> list[Path]:
    scripts = []
    for p in sorted(backend_dir.glob("*.py")):
        name = p.name
        if name == "__init__.py":
            continue
        if name.startswith("_") or name.startswith("."):
            continue
        scripts.append(p)
    return scripts

def run_script(path: Path, cwd: Path) -> int:
    print(f"\n===== ▶️  Запуск: {path.name} =====")
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(cwd),
            check=False
        )
        code = proc.returncode
        if code == 0:
            print(f"===== ✅ Успех: {path.name} (код {code}) =====\n")
        else:
            print(f"===== ❗️ Ошибка: {path.name} (код {code}) =====\n")
        return code
    except KeyboardInterrupt:
        print("Остановлено пользователем.")
        return 130
    except Exception as e:
        print(f"Исключение при запуске {path.name}: {e}")
        return 1

def main():
    here = Path(__file__).resolve().parent
    backend_dir = find_backend_dir(here)

    scripts = list_scripts(backend_dir)
    if not scripts:
        print("⚠️  В папке 'backend' не найдено исполняемых .py-файлов.")
        return 0

    print("Найдены скрипты для запуска (в порядке выполнения):")
    for s in scripts:
        print("  •", s.name)

    failures = 0
    for s in scripts:
        code = run_script(s, cwd=backend_dir)
        if code != 0:
            failures += 1

    total = len(scripts)
    print("\n===== Итог =====")
    print(f"Всего скриптов: {total}")
    print(f"Успешно:       {total - failures}")
    print(f"С ошибками:    {failures}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
