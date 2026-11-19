"""Explicit, opt-in demo data. Existing databases are never overwritten."""
import argparse
from backend.database import Inventory

DEMO = [
    ("Másolópapír A4, 80 g", "PAP-001", "Irodaszer", 12, 15, 4, 5, 6),
    ("Kartondoboz, 40 × 30 × 30 cm", "CSM-102", "Csomagolás", 86, 30, 8, 4, 20),
    ("Nitril védőkesztyű, M", "VED-031", "Munkavédelem", 8, 20, 5, 5, 10),
    ("Ragasztószalag, 48 mm", "CSM-014", "Csomagolás", 124, 40, 10, 3, 15),
    ("Golyóstoll, kék", "IRO-028", "Irodaszer", 65, 20, 3, 4, 10),
    ("LED fénycső, 120 cm", "VIL-007", "Üzemeltetés", 0, 5, 1, 7, 3),
    ("Kéztörlő, hajtogatott", "HIG-041", "Higiénia", 18, 18, 6, 4, 12),
    ("Címke, 100 × 150 mm", "CSM-009", "Csomagolás", 240, 100, 20, 5, 40),
    ("Fertőtlenítőszer, 1 l", "HIG-012", "Higiénia", 32, 10, 2, 3, 6),
    ("Iratrendező, 75 mm", "IRO-067", "Irodaszer", 44, 15, 2, 5, 8),
    ("Védőszemüveg, víztiszta", "VED-018", "Munkavédelem", 9, 10, 1, 7, 5),
    ("Stretch fólia, 500 mm", "CSM-022", "Csomagolás", 27, 12, 3, 4, 8),
]


def seed(path):
    service = Inventory(path)
    if service.products():
        print("A meglévő adatbázis megmaradt; bemutatóadatokat nem adtunk hozzá.")
        return
    for name, sku, category, stock, minimum, usage, lead, safety in DEMO:
        service.create({"name":name,"sku":sku,"category":category,"initial_stock":stock,"minimum_stock":minimum,"daily_usage":usage,"lead_time":lead,"safety_stock":safety})
    products = service.products()
    for sku, kind, quantity, note in [
        ("CSM-102", "in", 20, "SZL-2026-0148 szállítólevél"),
        ("IRO-028", "out", 5, "Irodai felhasználás"),
        ("CSM-014", "out", 12, "Rendelések csomagolása"),
        ("HIG-012", "in", 8, "Heti beszerzés"),
    ]:
        product = next(p for p in products if p["sku"] == sku)
        service.move({"product_id":product["id"],"type":kind,"quantity":quantity,"note":note})
    print("12 bemutatótermék és a kapcsolódó mozgásnapló létrehozva.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/inventory.sqlite3")
    seed(parser.parse_args().db)
