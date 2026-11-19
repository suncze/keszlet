from concurrent.futures import ThreadPoolExecutor
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.database import Inventory, AppError, MAX_STOCK


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "inventory.sqlite3"
        self.service = Inventory(self.path)

    def product(self, **overrides):
        data = {"name":"Teszttermék", "sku":"TESZT-001", "initial_stock":10,
                "minimum_stock":5, "daily_usage":4, "lead_time":5, "safety_stock":6}
        data.update(overrides)
        return self.service.create(data)

    def move(self, product, kind="in", quantity=5, **extra):
        return self.service.move({"product_id":product["id"], "type":kind, "quantity":quantity, **extra})

    def test_01_create_product_and_opening_log(self):
        p = self.product(name="  Másolópapír  ",sku=" pap-001 ",initial_stock=0)
        self.assertEqual((p["name"],p["sku"],p["stock"]),("Másolópapír","PAP-001",0))
        self.assertEqual(len(self.service.products()),1)
        self.assertEqual(self.service.movements({})["total"],0)

    def test_02_invalid_name_duplicate_sku_and_negative_stock(self):
        self.product()
        for overrides in ({"name":"  "},{"sku":"teszt-001"},{"sku":"NEW","initial_stock":-1}):
            with self.subTest(overrides=overrides), self.assertRaises(AppError):
                self.product(**overrides)
        self.assertEqual(len(self.service.products()),1)

    def test_03_intake_10_plus_5_is_15_and_logged(self):
        result = self.move(self.product())
        self.assertEqual(result["product"]["stock"],15)
        movement = self.service.movements({})["items"][0]
        self.assertEqual((movement["type"],movement["quantity"],movement["stock_after"]),("in",5,15))

    def test_04_issue_all_stock_is_allowed(self):
        p = self.product()
        result = self.move(p,"out",10)
        self.assertEqual(result["product"]["stock"],0)

    def test_04_invalid_issues_leave_stock_and_log_unchanged(self):
        p = self.product()
        for quantity in (11,0,-1,1.5,True,"5",None):
            with self.subTest(quantity=quantity), self.assertRaises(AppError):
                self.move(p,"out",quantity)
            self.assertEqual(self.service.product(p["id"])["stock"],10)
            self.assertEqual(self.service.movements({})["total"],1)

    def test_05_movements_keep_product_type_quantity_and_time(self):
        p = self.product()
        self.move(p,"in",5,note="SZL-123")
        self.move(p,"out",2)
        rows = self.service.movements({})["items"]
        self.assertEqual([r["type"] for r in rows],["out","in","opening"])
        self.assertTrue(all(r["product_id"] == p["id"] and r["created_at"] for r in rows))
        self.assertEqual(rows[1]["note"],"SZL-123")

    def test_06_low_stock_includes_threshold(self):
        p = self.product(initial_stock=5,minimum_stock=5)
        self.assertTrue(p["is_low"])
        self.assertFalse(self.move(p,"in",1)["product"]["is_low"])

    def test_06_zero_stock_and_zero_minimum_is_low(self):
        self.assertTrue(self.product(initial_stock=0,minimum_stock=0)["is_low"])

    def test_07_reorder_specification_example_is_14(self):
        self.assertEqual(self.product(initial_stock=12)["reorder_quantity"],14)

    def test_07_reorder_never_negative(self):
        self.assertEqual(self.product(initial_stock=100)["reorder_quantity"],0)

    def test_07_zero_usage_and_lead_time(self):
        self.assertEqual(self.product(daily_usage=0,lead_time=0,initial_stock=2,safety_stock=6)["reorder_quantity"],4)

    def test_08_restart_preserves_products_and_movements(self):
        p = self.product()
        self.move(p,"in",7)
        before = (self.service.products(),self.service.movements({}))
        reopened = Inventory(self.path)
        self.assertEqual(before,(reopened.products(),reopened.movements({})))

    def test_invalid_parameters_are_rejected(self):
        for key in ("initial_stock","minimum_stock","daily_usage","lead_time","safety_stock"):
            for value in (-1,1.1,False,"3",None):
                with self.subTest(key=key,value=value), self.assertRaises(AppError):
                    self.product(**{key:value})

    def test_invalid_payloads_and_extra_fields_rejected(self):
        for data in (None,[],{"stock":10}):
            with self.subTest(data=data), self.assertRaises(AppError):
                self.service.create(data)

    def test_metadata_edit_cannot_modify_stock(self):
        p = self.product()
        data = {key:p[key] for key in ("name","sku","category","minimum_stock","daily_usage","lead_time","safety_stock")}
        with self.assertRaises(AppError):
            self.service.update(p["id"],{**data,"stock":99})
        edited = self.service.update(p["id"],{**data,"name":"Új név","sku":"UJ-001"})
        self.assertEqual(edited["stock"],10)
        opening = self.service.movements({})["items"][0]
        self.assertEqual((opening["product_name"],opening["product_sku"]),("Teszttermék","TESZT-001"))

    def test_edit_duplicate_sku_is_atomic(self):
        a = self.product()
        b = self.product(sku="B")
        data = {key:b[key] for key in ("name","sku","category","minimum_stock","daily_usage","lead_time","safety_stock")}
        with self.assertRaises(AppError):
            self.service.update(b["id"],{**data,"sku":a["sku"],"name":"Elvesző változás"})
        self.assertEqual(self.service.product(b["id"]),b)

    def test_movement_log_is_immutable_in_database(self):
        self.product()
        with self.service.connection() as db:
            for statement in ("UPDATE movements SET quantity=999", "DELETE FROM movements"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    db.execute(statement)

    def test_failed_log_insert_rolls_back_stock(self):
        p = self.product()
        with self.service.connection() as db:
            db.executescript("CREATE TRIGGER fail_test BEFORE INSERT ON movements WHEN NEW.quantity=777 BEGIN SELECT RAISE(ABORT,'injected failure'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            self.move(p,"in",777)
        self.assertEqual(self.service.product(p["id"])["stock"],10)
        self.assertEqual(self.service.movements({})["total"],1)

    def test_concurrent_issues_cannot_oversell(self):
        p = self.product()
        def issue(_):
            try:
                self.move(p,"out",1)
                return True
            except AppError:
                return False
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(issue,range(30)))
        self.assertEqual(sum(results),10)
        self.assertEqual(self.service.product(p["id"])["stock"],0)
        self.assertEqual(self.service.movements({"type":"out"})["total"],10)

    def test_retried_movement_is_idempotent(self):
        p = self.product()
        first = self.move(p,request_id="same-request")
        second = self.move(p,request_id="same-request")
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(second["product"]["stock"],15)
        self.assertEqual(first["movement"],second["movement"])
        with self.assertRaises(AppError):
            self.move(p,quantity=6,request_id="same-request")

    def test_parallel_duplicate_submission_is_applied_once(self):
        p = self.product()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.move(p,request_id="parallel-request"),range(12)))
        self.assertEqual(sum(not r["replayed"] for r in results),1)
        self.assertEqual(self.service.product(p["id"])["stock"],15)

    def test_stock_maximum_enforced(self):
        p = self.product(initial_stock=MAX_STOCK)
        with self.assertRaises(AppError):
            self.move(p,"in",1)
        self.assertEqual(self.service.product(p["id"])["stock"],MAX_STOCK)

    def test_search_and_type_and_pagination(self):
        p = self.product(name="VÉDŐKESZTYŰ")
        self.move(p,note="Szállítólevél")
        self.assertEqual(self.service.movements({"q":"védőkesztyű"})["total"],2)
        self.assertEqual(self.service.movements({"q":"szállítólevél","type":"in"})["total"],1)
        first = self.service.movements({"limit":"1"})
        second = self.service.movements({"limit":"1","page":"2"})
        self.assertGreater(first["items"][0]["id"],second["items"][0]["id"])

    def test_date_filter_uses_budapest_midnight(self):
        with patch("backend.database.now",return_value="2026-11-18T23:30:00.000+00:00"):
            self.product()
        self.assertEqual(self.service.movements({"from":"2026-11-19","to":"2026-11-19"})["total"],1)
        self.assertEqual(self.service.movements({"to":"2026-11-18"})["total"],0)

    def test_invalid_log_filters_rejected(self):
        for query in ({"page":"0"},{"limit":"101"},{"from":"invalid"},{"type":"invalid"},{"product_id":"abc"},{"from":"2026-02-02","to":"2026-02-01"}):
            with self.subTest(query=query), self.assertRaises(AppError):
                self.service.movements(query)

    def test_unknown_product(self):
        with self.assertRaises(AppError) as error:
            self.service.product(999)
        self.assertEqual(error.exception.status,404)

    def test_sql_metacharacters_are_data(self):
        p = self.product(name="<script>alert(1)</script>",sku="'; DROP TABLE products;--")
        self.assertEqual(len(self.service.products()),1)
        self.assertEqual(self.service.movements({"q":"DROP TABLE"})["total"],1)
        self.assertEqual(p["stock"],10)


if __name__ == "__main__":
    unittest.main()
