"""Start both components: python3 start.py [--demo]. Ctrl+C stops both."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Készlet — frontend és backend indítása")
    parser.add_argument("--port", type=int, default=8080, help="Frontend port, alapérték: 8080")
    parser.add_argument("--api-port", type=int, default=8000, help="Backend port, alapérték: 8000")
    parser.add_argument("--db", default=os.environ.get("INVENTORY_DB", "data/inventory.sqlite3"))
    parser.add_argument("--demo", action="store_true", help="Bemutatóadatok csak üres adatbázishoz")
    args = parser.parse_args()
    if args.port == args.api_port or not all(1 <= p <= 65535 for p in (args.port,args.api_port)):
        parser.error("Két különböző, 1–65535 közötti port szükséges.")
    root = Path(__file__).resolve().parent
    database = Path(args.db)
    if not database.is_absolute():
        database = root / database
    if args.demo:
        from seed_demo import seed
        seed(database)
    children = []
    try:
        children.append(subprocess.Popen([sys.executable,"-m","backend.server","--port",str(args.api_port),"--frontend-port",str(args.port),"--db",str(database)], cwd=root))
        children.append(subprocess.Popen([sys.executable,"frontend_server.py","--port",str(args.port),"--api-port",str(args.api_port)], cwd=root))
        print(f"\nKÉSZLET — http://127.0.0.1:{args.port}\nLeállítás: Ctrl+C\n", flush=True)
        while all(process.poll() is None for process in children):
            time.sleep(.3)
        print("Az egyik kiszolgáló leállt. Ha a port foglalt, válassz másikat a --port és --api-port kapcsolóval.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nA kiszolgálók leállítása…")
        return 0
    finally:
        for process in children:
            if process.poll() is None:
                process.terminate()
        for process in children:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    sys.exit(main())
