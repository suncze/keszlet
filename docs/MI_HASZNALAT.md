# MI-támogatott fejlesztés és műszaki döntések

## Eszköz és munkamódszer

A fejlesztésben Codex, GPT-6-alapú asszisztens működött közre. A pontos modell-buildazonosító nem ismert. Az alkalmazás futtatása nem igényel MI-szolgáltatást.

| Fejlesztési fázis | Átadott kontextus | Eredmény és ellenőrzés |
| --- | --- | --- |
| Elemzés | Egyetlen raktár, nyolc elfogadási feltétel, készletmozgások és rendelési képlet | `SPECIFIKACIO.md`; a feltételek és tesztek kapcsolata a `TESZTELES.md` fájlban |
| Implementáció | Külön frontend/backend, tartós tárolás, negatív készlet tiltása | `backend/`, `frontend/`; tranzakciós és HTTP-tesztek |
| Tesztelés | Normál, határ-, hibás és regressziós esetek; reprodukálható eredmények | `tests/`, `scripts/`, `docs/evidence/` |

A kontextusok tartalmi összefoglalók. Az alábbi technikai döntéseket az asszisztens javasolta és valósította meg; nem tulajdonítjuk őket más közreműködőnek.

## 1. Minimumkészlet és biztonsági készlet elkülönítése

**Probléma:** a két készletparaméter eltérő szabályt vezérel.

**Eszköz és kontextus:** Codex; az alacsony készlet jelzése és a konkrét 4 × 5 + 6 − 12 rendelési példa. A feladat a két szabály pontos megvalósítása volt.

**Javaslat és döntés:** a minimum a `stock <= minimum_stock` figyelmeztetéshez tartozik. A biztonsági készlet a rendelési képletben szerepel. Külön paraméter és külön számítás maradt, mert egy figyelmeztetett terméknek is lehet nulla rendelési javaslata.

**Ellenőrzés:** `backend/database.py::enrich`; a `tests/test_inventory.py` fájlban `test_06_low_stock_includes_threshold`, `test_06_zero_stock_and_zero_minimum_is_low`, `test_07_reorder_specification_example_is_14`, `test_07_reorder_never_negative`. Az eredmény a konkrét példánál 14 db; a minimumon lévő készlet alacsony.

**Korlát:** az adatok helyességét automatikusan ellenőrizzük; a figyelmeztetés megjelenítését a kézi tesztterv tartalmazza.

## 2. Készletváltozás és naplózás közös tranzakcióban

**Probléma:** párhuzamos kiadások vagy hibás naplóírás mellett is helyesnek kell maradnia a készletnek.

**Eszköz és kontextus:** Codex; bevételezés, kiadás, megőrzött előzmények, tartós SQLite-tárolás és a negatív készlet tiltása.

**Javaslat és döntés:** a készlet ellenőrzése, frissítése és a naplóbeszúrás `BEGIN IMMEDIATE` tranzakcióba került. A frontend ellenőrzése a kitöltést segíti; az adatokat a backend védi. A műveletazonosító lehetővé teszi az ismételt kérés egyszeri végrehajtását. Az eredeti név és cikkszám a naplóban is tárolódik.

**Ellenőrzés:** `Inventory.transaction`, `Inventory.move`, `_log`; `test_concurrent_issues_cannot_oversell`, `test_failed_log_insert_rolls_back_stock`, `test_parallel_duplicate_submission_is_applied_once`, `test_metadata_edit_cannot_modify_stock`. Harminc kiadási kísérletből tíz sikerül tíz darab készlet mellett. Tizenkét azonos kérés egyszer módosít készletet.

**Korlát:** az idempotencia a kliens által újrahasznált azonosító mellett működik. Több raktár és elosztott üzem nincs megvalósítva.

## 3. Tesztek ellenőrzése hibainjektálással és regresszióval

**Probléma:** a sikeres tesztfutás mellett azt is ellenőrizni kell, hogy egy hibás szabályt valóban felismernek a tesztek.

**Eszköz és kontextus:** Codex; a meglévő tesztek, a minimumkészlet határértéke és az API-szélsőértékek.

**Javaslat és döntés:** az összehasonlítást elkülönített másolatban `<=` helyett `<` értékre módosítjuk, és ugyanazt a tesztet futtatjuk. Ez szándékos hibainjektálás, nem valódi korábbi fejlesztési hiba. Ettől külön kezeljük a ténylegesen javított azonosító-, dátum- és Unicode-szélsőértékeket.

**Ellenőrzés:** `python3 scripts/defect_demo.py`. A `docs/evidence/defect/` megőrzi a két forrást, a tesztet, a hibás és sikeres futást, valamint az ellenőrzőösszegeket. A valódi szélsőértékekre a `tests/test_review.py` tartalmaz regressziós teszteket. A teljes tesztkimenet: `docs/evidence/test-results.txt`.

**Korlát:** egyetlen mutáció nem bizonyítja minden lehetséges hiba felismerését. A böngészős és hálózati használat külön ellenőrzést igényel.

## Két alkalmazott munkamódszer összehasonlítása

| Szempont | Implementáció, majd elfogadási tesztek | Reprodukáló teszt, majd javítás |
| --- | --- | --- |
| Alkalmazás | Az első verzió üzleti szabályai és 38 tesztje | Az API- és Unicode-szélsőértékek javítása |
| Előny | A teljes alapszabályrendszer áttekinthető | A javítás ugyanazzal a teszttel igazolható |
| Megfigyelt korlát | A sikeres tesztek mellett kimaradt néhány szélsőérték | Csak az előzetesen megfogalmazott esetet igazolja |
| Bizonyíték | Korábbi forrás és tesztek | Hibás és javított futási eredmények; 44 sikeres teszt |

Mindkét módszer MI-t használt. Nem végeztünk két modell összehasonlítását, és nem mértünk időnyereséget.

## Fejlesztési segédeszközök

Az `AGENTS.md` rögzíti a megőrzendő szabályokat és a munkamódszert.
A `verify.py` teszteket futtat és eredményt ment, a `defect_demo.py` elkülönített hibainjektálást végez; az API-szélsőértékeket a `tests/test_review.py` ellenőrzi.
