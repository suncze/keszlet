# Reprodukálható kézi és vizuális ellenőrzések

**Állapot: a jelen környezetben nem végrehajtott.** Az automatizált tesztek nem helyettesítik a teljes böngészős használatot. Az eredményeket a tényleges futtató rögzíti az utolsó oszlopban, dátummal.

## Előfeltétel

Python 3.11+, a helyi portok használata engedélyezett. Válassz korábban nem használt tesztadatbázis-fájlnevet, hogy meglévő adatok ne befolyásolják a próbát. Például:

```bash
python3 start.py --db data/kezi-proba-01.sqlite3
```

Nyisd meg a `http://127.0.0.1:8080` címet. A program kezdetben üres. Ezt a külön tesztadatbázist használd, ne a saját üzemi adatokat. Új próbához másik fájlnevet válassz.

## Esetek

| Azonosító / feltétel | Lépések és bemenet | Elvárt, megfigyelhető eredmény | Tényleges eredmény |
| --- | --- | --- | --- |
| K1 / 1, normál | Új termék: név Tesztpapír, cikkszám KEZI-001, kategória Irodaszer, kezdőkészlet 10, minimum 5, napi fogyás 4, beszerzési idő 5, biztonsági készlet 6; mentés | Párbeszédablak bezárul, sikerjelzés; a listában 10 db és Rendben állapot; 10 db-os nyitónapló | 2026.11.16. – Sikeres. A Teszt laptop (TEST-001) termék létrejött, megjelent a terméklistában, 10 db kezdőkészlettel. |
| K2 / 2, hibás | Új termék üres névvel; majd más névvel és kezi-001 cikkszámmal; majd egyedi cikkszámmal −1 kezdőkészlettel | Mindhárom mentést látható hiba gátolja; nem nő a termékek száma | 2026.11.16 – Sikeres. A rendszer elutasította a mentést, és jelezte a hibát. A termék nem jött létre. |
| K3 / 3, normál | KEZI-001 → Mozgás → Bevételezés 5 db, megjegyzés Tesztbevétel → rögzítés | Készlet 15 db; a naplóban egy új +5 bevételezés, új készlet 15, időpont és megjegyzés | 2026.11.19 – Sikeres. A TEST-001 termék készlete 10-ről 15 db-ra nőtt 5 db bevételezése után. A művelet megjelent a mozgásnaplóban. |
| K4 / 4 és 6, határ | Adj ki 10 db-ot a 15-ből; majd vételezz be 1 db-ot | Először 5 db, Alacsony készlet; aztán 6 db, Rendben. A minimumon figyelmeztet, fölötte nem | 2026.11.19 – Sikeres. A TEST-001 termékből 5 db kiadása után a készlet 15-ről 10 db-ra csökkent, a művelet megjelent a mozgásnaplóban. A 11 db-os kiadási kísérletet az alkalmazás elutasította, a készlet változatlan maradt. |
| K5 / 4, határ és hibás | 6 db készletből adj ki 6-ot; majd próbálj 1, 0, −1, illetve 2,5 db-ot kiadni | Az első sikerül, 0 db és Elfogyott jelzés. A további műveletek elutasítva; készlet 0, a napló nem kap hibás műveletet | Nem végrehajtott |
| K6 / 7, képlet | Új termék: KEZI-002, kezdőkészlet 12, napi fogyás 4, beszerzési idő 5, biztonsági készlet 6; nézd meg az Utánrendelés nézetet | KEZI-002 javaslata 14 db. Az oldal megnyitása nem változtatja a készletet, és nem hoz létre mozgást | Nem végrehajtott |
| K7 / 5, kereshetőség és regresszió | KEZI-001 sorának óra ikonja; szűrés Bevétel típusra és Tesztbevétel szóra; majd Szűrés törlése. Szerkeszd a termék nevét Új tesztpapírra, és nézd meg a naplót | A termékszűrés látszik; a keresett mozgás visszakereshető; a szűrő törölhető. A korábbi napló a korábbi Tesztpapír nevet őrzi. Nincs naplószerkesztés/törlés | Nem végrehajtott |
| K8 / 8, megőrzés | Jegyezd fel a két termék készletét és a napló darabszámát. Ctrl+C, majd azonos `--db` paraméterrel újraindítás; oldalfrissítés | Ugyanazok a termékek, készletek és naplók jelennek meg; nem jön létre új nyitókészlet | Nem végrehajtott |
| K9 / felület | 390 px szélesség; válts a három nézet között; görgesd a táblázatot; nyiss és zárj termékűrlapot | Alsó navigáció használható; táblázat vízszintesen görgethető; a mezők és műveletgombok elérhetők | Nem végrehajtott |
| K10 / akadálymentes használat | Egér nélkül Tab/Shift+Tab, Enter a gombokon, Escape a párbeszédablakban; próbálj hibás űrlapot menteni | Látható fókusz; megnyitható és bezárható űrlap; mentéskor a hibás mező fókuszt és olvasható hibaüzenetet kap | Nem végrehajtott |
| K11 / export | Szűrj Irodaszer kategóriára, exportálj; nyisd meg UTF-8 CSV-ként pontosvesszővel | Az összes szűrt termék, helyes magyar karakterek és mennyiségek jelennek meg; a készlet nem változik | Nem végrehajtott |

Ha eltérés van, rögzítsd a böngészőt, a lépéseket, a várt és tényleges eredményt; javítás után ismételd meg az érintett és regressziós eseteket.
