"""Exercise the real HTTP handlers using byte streams, without opening ports."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.database import Inventory
from backend.server import handler_for
from frontend_server import FrontendHandler


class Transport:
    def __init__(self, request):
        self.request = io.BytesIO(request)
        self.response = bytearray()

    def makefile(self, *args, **kwargs):
        return self.request

    def sendall(self, data):
        self.response.extend(data)

    def settimeout(self, seconds):
        pass


def exchange(handler, method, path, body=None, headers=None, raw=None, **kwargs):
    content = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    values = {"Host":"localhost", **(headers or {})}
    if content:
        values.setdefault("Content-Type","application/json")
        values.setdefault("Content-Length",str(len(content)))
    request = f"{method} {path} HTTP/1.0\r\n" + "".join(f"{key}: {value}\r\n" for key,value in values.items()) + "\r\n"
    transport = Transport(request.encode() + content)
    with patch.object(handler,"log_message"):
        handler(transport,("127.0.0.1",12345),None,**kwargs)
    head, payload = bytes(transport.response).split(b"\r\n\r\n",1)
    lines = head.decode().split("\r\n")
    response_headers = dict(line.split(": ",1) for line in lines[1:])
    return int(lines[0].split()[1]),response_headers,payload


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = Inventory(Path(self.temp.name) / "test.sqlite3")
        self.handler = handler_for(self.service,{"http://127.0.0.1:8080"})

    def request(self, method, path, **kwargs):
        status, headers, body = exchange(self.handler,method,path,**kwargs)
        return status,headers,json.loads(body) if body else None

    def test_full_product_and_movement_flow_through_http(self):
        status,headers,p = self.request("POST","/api/products",body={"name":"Papír","sku":"P1","initial_stock":10})
        self.assertEqual(status,201)
        self.assertEqual(headers["Content-Type"],"application/json; charset=utf-8")
        status,_,result = self.request("POST","/api/movements",body={"product_id":p["id"],"type":"in","quantity":5,"request_id":"HTTP-1"})
        self.assertEqual((status,result["product"]["stock"]),(201,15))
        status,_,result = self.request("POST","/api/movements",body={"product_id":p["id"],"type":"out","quantity":16})
        self.assertEqual(status,409)
        self.assertEqual(result["field"],"quantity")
        status,_,products = self.request("GET","/api/products")
        self.assertEqual(products["items"][0]["stock"],15)
        self.assertEqual(self.request("GET","/api/movements?type=in")[2]["total"],1)

    def test_put_preserves_stock(self):
        _,_,p = self.request("POST","/api/products",body={"name":"Papír","sku":"P1","initial_stock":10})
        status,_,updated = self.request("PUT",f"/api/products/{p['id']}",body={"name":"Új név","sku":"P1"})
        self.assertEqual((status,updated["stock"]),(200,10))

    def test_validation_error_is_json(self):
        status,_,error = self.request("POST","/api/products",body={"name":"","sku":"P1"})
        self.assertEqual((status,error["field"]),(400,"name"))

    def test_malformed_json(self):
        self.assertEqual(self.request("POST","/api/products",raw=b'{broken')[0],400)

    def test_json_array_is_rejected(self):
        self.assertEqual(self.request("POST","/api/products",body=[])[0],400)

    def test_content_type_and_size(self):
        self.assertEqual(self.request("POST","/api/products",raw=b"{}",headers={"Content-Type":"text/plain"})[0],415)
        self.assertEqual(self.request("POST","/api/products",headers={"Content-Type":"application/json","Content-Length":"999999"})[0],413)

    def test_allowed_cors_origin(self):
        status,headers,_ = self.request("OPTIONS","/api/products",headers={"Origin":"http://127.0.0.1:8080"})
        self.assertEqual(status,204)
        self.assertEqual(headers["Access-Control-Allow-Origin"],"http://127.0.0.1:8080")

    def test_untrusted_origin_cannot_mutate_stock(self):
        status,_,_ = self.request("POST","/api/products",body={"name":"Papír","sku":"P1"},headers={"Origin":"https://untrusted.example"})
        self.assertEqual(status,403)
        self.assertFalse(self.service.products())

    def test_unknown_endpoint_and_health(self):
        self.assertEqual(self.request("GET","/api/missing")[0],404)
        self.assertEqual(self.request("GET","/api/health")[2]["status"],"ok")

    def test_frontend_and_runtime_configuration(self):
        directory = str(Path(__file__).resolve().parents[1] / "frontend")
        status,headers,html = exchange(FrontendHandler,"GET","/",directory=directory)
        self.assertEqual(status,200)
        self.assertIn(b'lang="hu"',html)
        self.assertIn("Content-Security-Policy",headers)
        status,headers,script = exchange(FrontendHandler,"GET","/config.js",directory=directory)
        self.assertEqual(status,200)
        self.assertIn(b"8000",script)
        self.assertEqual(headers["Content-Type"],"text/javascript; charset=utf-8")

    def test_frontend_does_not_expose_database(self):
        directory = str(Path(__file__).resolve().parents[1] / "frontend")
        status,_,_ = exchange(FrontendHandler,"GET","/../data/inventory.sqlite3",directory=directory)
        self.assertEqual(status,404)


if __name__ == "__main__":
    unittest.main()
