# Készletkezelő és beszerzéstámogató webalkalmazás

Verzió: 1.1.

## Cél, szerepkör és forgatókönyvek

Kisvállalkozások egyetlen raktárának webes készletnyilvántartása. A készletkezelő terméket vesz fel, adatokat szerkeszt, bevételez és kiad, keres és szűr, mozgásnaplót néz, valamint beszerzést tervez. Külön bejelentkezés nincs. A frontend a felületért, a backend az ellenőrzésekért és üzleti szabályokért, az SQLite-adatbázis a tartós tárolásért felel.

## Számozott elfogadási feltételek

1. **Létrehozás:** érvényes névvel, egyedi cikkszámmal és 0 vagy pozitív egész kezdőkészlettel létrehozott termék megjelenik a listában, a megadott készlettel.
2. **Hibás adatok:** üres név, foglalt cikkszám vagy negatív kezdőkészlet esetén látható hibaüzenet jelenik meg, és nem keletkezik termék. A cikkszám kis/nagybetűs változata ugyanannak számít.
3. **Bevételezés:** 10 db készlethez 5 db bevételezése 15 db készletet eredményez, és a mozgás a naplóba kerül.
4. **Kiadás és határok:** 10 db készletből 10 db kiadható, az eredmény 0. Több mint 10 db, illetve nulla, negatív vagy nem egész mennyiség kiadása hibával elutasítandó; sem a készlet, sem a napló nem változhat.
5. **Napló:** minden sikeres bevételezés és kiadás tárolja a terméket, típust, mennyiséget és időpontot. Az előzmények a felületen kereshetők, és nem szerkeszthetők utólag.
6. **Alacsony készlet:** 5 db minimum mellett 5 db aktuális készletnél figyelmeztetés jelenik meg, 6 db-nál nem. A nulla készlet külön jelzést kap, és alacsonynak számít nulla minimum mellett is.
7. **Utánrendelés:** a javaslat max(0, napi fogyás × beszerzési idő + biztonsági készlet − aktuális készlet). A 4 db/nap, 5 nap, 6 db tartalék, 12 db készlet bemenet eredménye 14 db. Negatív számított igényből 0 db lesz; a javaslat önmagában nem módosít adatot.
8. **Megőrzés:** termék és készletmozgás mentése, majd a backend leállítása és újraindítása után minden korábbi termék, készlet és naplóbejegyzés változatlanul elérhető.

## Bizonytalanságok és választott értelmezések

- Egy raktár, egy szerepkör, hitelesítés nélkül; a helyi kiszolgálók nem nyilvános szolgáltatások.
- Minden mennyiség egész. A készlet és mozgás legfeljebb 1 milliárd db; a minimum, napi fogyás, beszerzési idő és biztonsági készlet 0–1 millió. A minimum a figyelmeztetés, a biztonsági készlet a rendelési képlet paramétere.
- A napi fogyást a felhasználó adja meg, nem a napló számítja. A javaslat nem automatikus rendelés.
- A termék metaadata szerkeszthető, készlete csak bevételezéssel/kiadással változik. Pozitív nyitókészlet külön naplóbejegyzés. Korábbi terméknév és cikkszám megmarad a naplóban.
- Egy mozgás és naplózása közös tranzakció; azonos műveletazonosító ismétlése egyszer hajtódik végre.
- UTC-tárolás; Budapest időzónájú megjelenítés és dátumszűrés.
