# Tesztelés és elfogadási feltételek

Futtatás a projekt gyökérkönyvtárából:

```bash
python3 -m unittest discover -v
```

## Automatizált ellenőrzés

2026. november 19-én a felülvizsgálat után **44 teszt sikeresen lefutott**, Python 3.14.8 és SQLite 3.53.4 használatával. Az eredeti verzió 38 tesztjéhez hat új regressziós teszt került.

A kibővített 44 teszt Python 3.11 alatt is sikeresen lefutott. A `verification.json` és a teljes mentett tesztnapló a Python 3.14.8-as futást rögzíti.

| Elfogadási feltétel | Automatizált lefedettség |
| --- | --- |
| 1. Érvényes termék létrehozása | Név és cikkszám normalizálása, nulla kezdőkészlet, listába kerülés; HTTP 201 |
| 2. Hibás termékadatok elutasítása | Üres név, kis/nagybetűben eltérő duplikált cikkszám, negatív és hibás típusú számok; nincs részleges mentés |
| 3. 10 + 5 = 15 bevételezés | Készlet és napló ellenőrzése az üzleti rétegben és a HTTP-kezelőn keresztül |
| 4. Teljes készlet kiadása és határesetek | 10 − 10 = 0; túladás, nulla, negatív, tört, szöveg és logikai érték elutasítása |
| 5. Készletmozgási napló | Termék, típus, mennyiség, új készlet, időpont, megjegyzés; keresés, típus, dátum, lapozás |
| 6. Alacsony készlet | Küszöbön igaz, küszöb felett hamis; nulla készlet és nulla minimum kezelése |
| 7. Utánrendelés | A specifikáció 14 db-os példája, negatív eredmény helyett nulla, nulla napi fogyás |
| 8. Adatok megőrzése | Új adatbázis-kapcsolat, új szolgáltatáspéldány és két külön Python-folyamat után az adatok és naplók változatlanok |

## Kiemelt tesztesetek

| Eset | Futtatható bizonyíték a `tests/test_inventory.py` fájlban |
| --- | --- |
| Normál működés | `test_03_intake_10_plus_5_is_15_and_logged` |
| Első érdemi határ | `test_04_issue_all_stock_is_allowed`: pontosan a teljes készlet kiadása |
| Második érdemi határ | `test_06_low_stock_includes_threshold`: minimumon alacsony, fölötte nem |
| Hibás bemenet | `test_04_invalid_issues_leave_stock_and_log_unchanged`: nulla, negatív, tört és hibás típus |
| Regresszió | `test_08_restart_preserves_products_and_movements`, `test_metadata_edit_cannot_modify_stock` |

A tesztnevek nem pusztán dokumentációs címkék: a megadott metódusok a tesztfuttatóval külön is végrehajthatók.

## Hibás és javított változat, megőrzött futási eredmények

```bash
python3 scripts/defect_demo.py
python3 scripts/verify.py
```

**Szándékos hibainjektálás:** a `defect_demo.py` elkülönített másolatban `<=` helyett `<` összehasonlítást használ. Ez nem tényleges korábbi fejlesztési hiba. Ugyanaz a küszöbteszt a hibás változaton elbukik (kilépési kód 1), a javítotton átmegy (0). Mindkét teljes forrás, a tesztpillanatkép, a két napló és az ellenőrzőösszegek megmaradnak a `docs/evidence/defect/` könyvtárban.

**Regressziós tesztek:** a `tests/test_review.py` az API-azonosítók, a lapozás, a dátumformátumok és a normalizált cikkszám szélsőértékeit ellenőrzi. A hibás értékek megfelelő 400/404 választ kapnak. Külön teszt igazolja, hogy két külön Python-folyamat között is megmaradnak a mentett termékek és készletmozgások.

