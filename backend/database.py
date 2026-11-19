"""Transactional inventory service. No third-party dependencies."""
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import uuid
from zoneinfo import ZoneInfo


class AppError(Exception):
    def __init__(self, message, status=400, field=None):
        super().__init__(message)
        self.status, self.field = status, field


FIELDS = {"name", "sku", "category", "minimum_stock", "daily_usage", "lead_time", "safety_stock"}
MAX_STOCK = 1_000_000_000
SQLITE_MAX_INTEGER = 2**63 - 1


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def integer(value, field, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise AppError(f"Egész számot adj meg {minimum:,} és {maximum:,} között.", field=field)
    return value


def clean_text(value, field, label, maximum, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value.strip()) > maximum:
        raise AppError(f"{label}: {'1' if required else '0'}–{maximum} karakter adható meg.", field=field)
    return value.strip()


def product_data(data, creating):
    if not isinstance(data, dict):
        raise AppError("JSON objektum szükséges.")
    allowed = FIELDS | ({"initial_stock"} if creating else set())
    if set(data) - allowed:
        raise AppError("Ismeretlen mező. A készlet kizárólag készletmozgással módosítható.")
    result = {
        "name": clean_text(data.get("name"), "name", "Terméknév", 160),
        "sku": clean_text(clean_text(data.get("sku"), "sku", "Cikkszám", 64).upper(), "sku", "Cikkszám", 64),
        "category": clean_text(data.get("category", ""), "category", "Kategória", 80, False),
    }
    for key in ("minimum_stock", "daily_usage", "lead_time", "safety_stock"):
        result[key] = integer(data.get(key, 0), key)
    if creating:
        result["stock"] = integer(data.get("initial_stock", 0), "initial_stock", maximum=MAX_STOCK)
    return result


def enrich(row):
    item = dict(row)
    item["is_low"] = item["stock"] <= item["minimum_stock"]
    item["reorder_quantity"] = max(0, item["daily_usage"] * item["lead_time"] + item["safety_stock"] - item["stock"])
    item["coverage_days"] = round(item["stock"] / item["daily_usage"], 1) if item["daily_usage"] else None
    return item


class Inventory:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 160),
                    sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    category TEXT NOT NULL DEFAULT '',
                    stock INTEGER NOT NULL CHECK(typeof(stock)='integer' AND stock BETWEEN 0 AND 1000000000),
                    minimum_stock INTEGER NOT NULL CHECK(minimum_stock >= 0),
                    daily_usage INTEGER NOT NULL CHECK(daily_usage >= 0),
                    lead_time INTEGER NOT NULL CHECK(lead_time >= 0),
                    safety_stock INTEGER NOT NULL CHECK(safety_stock >= 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    product_name TEXT NOT NULL,
                    product_sku TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('in','out','opening')),
                    quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity > 0),
                    stock_after INTEGER NOT NULL CHECK(stock_after >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    request_id TEXT UNIQUE
                );
                CREATE INDEX IF NOT EXISTS movements_product_date ON movements(product_id,created_at);
                CREATE TRIGGER IF NOT EXISTS immutable_movement_update BEFORE UPDATE ON movements
                BEGIN SELECT RAISE(ABORT, 'A mozgásnapló nem módosítható.'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_movement_delete BEFORE DELETE ON movements
                BEGIN SELECT RAISE(ABORT, 'A mozgásnapló nem törölhető.'); END;
                PRAGMA user_version=1;
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.create_function("casefold", 1, lambda value: str(value).casefold(), deterministic=True)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def products(self):
        with self.connection() as db:
            return [enrich(row) for row in db.execute("SELECT * FROM products ORDER BY name COLLATE NOCASE,id")]

    def product(self, product_id, db=None):
        if type(product_id) is not int or not 1 <= product_id <= SQLITE_MAX_INTEGER:
            raise AppError("A termék nem található.", 404)
        if db is None:
            with self.connection() as connection:
                return self.product(product_id, connection)
        row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if row is None:
            raise AppError("A termék nem található.", 404)
        return enrich(row)

    def create(self, data):
        values = product_data(data, True)
        timestamp = now()
        try:
            with self.transaction() as db:
                keys = list(values) + ["created_at", "updated_at"]
                cursor = db.execute(f"INSERT INTO products ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", list(values.values()) + [timestamp, timestamp])
                product = self.product(cursor.lastrowid, db)
                if product["stock"]:
                    self._log(db, product, "opening", product["stock"], "Nyitókészlet", timestamp)
                return product
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc):
                raise AppError("Ez a cikkszám már létezik.", 409, "sku") from exc
            raise

    def update(self, product_id, data):
        values = product_data(data, False)
        try:
            with self.transaction() as db:
                self.product(product_id, db)
                db.execute(f"UPDATE products SET {','.join(key+'=?' for key in values)},updated_at=? WHERE id=?", list(values.values()) + [now(), product_id])
                return self.product(product_id, db)
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc):
                raise AppError("Ez a cikkszám már létezik.", 409, "sku") from exc
            raise

    def _log(self, db, product, kind, quantity, note, timestamp, request_id=None):
        cursor = db.execute("INSERT INTO movements(product_id,product_name,product_sku,type,quantity,stock_after,note,created_at,request_id) VALUES(?,?,?,?,?,?,?,?,?)", (product["id"], product["name"], product["sku"], kind, quantity, product["stock"], note, timestamp, request_id))
        return dict(db.execute("SELECT * FROM movements WHERE id=?", (cursor.lastrowid,)).fetchone())

    def move(self, data):
        if not isinstance(data, dict) or set(data) - {"product_id", "type", "quantity", "note", "request_id"}:
            raise AppError("Érvénytelen készletmozgási adatok.")
        product_id = integer(data.get("product_id"), "product_id", 1, MAX_STOCK)
        quantity = integer(data.get("quantity"), "quantity", 1, MAX_STOCK)
        kind = data.get("type")
        if kind not in ("in", "out"):
            raise AppError("Bevételezés vagy kiadás választható.", field="type")
        note = clean_text(data.get("note", ""), "note", "Megjegyzés", 500, False)
        request_id = clean_text(data.get("request_id", str(uuid.uuid4())), "request_id", "Műveletazonosító", 80)
        with self.transaction() as db:
            previous = db.execute("SELECT * FROM movements WHERE request_id=?", (request_id,)).fetchone()
            if previous:
                if (previous["product_id"], previous["type"], previous["quantity"], previous["note"]) != (product_id, kind, quantity, note):
                    raise AppError("A műveletazonosító már másik művelethez tartozik.", 409)
                return {"product": self.product(product_id, db), "movement": dict(previous), "replayed": True}
            product = self.product(product_id, db)
            stock = product["stock"] + (quantity if kind == "in" else -quantity)
            if stock < 0:
                raise AppError(f"Nincs elegendő készlet. Elérhető: {product['stock']} db.", 409, "quantity")
            if stock > MAX_STOCK:
                raise AppError("A készlet nem haladhatja meg az 1 000 000 000 darabot.", field="quantity")
            timestamp = now()
            db.execute("UPDATE products SET stock=?,updated_at=? WHERE id=?", (stock, timestamp, product_id))
            product["stock"] = stock
            movement = self._log(db, product, kind, quantity, note, timestamp, request_id)
            return {"product": self.product(product_id, db), "movement": movement, "replayed": False}

    def movements(self, query):
        where, params = [], []
        search = query.get("q", "").strip()
        if search:
            where.append("(instr(casefold(product_name),casefold(?))>0 OR instr(casefold(product_sku),casefold(?))>0 OR instr(casefold(note),casefold(?))>0)")
            params.extend([search] * 3)
        if query.get("type"):
            if query["type"] not in ("in", "out", "opening"):
                raise AppError("Ismeretlen mozgástípus.")
            where.append("type=?")
            params.append(query["type"])
        if query.get("product_id"):
            try:
                product_id = int(query["product_id"])
                if not 1 <= product_id <= SQLITE_MAX_INTEGER:
                    raise ValueError
            except ValueError as exc:
                raise AppError("Érvénytelen termékazonosító.") from exc
            where.append("product_id=?")
            params.append(product_id)
        for key, operator in (("from", ">="), ("to", "<")):
            if query.get(key):
                try:
                    date = datetime.strptime(query[key], "%Y-%m-%d").replace(tzinfo=ZoneInfo("Europe/Budapest"))
                    if date.date().isoformat() != query[key]:
                        raise ValueError
                    if key == "to":
                        date += timedelta(days=1)
                    boundary = date.astimezone(timezone.utc).isoformat(timespec="milliseconds")
                except (ValueError, OverflowError) as exc:
                    raise AppError("Érvénytelen dátum. A formátum ÉÉÉÉ-HH-NN.") from exc
                where.append(f"created_at{operator}?")
                params.append(boundary)
        if query.get("from") and query.get("to") and query["from"] > query["to"]:
            raise AppError("A kezdődátum nem lehet későbbi a záródátumnál.")
        try:
            page, limit = int(query.get("page", 1)), int(query.get("limit", 20))
            if page < 1 or not 1 <= limit <= 100 or (page - 1) * limit > SQLITE_MAX_INTEGER:
                raise ValueError
        except ValueError as exc:
            raise AppError("Érvénytelen lapozási paraméter.") from exc
        condition = " WHERE " + " AND ".join(where) if where else ""
        with self.connection() as db:
            total = db.execute("SELECT count(*) FROM movements" + condition, params).fetchone()[0]
            rows = db.execute("SELECT * FROM movements" + condition + " ORDER BY id DESC LIMIT ? OFFSET ?", params + [limit, (page - 1) * limit]).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "page": page, "limit": limit}
