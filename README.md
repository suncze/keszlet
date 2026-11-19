# készlet.

Magyar nyelvű készletkezelő és beszerzéstámogató webalkalmazás kisvállalkozások számára.

Külön frontend, REST API és fájlalapú SQLite-adatbázis. Nincs szükség Node.js-re, csomagtelepítésre, külső szolgáltatásra vagy internetkapcsolatra.

## Gyors indítás

**Környezet:** Python 3.11 vagy újabb, macOS vagy Linux. A rendszernek rendelkeznie kell az `Europe/Budapest` időzóna adataival; ezek a szokásos macOS- és Linux-telepítések részei.

1. Nyiss terminált a projekt gyökérkönyvtárában, ahol a `start.py` található.
2. Indítsd el a programot:

```bash
python3 start.py
```

3. Nyisd meg: **http://127.0.0.1:8080**

**Kipróbáláshoz bemutatóadatokkal:**

```bash
python3 start.py --demo
```

A bemutató 12 terméket és készletmozgásokat tartalmaz. Csak üres adatbázist tölt fel; meglévő adatokat nem módosít. A bemutatóban a `PAP-001` cikkszámú termék készlete 12 db, napi fogyása 4 db, beszerzési ideje 5 nap, biztonsági készlete 6 db: a javaslat pontosan **14 db**.

Leállítás: **Ctrl+C**. Ez mindkét kiszolgálót leállítja. A mentett adatok megmaradnak.

Ha valamelyik port foglalt:

```bash
python3 start.py --port 8090 --api-port 8010
```

Ekkor a felület: `http://127.0.0.1:8090`. Az API-címet a frontend automatikusan átveszi.

Külön adatbázis használatához:

```bash
python3 start.py --db data/sajat-raktar.sqlite3
```

## Fő funkciók

- Reszponzív magyar kezelőfelület asztali és mobilnézettel.
- Termék létrehozása és adatainak szerkesztése, egyedi cikkszámmal és opcionális kategóriával.
- Kezdőkészlet rögzítése; a pozitív nyitókészlet önálló naplóbejegyzést kap.
- Bevételezés és kiadás, készletelőnézettel és opcionális megjegyzéssel.
- Szerver- és kliensoldali ellenőrzések, mezőhöz kötött hibaüzenetek.
- Keresés név, cikkszám és kategória alapján; állapot- és kategóriaszűrés, rendezés, lapozás.
- Alacsony készlet jelzése a minimum elérésekor is; külön jelzés a nulla készletnek.
- Utánrendelési lista, a számítás bemeneti adataival és javasolt mennyiségeivel.
- Időrendben visszakereshető mozgásnapló; termék-, szöveg-, típus- és dátumszűrés.
- Készlet- és beszerzési lista CSV-exportja az aktuális szűrés szerint, az összes szűrt sorral.
- Áttekintő mutatók és legutóbbi készletmozgások.

## Használat

**Új termék:** az „Új termék” gombbal add meg a nevet, cikkszámot, kezdőkészletet és a készletkezelési adatokat. A cikkszámot a program nagybetűsíti, a kis- és nagybetűs változatok ugyanannak számítanak.

**Készletváltozás:** a termék sorában a „Mozgás” gombbal válassz bevételezést vagy kiadást. Csak pozitív egész darabszám adható meg. A teljes készlet kiadható, a rendelkezésre állónál több nem. A készlet a termékszerkesztőben nem írható át.

**Utánrendelés:** a lista csak a pozitív rendelési javaslatokat mutatja. Képlete:

```text
max(0, napi fogyás × beszerzési idő + biztonsági készlet − aktuális készlet)
```

A minimumkészlet a figyelmeztetés küszöbe; a biztonsági készlet az utánrendelési képlet egyik bemenete. Ezért egy alacsony készletű terméknek is lehet nulla a rendelési javaslata. A napi fogyás kézzel megadott tervezési paraméter, nem a naplóból számított érték. A javaslat nem hoz létre rendelést és nem változtat készletet.

**Napló:** a sor végén látható óra ikonnal közvetlenül a termék előzményeire szűrhetsz. A „Törlés” gomb a szűrőket törli; naplóbejegyzést nem töröl. Az időpontok és dátumszűrések Budapest időzónáját használják. Az adatbázis az időpontokat UTC-ben tárolja.

## Felépítés

| Elem | Technológia | Feladat |
| --- | --- | --- |
| Frontend | HTML5, CSS, natív JavaScript | Képernyők, űrlapok, keresés, CSV-export |
| Frontend-kiszolgáló | Python `http.server` | Statikus felület és futásidejű API-konfiguráció |
| Backend | Python, JSON REST API | Ellenőrzések, üzleti szabályok, készletműveletek |
| Adatbázis | SQLite, WAL | Tartós termék- és mozgástárolás |
| Tesztek | Python `unittest` | Üzleti, tranzakciós és HTTP-ellenőrzések |

