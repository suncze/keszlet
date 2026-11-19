"""INTENTIONAL mutation: stock < minimum instead of <=. Not a real development bug."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests.test_inventory.InventoryTests.test_06_low_stock_includes_threshold"
CORRECT = 'item["is_low"] = item["stock"] <= item["minimum_stock"]'
INCORRECT = 'item["is_low"] = item["stock"] < item["minimum_stock"]'


def main():
    evidence = ROOT / "docs" / "evidence" / "defect"
    evidence.mkdir(parents=True,exist_ok=True)
    fixed = (ROOT / "backend" / "database.py").read_text(encoding="utf-8")
    if fixed.count(CORRECT) != 1:
        raise SystemExit("A várt javított szabály nem található pontosan egyszer; kézi ellenőrzés szükséges.")
    broken = fixed.replace(CORRECT,INCORRECT,1)
    (evidence / "broken_database.py").write_text(broken,encoding="utf-8")
    (evidence / "fixed_database.py").write_text(fixed,encoding="utf-8")
    shutil.copy2(ROOT / "tests" / "test_inventory.py",evidence / "test_inventory_snapshot.py")
    codes = {}
    with TemporaryDirectory(prefix="keszlet-defect-") as temporary:
        folder = Path(temporary)
        for name in ("backend","tests"):
            shutil.copytree(ROOT / name,folder / name,ignore=shutil.ignore_patterns("__pycache__"))
        for variant, source in (("broken",broken),("fixed",fixed)):
            (folder / "backend" / "database.py").write_text(source,encoding="utf-8")
            shutil.rmtree(folder / "backend" / "__pycache__",ignore_errors=True)
            result = subprocess.run([sys.executable,"-B","-m","unittest",TEST,"-v"],cwd=folder,capture_output=True,text=True)
            codes[variant] = result.returncode
            (evidence / f"{variant}.log").write_text(result.stdout+result.stderr,encoding="utf-8")
            print(f"{variant}: kilépési kód {result.returncode}")
    report = {
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "kind":"INTENTIONAL EDUCATIONAL MUTATION; not a real development defect",
        "test":TEST,"correct_rule":CORRECT,"incorrect_rule":INCORRECT,
        "expected":"stock=minimum=5 is low; stock=6, minimum=5 is not low",
        "exit_codes":codes,
        "sha256":{name:hashlib.sha256((evidence / name).read_bytes()).hexdigest() for name in ("broken_database.py","fixed_database.py","test_inventory_snapshot.py")},
    }
    (evidence / "manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if codes != {"broken":1,"fixed":0}:
        raise SystemExit("Nem a várt hibás/javított eredmény született; vizsgáld meg a naplókat.")
    print("Bizonyíték mentve. A működő alkalmazás kódját és adatait nem módosítottuk.")


if __name__ == "__main__":
    main()
