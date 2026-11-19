# Fejlesztési útmutató MI-asszisztenseknek

## Kontextus

Először olvasd el a `SPECIFIKACIO.md` és `TESZTELES.md` dokumentumokat.
A projekt egyetlen raktárat kezel, bejelentkezés nélkül. Csak a kért funkciókat valósítsd meg.

## Megőrzendő szabályok

- A készlet csak pozitív egész bevételezéssel/kiadással változik; nulla alá nem csökkenhet.
- A készlet és napló közös SQLite-tranzakcióban módosul.
- A napló utólag nem szerkeszthető; a meglévő adatok nem törölhetők.
- Alacsony készlet: `stock <= minimum_stock`.
- Rendelési javaslat: `max(0, daily_usage * lead_time + safety_stock - stock)`.
- Ne módosítsd a felhasználó `data/` adatbázisát tesztelés céljából.
- Minden HTML-be kerülő felhasználói adatot kódolj; az SQL paraméterezett maradjon.

## Munkamódszer

Az érintett működési szabályt azonosítsd, a hibát lehetőleg előbb regressziós teszttel mutasd ki.
Python 3.11+ és standard könyvtár használatos; új függőséget csak indokolt esetben vezess be.
Az érdemi szabályváltozást a specifikációhoz és a tesztekhez is vezesd át.

```bash
python3 -m unittest discover -v
python3 scripts/verify.py
python3 scripts/defect_demo.py
```

Az utolsó parancs egy szándékosan hibássá tett, elkülönített másolatot ellenőriz.
A működő alkalmazást és saját adatbázisát nem módosíthatja.
A teszteredményeket tartsd meg; böngészős ellenőrzést csak tényleges használat után jelölj sikeresnek.

## Dokumentáció

Frissítsd az érintett műszaki leírásokat és a változásnaplót.
Az alkalmazás működését, a döntéseket és a tényleges ellenőrzéseket dokumentáld.
Ne állíts közzétételt vagy sikeres ellenőrzést bizonyíték nélkül.