A frontend és a backend külön folyamatban és porton fut. A `start.py` a közös indító. Az API önállóan is használható.

```text
keszletkezelo/
  backend/
    database.py         Adatmodell, ellenőrzések, tranzakciók
    server.py           HTTP API
  frontend/
    index.html          Felület
    styles.css          Reszponzív megjelenés
    app.js              Klienslogika
    favicon.svg         Alkalmazásikon
  tests/                Automatizált tesztek
  frontend_server.py    Frontend-kiszolgáló
  seed_demo.py          Opcionális bemutatóadatok
  start.py              Közös indítás
  API.md                API-referencia
  TESZTELES.md          Elfogadási feltételek és ellenőrzés
```

## Adatbiztonság és megőrzés

- Az alapértelmezett adatbázis: `data/inventory.sqlite3`, a projekt mappáján belül. Első indításkor automatikusan létrejön.
- A backend újraindítása nem hozza létre újra és nem üríti az adatokat.
- A készletváltozás és a naplóírás közös `BEGIN IMMEDIATE` tranzakcióban történik. Párhuzamos kiadások nem adhatnak el többet a rendelkezésre álló készletnél.
- A mozgások terméknevet és cikkszámot is tárolnak, így a napló egy későbbi átnevezés után is megőrzi az eredeti adatokat.
- Adatbázis-triggerek tiltják a napló utólagos módosítását és törlését.
- A kliens műveletazonosítót küld. Ugyanannak a készletmozgásnak az ismételt beküldése nem változtatja meg másodszor a készletet.
- Paraméterezett SQL, HTML-kimenetkódolás, CSV-képletvédelem, kérésméret-korlát és szűkített CORS védi az adatkezelést.

**Mentés:** állítsd le a programot, majd másold el a teljes `data` könyvtárat. Visszaállításkor szintén álljon a program. A fő SQLite-fájlt futás közben önmagában ne másold, mert a WAL-fájlban is lehetnek friss adatok.

## Tesztelés

```bash
python3 -m unittest discover -v
```

A tesztek ideiglenes adatbázisokat használnak, a saját és a bemutatóadatokat nem módosítják. Részletek: [TESZTELES.md](TESZTELES.md).

## Dokumentáció

| Anyag | Hivatkozás |
| --- | --- |
| Működési szabályok és elfogadási feltételek | [SPECIFIKACIO.md](SPECIFIKACIO.md) |
| Műszaki döntések és MI-támogatott fejlesztés | [docs/MI_HASZNALAT.md](docs/MI_HASZNALAT.md) |
| MI-fejlesztési útmutató és ellenőrző parancsok | [AGENTS.md](AGENTS.md), `scripts/` |
| Automatizált és kézi ellenőrzés, hibás/javított bizonyíték | [TESZTELES.md](TESZTELES.md), [docs/KEZI_TESZTEK.md](docs/KEZI_TESZTEK.md), `docs/evidence/` |
| Változásnapló | [docs/VERZIOK.md](docs/VERZIOK.md) |

Bizonyítékok megismétlése:

```bash
python3 scripts/verify.py
python3 scripts/defect_demo.py
```

A `defect_demo.py` akkor sikeres, ha az elkülönített, szándékosan hibás kódon elbukik a teszt, a javítotton pedig átmegy. A működő alkalmazás és saját adatbázisa nem sérül.

## Önálló komponensek

A projekt mappájából, két terminálban:

```bash
python3 -m backend.server --port 8000 --frontend-port 8080
```

```bash
python3 frontend_server.py --port 8080 --api-port 8000
```

Opcionális környezeti változók: `INVENTORY_DB` az adatbázis helyéhez; `ALLOWED_ORIGINS` további, vesszővel elválasztott frontend-eredetekhez. A normál helyi indításhoz egyik sem szükséges.

## Határok

Az alkalmazás egyetlen raktárt és egy készletkezelő szerepkört kezel, bejelentkezés nélkül. A kiszolgálók csak a helyi gépről elérhető `127.0.0.1` címen figyelnek. Internetes üzemeltetéshez HTTPS, hitelesítés és erre alkalmas alkalmazáskiszolgáló szükséges.

A készlet és a mozgás mennyisége legfeljebb 1 milliárd db lehet; a tervezési paraméterek legfeljebb 1 millió nemnegatív egész értéket fogadnak el. A kezdőkészlet nemnegatív, a készletmozgás mennyisége szigorúan pozitív. Ezeket a korlátokat a backend is ellenőrzi.
