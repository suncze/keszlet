"""Regression checks for API input boundaries and persistent storage."""
import json
import logging
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.database import Inventory, AppError
from backend.server import handler_for
from tests.test_http import exchange


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "review.sqlite3"
        self.service = Inventory(self.path)
        self.handler = handler_for(self.service,set())

    def request(self, method, path, **kwargs):
        with patch.object(logging,"exception"):
            status,_,raw = exchange(self.handler,method,path,**kwargs)
        return status,json.loads(raw)

    def test_extreme_date_is_validation_error_not_server_error(self):
        for key,value in (("to","9999-12-31"),("from","0001-01-01"),("to","2026-2-3")):
            with self.subTest(key=key,value=value):
                self.assertEqual(self.request("GET",f"/api/movements?{key}={value}")[0],400)

    def test_extreme_query_numbers_do_not_crash_sqlite(self):
        for query in ("product_id="+"9"*100,"page="+"9"*100):
            with self.subTest(query=query):
                self.assertEqual(self.request("GET","/api/movements?"+query)[0],400)

    def test_extreme_and_non_ascii_product_id_is_not_server_error(self):
        for identifier in ("9"*100,"²"):
            with self.subTest(identifier=identifier):
                self.assertEqual(self.request("GET","/api/products/"+identifier)[0],404)

    def test_sku_limit_applies_after_uppercase_normalization(self):
        with self.assertRaises(AppError) as error:
            self.service.create({"name":"Termék","sku":"ß"*64})
        self.assertEqual(error.exception.field,"sku")
        self.assertFalse(self.service.products())

    def test_invalid_intakes_leave_stock_and_log_unchanged(self):
        product = self.service.create({"name":"Papír","sku":"P1","initial_stock":10})
        for quantity in (0,-1,2.5,"2",True):
            with self.subTest(quantity=quantity):
                status,_ = self.request("POST","/api/movements",body={"product_id":product["id"],"type":"in","quantity":quantity})
                self.assertEqual(status,400)
                self.assertEqual(self.service.product(product["id"])["stock"],10)
                self.assertEqual(self.service.movements({})["total"],1)

    def test_real_process_restart_preserves_all_saved_data(self):
        root = Path(__file__).resolve().parents[1]
        create = "from backend.database import Inventory; import sys; s=Inventory(sys.argv[1]); p=s.create({'name':'Tartós termék','sku':'SAVE','initial_stock':10}); s.move({'product_id':p['id'],'type':'in','quantity':5})"
        read = "from backend.database import Inventory; import json,sys; s=Inventory(sys.argv[1]); print(json.dumps({'products':s.products(),'movements':s.movements({})}))"
        subprocess.run([sys.executable,"-c",create,str(self.path)],cwd=root,check=True,capture_output=True,text=True)
        expected = {"products":self.service.products(),"movements":self.service.movements({})}
        actual = subprocess.run([sys.executable,"-c",read,str(self.path)],cwd=root,check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(actual.stdout),expected)
        self.assertEqual(expected["products"][0]["stock"],15)


if __name__ == "__main__":
    unittest.main()