**Teljes ellenőrzés:** a `verify.py` a valódi tesztkimenetet `docs/evidence/test-results.txt` néven, a környezetet és kilépési kódot `verification.json` néven őrzi meg. Ellenőrzi a specifikáció hosszát és nyolc számozott feltételét és a Python-szintaxist is.

További regressziós ellenőrzések:

- Harminc párhuzamos, egy darabos kiadás tíz darab készletből: pontosan tíz sikeres kiadás, nulla maradék.
- Tizenkét párhuzamosan ismételt, azonos azonosítójú bevételezés: egyetlen készletváltozás.
- Készlet és napló közös visszagörgetése mesterséges naplóírási hiba esetén.
- Közvetlen naplómódosítás és törlés tiltása adatbázis-triggerrel.
- A termék átnevezése nem írja át a napló korábbi nevét és cikkszámát.
- Készlet közvetlen szerkesztésének tiltása; cikkszámütközés esetén teljes visszagörgetés.
- Felső mennyiségi korlát, hibás JSON, hibás tartalomtípus, túl nagy kérés.
- Engedélyezett CORS, nem megbízható eredet visszautasítása, állapotvégpont.
- Budapest éjfélhatárának ellenőrzése UTC-tárolás mellett.
- Unicode kis/nagybetű-független naplókeresés és SQL-metakarakterek adatként kezelése.
- Frontend HTML, biztonsági fejlécek és dinamikus API-konfiguráció kiszolgálása; adatbázisfájl elérésének tiltása.

Az HTTP-tesztek a tényleges `BaseHTTPRequestHandler` implementációt és a tényleges SQLite-szolgáltatást használják, HTTP-bájtsorozatokkal. Nem hálózati kapcsolaton futnak, és nem helyettesítik az élő böngészős tesztet.

A JavaScript szintaxisát Node.js fordítóval külön ellenőriztük. A program futtatásához Node.js nem szükséges.

## Ellenőrzési korlát

A fejlesztési környezet elutasította a helyi TCP-portok megnyitását (`PermissionError: Operation not permitted`). Emiatt a két kiszolgáló együttes, élő hálózati indítását és a böngészős működést itt nem lehetett végigellenőrizni. A csomagban nincs olyan állítás, hogy az alábbi kézi böngészős lépések lefutottak.

## Kézi böngészős ellenőrzés

A részletes bemenet–lépés–elvárt eredmény táblázat és a tényleges eredmény rögzítésére szolgáló oszlop: [docs/KEZI_TESZTEK.md](docs/KEZI_TESZTEK.md). Az ottani esetek státusza még nem végrehajtott. Az alábbi rövid lista csak áttekintés.

1. `python3 start.py --demo`; nyisd meg a `http://127.0.0.1:8080` címet.
2. Keresd a `PAP-001` terméket; az Utánrendelés nézetben ellenőrizd a 14 db-os javaslatot.
3. Vegyél fel egy új terméket 10 db kezdőkészlettel; üres névvel és foglalt cikkszámmal ellenőrizd a hibaüzeneteket.
4. Rögzíts 5 db bevételezést; az aktuális készlet 15 db legyen, és a naplóban jelenjen meg a művelet.
5. Adj ki 15 db-ot; a készlet 0 db legyen. Próbálj még 1 db-ot kiadni: a művelet ne sikerüljön.
6. Szerkeszd a termék nevét és paramétereit. A készlet közvetlen módosítására ne legyen mező; a napló korábbi adatai maradjanak meg.
7. Próbáld ki a kategória- és állapotszűrést, rendezést, lapozást és CSV-exportot.
8. A naplóban próbáld ki a szöveg-, termék-, típus- és dátumszűrést, valamint azok törlését.
9. Állítsd le és indítsd újra a programot; a saját termékek és mozgások maradjanak meg.
10. Ellenőrizd 390 px szélességen és billentyűzettel: alsó navigáció, vízszintesen görgethető táblázat, párbeszédablak, Tab, Escape és fókuszjelölés.
