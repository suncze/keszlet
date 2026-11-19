# REST API

Alapcím: `http://127.0.0.1:8000`. A törzset tartalmazó kérések tartalomtípusa `application/json`. Az API UTF-8 JSON-válaszokat küld. Legfeljebb 16 KiB-os kérés fogadható el.

| Metódus | Útvonal | Sikeres válasz |
| --- | --- | --- |
| GET | `/api/health` | 200, állapot és verzió |
| GET | `/api/products` | 200, `{ "items": [...] }` |
| GET | `/api/products/{id}` | 200, egy termék |
| POST | `/api/products` | 201, létrehozott termék |
| PUT | `/api/products/{id}` | 200, módosított termék |
| GET | `/api/movements` | 200, lapozható mozgásnapló |
| POST | `/api/movements` | 201, készletváltozás és mozgás; ismétléskor 200 |

## Termék létrehozása

```json
{
  "name": "Másolópapír A4",
  "sku": "PAP-001",
  "category": "Irodaszer",
  "initial_stock": 12,
  "minimum_stock": 15,
  "daily_usage": 4,
  "lead_time": 5,
  "safety_stock": 6
}
```

A `name` és `sku` kötelező. A kategória alapértéke üres szöveg, a numerikus mezőké 0. A számokat JSON egész számként kell küldeni; szöveg, tört vagy logikai érték nem fogadható el. Az üres vagy csak szóközökből álló név és cikkszám hibás. A név legfeljebb 160, a cikkszám 64, a kategória 80 karakteres lehet. A cikkszámot a szerver nagybetűsíti.

A cikkszámra a 64 karakteres korlát a nagybetűsítés után is érvényes, mert egyes Unicode-karakterek átalakításkor hosszabbá válnak.

Válasz a mentett és számított mezőkkel:

```json
{
  "id": 1,
  "name": "Másolópapír A4",
  "sku": "PAP-001",
  "category": "Irodaszer",
  "stock": 12,
  "minimum_stock": 15,
  "daily_usage": 4,
  "lead_time": 5,
  "safety_stock": 6,
  "created_at": "2026-11-19T10:00:00.000+00:00",
  "updated_at": "2026-11-19T10:00:00.000+00:00",
  "is_low": true,
  "reorder_quantity": 14,
  "coverage_days": 3.0
}
```

A `coverage_days` a készlet / napi fogyás értéke, egy tizedesre kerekítve; nulla napi fogyásnál `null`. A rendelési javaslat mindig egész darabszám.

## Termék szerkesztése

A `PUT` teljes metaadatcserét végez. A `name` és `sku` kötelező; az elhagyott kategória üresre, a tervezési paraméterek 0-ra állnak. A frontend mindig minden metaadatmezőt elküld.

```json
{
  "name": "Másolópapír A4, 80 g",
  "sku": "PAP-001",
  "category": "Irodaszer",
  "minimum_stock": 15,
  "daily_usage": 4,
  "lead_time": 5,
  "safety_stock": 6
}
```

A `stock` és `initial_stock` mezők módosításkor nem engedélyezettek. Az ismeretlen mezőket a szerver elutasítja. Termék- és mozgástörlésre nincs végpont.

## Készletmozgás

```json
{
  "product_id": 1,
  "type": "in",
  "quantity": 5,
  "note": "SZL-2026-0148",
  "request_id": "egyedi-muveletazonosito-001"
}
```

- `product_id`: kötelező pozitív egész termékazonosító.
- `type`: `in` (bevételezés) vagy `out` (kiadás).
- `quantity`: pozitív egész mennyiség, legfeljebb 1 milliárd.
- `note`: opcionális megjegyzés, legfeljebb 500 karakter.
- `request_id`: opcionális, legfeljebb 80 karakteres egyedi azonosító. Az ismételhető klienskérések mindig adják meg. Elhagyásakor a szerver generál egyet, ilyenkor a kliensismétlés nem deduplikálható.

Válasz: `{ "product": {...}, "movement": {...}, "replayed": false }`.

Azonos azonosító és tartalom ismétlésekor a meglévő mozgás és az aktuális termékállapot érkezik vissza `replayed: true` értékkel; új készletművelet nem történik. Azonos azonosító eltérő tartalommal 409-es hiba.

A naplóban az `opening` típus a termék létrehozásakor automatikusan rögzített pozitív nyitókészlet. Ezt a kliensek nem hozhatják létre közvetlenül.

## Napló lekérdezése

```text
GET /api/movements?q=pap%C3%ADr&type=out&from=2026-11-01&to=2026-11-30&page=1&limit=20
```

| Paraméter | Jelentés |
| --- | --- |
| `q` | Részszöveg a korabeli terméknévben, cikkszámban vagy megjegyzésben; Unicode kis/nagybetű-független |
| `type` | `in`, `out` vagy `opening` |
| `product_id` | Egyetlen termék előzményei |
| `from` | Első nap, beleértve; `YYYY-MM-DD` |
| `to` | Utolsó nap, beleértve; `YYYY-MM-DD` |
| `page` | Pozitív oldalszám, alapérték 1 |
| `limit` | Oldalméret 1–100, alapérték 20 |

A dátumszűrés Budapest időzónája szerinti teljes napokra vonatkozik, a téli/nyári időszámítás figyelembevételével. A rendezés csökkenő mozgásazonosító szerinti. Az egyesítetten használt szűrők ÉS kapcsolatban állnak.

A dátum csak pontos `YYYY-MM-DD` formában fogadható el; a UTC-határra alakításkor túlcsorduló dátum 400-as hibát kap. A termékazonosítók és lapozási eltolások nem léphetik túl az SQLite 64 bites egészszám-tartományát; ezek hibás értékei nem okoznak belső szerverhibát.

Válasz: `{ "items": [...], "total": 42, "page": 1, "limit": 20 }`.

## Hibák

```json
{
  "error": "Nincs elegendő készlet. Elérhető: 10 db.",
  "field": "quantity"
}
```

| HTTP-kód | Jelentés |
| --- | --- |
| 400 | Hibás adat, JSON vagy szűrő |
| 403 | Nem engedélyezett böngészős eredet |
| 404 | Ismeretlen termék vagy végpont |
| 409 | Foglalt cikkszám, elégtelen készlet vagy ütköző műveletazonosító |
| 413 | Hiányzó vagy túl nagy kérésméret |
| 415 | Nem JSON tartalomtípus |
| 500 | Belső hiba; részletei csak a szerver naplójába kerülnek |

A mezőhöz nem köthető hibánál a `field` hiányozhat vagy `null`. Hibás készletmozgás esetén a készlet és a napló változatlan.
