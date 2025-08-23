# Auto-generated unified runner
from pathlib import Path
import argparse
import importlib
import subprocess
import sys
import time
import json
import shutil
import traceback
from typing import List

ROOT = Path(r"/mnt/data/backend_extracted")
BACKEND_DIR = ROOT / "backend"

def discover_modules() -> List[str]:
    mods = []
    for p in BACKEND_DIR.glob("*.py"):
        if p.name.startswith("_") or p.name == "__init__.py":
            continue
        mods.append(p.stem)
    mods.sort()
    return mods

def has_callable(mod, name: str) -> bool:
    return hasattr(mod, name) and callable(getattr(mod, name))

def run_via_import(module_name: str, entry: str):
    import importlib
    start = time.time()
    try:
        mod = importlib.import_module(f"backend.{module_name}")
    except Exception as e:
        return {"module": module_name, "mode": "import", "entry": entry, "ok": False, "error": repr(e), "elapsed": 0.0}
    try:
        func = getattr(mod, entry)
        func()
        return {"module": module_name, "mode": "import", "entry": entry, "ok": True, "elapsed": time.time() - start}
    except Exception as e:
        return {"module": module_name, "mode": "import", "entry": entry, "ok": False, "error": traceback.format_exc(), "elapsed": time.time() - start}

def run_via_subprocess(module_name: str, timeout: int):
    start = time.time()
    cmd = [sys.executable, "-m", f"backend.{module_name}"]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0
        return {
            "module": module_name,
            "mode": "subprocess",
            "cmd": " ".join(cmd),
            "ok": ok,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "returncode": proc.returncode,
            "elapsed": time.time() - start,
        }
    except subprocess.TimeoutExpired:
        return {"module": module_name, "mode": "subprocess", "cmd": " ".join(cmd), "ok": False, "error": f"Timeout after {timeout}s", "elapsed": time.time() - start}
    except Exception:
        return {"module": module_name, "mode": "subprocess", "cmd": " ".join(cmd), "ok": False, "error": traceback.format_exc(), "elapsed": time.time() - start}

def find_generated_files():
    exts = {".xml", ".rss", ".atom", ".json"}
    found = []
    for p in ROOT.glob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            found.append(p)
    return found

def move_outputs(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    for p in find_generated_files():
        target = out_dir / p.name
        try:
            if target.exists():
                target.unlink()
            shutil.move(str(p), str(target))
            moved.append(str(target))
        except Exception:
            pass
    return moved

def main():
    parser = argparse.ArgumentParser(description="Unified runner for backend scrapers.")
    parser.add_argument("--list", action="store_true", help="List available modules and exit.")
    parser.add_argument("--all", action="store_true", help="Run all discovered modules.")
    parser.add_argument("--only", type=str, default="", help="Comma-separated list of modules to run.")
    parser.add_argument("--out-dir", type=str, default="outputs", help="Directory to collect generated files (xml/rss/atom/json).")
    parser.add_argument("--timeout", type=int, default=300, help="Per-module timeout (seconds) for subprocess mode.")
    args = parser.parse_args()

    modules = discover_modules()

    if args.list:
        print("Discovered modules:", ", ".join(modules))
        sys.exit(0)

    selected = modules if args.all else [m.strip() for m in args.only.split(",") if m.strip()]
    if not selected:
        parser.error("Nothing to run. Use --all or --only mod1,mod2. Use --list to see available modules.")

    report = {"selected": selected, "results": [], "moved": [], "out_dir": args.out_dir}
    for mod in selected:
        # стратегия: пытаемся импортировать и вызвать generate(), затем main(), иначе подпроцесс
        try:
            imported = importlib.import_module(f"backend.{mod}")
            if has_callable(imported, "generate"):
                res = run_via_import(mod, "generate")
            elif has_callable(imported, "main"):
                res = run_via_import(mod, "main")
            else:
                res = run_via_subprocess(mod, args.timeout)
        except Exception:
            res = run_via_subprocess(mod, args.timeout)
        report["results"].append(res)

    out_dir = ROOT / args.out_dir
    moved = move_outputs(out_dir)
    report["moved"] = moved

    report_path = ROOT / "generate_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReport saved to: {report_path}")
    print(f"Outputs moved to: {out_dir.resolve()}")

if __name__ == "__main__":
    main()
