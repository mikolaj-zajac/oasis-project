# Oasis – opis projektu

Aplikacja w Pythonie (3.10+), konsolowa i z GUI we Flecie (telefon/WWW), dopasowująca rośliny doniczkowe do użytkownika na podstawie ankiety. Dane roślin i chorób są przechowywane w bazie SQLite.

## Uruchomienie

```
python3 main.py
```

Przy pierwszym uruchomieniu tworzony jest plik `oasis.db` i wypełniany przykładowymi roślinami i chorobami.

### Wersja mobilna (Flet)

```
python3 -m venv .venv && .venv/bin/pip install "flet[all]==1.1.2"
.venv/bin/flet run app_mobile.py              # okno na komputerze
.venv/bin/flet run --android app_mobile.py    # podgląd w aplikacji Flet na telefonie (QR)
.venv/bin/flet build apk                      # plik .apk (Android)
.venv/bin/flet build ipa                      # iOS (wymaga Xcode)
PORT=8765 .venv/bin/python app_mobile.py      # strona WWW pod http://<IP>:8765
```

Gdy ustawiona jest zmienna `PORT`, aplikacja działa jako serwer WWW (Python wykonuje się na serwerze, przeglądarka tylko wyświetla interfejs). Zależności dla hostingu: `requirements.txt`, polecenie startowe `python app_mobile.py`.

`app_mobile.py` korzysta z tych samych modeli, walidatorów i `Repozytorium` co wersja konsolowa. Baza zapisywana jest w katalogu danych aplikacji (`FLET_APP_STORAGE_DATA`, domyślnie bieżący katalog). Konfiguracja budowania: `pyproject.toml`.

### Ekrany GUI

| Trasa | Ekran |
|-------|-------|
| `/` | Logowanie (e-mail + hasło) |
| `/rejestracja` | Zakładanie konta (imię, e-mail, hasło) |
| `/start/1`–`/start/3` | Kreator profilu: czas na opiekę, nasłonecznienie, doświadczenie (osobny ekran na każdy krok, pasek postępu) |
| `/panel` | Moje rośliny: podsumowanie, status podlewania, przycisk-kropla do oznaczania i cofania podlania |
| `/odkrywaj` | Katalog: wyszukiwarka, filtr „Dla mnie / Wszystkie”, dodawanie roślin do kolekcji |
| `/profil` | Dane użytkownika, preferencje, zmiana preferencji, wylogowanie |

Kliknięcie karty rośliny otwiera szczegóły (instrukcje, choroby, ostatnie podlanie, usuwanie z kolekcji). Sesja zapamiętywana jest w przeglądarce (`SharedPreferences`, token z tabeli `sesje`), więc po odświeżeniu użytkownik pozostaje zalogowany. Niezalogowany użytkownik trafia zawsze na `/`, a zalogowany bez profilu na `/start/1`.

## Struktura

| Plik | Rola |
|------|------|
| `app_mobile.py` | GUI (Flet): klasa `Aplikacja` z routingiem, ekranami i obsługą sesji |
| `wyglad.py` | Etykiety i ikony opcji, kolory, wspólne elementy interfejsu (pola, karty, znaczki) |
| `main.py` | Punkt wejścia konsolowy: otwiera bazę, uruchamia ankietę, zapisuje użytkownika, wypisuje dopasowane rośliny |
| `enums.py` | `Rola`, `PoziomSlonca`, `PoziomCzasu`, `Doswiadczenie` |
| `modele.py` | Klasy domenowe: `Objaw`, `Choroba`, `Roslina`, `ProfilUzytkownika`, `Uzytkownik`, `BazaRoslin`, `RoslinaUzytkownika` |
| `ankieta.py` | Walidacja wejścia (imię, e-mail, hasło) i konsolowa ankieta startowa |
| `dane.py` | Przykładowe dane początkowe (3 rośliny, 2 choroby) |
| `baza_sql.py` | Warstwa SQLite: `Repozytorium` (schemat, rośliny, konta, sesje, kolekcje, podlewania) |
| `profil.json` | Wynik ostatniej ankiety (ignorowany przez git) |
| `oasis.db` | Plik bazy SQLite (ignorowany przez git) |

## Model domenowy

- `Choroba` ma kompozycję `Objaw` (1..*).
- `Roslina` i `Choroba` połączone asocjacją wiele-do-wielu (`dodaj_chorobe` ustawia oba kierunki).
- `Uzytkownik` ma kompozycję `ProfilUzytkownika` (0..1).
- `BazaRoslin` agreguje rośliny i choroby; zmiany tylko przez administratora (`PermissionError` w przeciwnym razie).
- `RoslinaUzytkownika` to roślina w kolekcji użytkownika z historią podlewań; wylicza następne podlanie (ostatnie + `cykl_nawadniania_dni`, a gdy nie była podlewana, dzień dodania).
- Dopasowanie: roślina pasuje, gdy jej wymagane słońce, czas opieki i trudność są nie większe niż w profilu użytkownika.

## Baza SQLite

Tabele: `choroby`, `objawy`, `rosliny`, `rosliny_choroby` (łącząca), `uzytkownicy` (unikalny e-mail), `profile`, `hasla` (sól + skrót PBKDF2-SHA256), `sesje` (losowy token), `moje_rosliny` (kolekcja, para użytkownik–roślina unikalna), `podlewania` (data podlania rośliny z kolekcji).

- Enumy zapisywane są jako nazwy (np. `POLCIEN`) i odtwarzane przez `Enum[nazwa]`.
- Klucze obce włączone (`PRAGMA foreign_keys = ON`), usuwanie kaskadowe.
- Zapisy w transakcjach; błędy zgłaszane jako `BladBazy`.
- `Repozytorium` działa jako menedżer kontekstu (`with Repozytorium() as repo`).
- Ponowna ankieta z tym samym e-mailem aktualizuje użytkownika i profil.
- Operacje na kolekcji i podlewaniach sprawdzają właściciela, więc użytkownik nie zmieni cudzej rośliny.
- Nowe tabele tworzone są przez `CREATE TABLE IF NOT EXISTS`, więc istniejący plik `oasis.db` dostaje je automatycznie.

## Konwencje

- Nazewnictwo domeny po polsku, bez komentarzy w kodzie.
- Pola prywatne z prefiksem `_`, dostęp przez właściwości.
- Importy ankiety i modeli w funkcjach są lokalne, aby uniknąć cyklu.

## Kolejne kroki

- Panel administratora (dodawanie roślin i chorób do bazy).
- Więcej roślin w `dane.py` (katalog ma na razie 3).
- Przypomnienia o podlewaniu (powiadomienia).
- Testy automatyczne.
