"""Reproducible project verification; saves real results, never edits user data."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT / "docs" / "evidence"
    evidence.mkdir(parents=True,exist_ok=True)
    specification = (ROOT / "SPECIFIKACIO.md").read_text(encoding="utf-8")
    checks = {
        "specification_characters":len(specification),
        "specification_within_4000":len(specification) <= 4000,
        "acceptance_criteria_numbered_1_through_8":re.findall(r"^(\d+)\. ",specification,re.M) == [str(i) for i in range(1,9)],
    }
    syntax_errors = []
    for folder in ("backend","tests","scripts"):
        for path in (ROOT / folder).rglob("*.py"):
            try:
                compile(path.read_text(encoding="utf-8"),str(path),"exec")
            except SyntaxError as exc:
                syntax_errors.append(str(exc))
    for name in ("start.py","frontend_server.py","seed_demo.py"):
        compile((ROOT / name).read_text(encoding="utf-8"),name,"exec")
    checks["python_syntax_errors"] = syntax_errors
    command = [sys.executable,"-m","unittest","discover","-v"]
    result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    log = result.stdout + result.stderr
    (evidence / "test-results.txt").write_text(log,encoding="utf-8")
    match = re.search(r"Ran (\d+) tests?",log)
    report = {
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "python":platform.python_version(),"sqlite":sqlite3.sqlite_version,
        "command":["python3","-m","unittest","discover","-v"],
        "exit_code":result.returncode,"tests_run":int(match[1]) if match else None,
        "checks":checks,
        "browser_test":"Not performed: local TCP binding was denied by the execution environment.",
    }
    (evidence / "verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(log)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if result.returncode == 0 and all((checks["specification_within_4000"],checks["acceptance_criteria_numbered_1_through_8"],not syntax_errors)) else 1


if __name__ == "__main__":
    sys.exit(main())
