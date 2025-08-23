from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

DEFAULT_PATTERNS = ["*.json", "*.csv", "*.xml", "*.txt"]

def find_backend_dir(base: Path, cli_backend: str | None) -> Path:
    if cli_backend:
        p = (base / cli_backend).resolve()
        if not p.is_dir():
            raise SystemExit(f"❌ --backend указан, но не найден каталог: {p}")
        return p
    cand1 = base / "backend"
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

def run_script(script: Path, cwd: Path) -> dict:
    started_at = datetime.utcnow().isoformat() + "Z"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(cwd),
        capture_output=True,
        text=True
    )
    ended_at = datetime.utcnow().isoformat() + "Z"
    return {
        "script": script.name,
        "returncode": proc.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "stdout": proc.stdout,
        "stderr": proc.stderr
    }

def move_outputs(backend_dir: Path, out_dir: Path, patterns: list[str]) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    for pat in patterns:
        for p in backend_dir.glob(pat):
            if p.is_file():
                target = out_dir / p.name
                # If name collision, add numeric suffix
                idx = 1
                while target.exists():
                    target = out_dir / f"{p.stem}_{idx}{p.suffix}"
                    idx += 1
                target.write_bytes(p.read_bytes())
                moved.append(str(target.resolve()))
    return moved

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run all python scripts in ./backend and generate a JSON report.")
    ap.add_argument("--backend", type=str, default=None, help="Path to backend directory (default: ./backend or ./backend/backend)")
    ap.add_argument("--out-dir", type=str, default="outputs", help="Where to collect obvious outputs (*.json, *.csv, *.xml, *.txt)")
    ap.add_argument("--no-collect", action="store_true", help="Do not collect outputs")
    return ap

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)

    here = Path(__file__).resolve().parent
    backend_dir = find_backend_dir(here, args.backend)

    scripts = list_scripts(backend_dir)
    if not scripts:
        print("⚠️  В папке 'backend' не найдено исполняемых .py-файлов.")
        return 0

    print("Найдены скрипты для запуска (в порядке выполнения):")
    for s in scripts:
        print("  •", s.name)

    results = []
    failures = 0
    for s in scripts:
        print(f"\n===== ▶️  Запуск: {s.name} =====")
        res = run_script(s, cwd=backend_dir)
        results.append(res)
        if res["returncode"] == 0:
            print(f"===== ✅ Успех: {s.name} =====")
        else:
            print(f"===== ❗️ Ошибка: {s.name} (код {res['returncode']}) =====")
            failures += 1

    report = {
        "backend_dir": str(backend_dir.resolve()),
        "total": len(scripts),
        "success": len(scripts) - failures,
        "failures": failures,
        "results": results
    }

    report_path = here / "generate_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 Отчёт сохранён в: {report_path}")

    if not args.no_collect:
        out_dir = (here / args.out_dir).resolve()
        moved = move_outputs(backend_dir, out_dir, DEFAULT_PATTERNS)
        print(f"📦 Перемещено файлов: {len(moved)} → {out_dir}")
    else:
        moved = []

    # Also place a lightweight summary at the end
    print("\n===== Итог =====")
    print(f"Всего скриптов: {len(scripts)}")
    print(f"Успешно:       {len(scripts) - failures}")
    print(f"С ошибками:    {failures}")

    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
