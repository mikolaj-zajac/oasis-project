# Oasis – opis projektu

Konsolowa aplikacja w Pythonie (3.10+) dopasowująca rośliny doniczkowe do użytkownika na podstawie ankiety. Dane roślin i chorób są przechowywane w bazie SQLite.

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

`app_mobile.py` korzysta z tych samych modeli, walidatorów i `Repozytorium` co wersja konsolowa. Baza i `profil.json` zapisywane są w katalogu danych aplikacji (`FLET_APP_STORAGE_DATA`). Konfiguracja budowania: `pyproject.toml`.

## Struktura

| Plik | Rola |
|------|------|
| `app_mobile.py` | GUI mobilne (Flet): formularz ankiety i karty dopasowanych roślin |
| `main.py` | Punkt wejścia konsolowy: otwiera bazę, uruchamia ankietę, zapisuje użytkownika, wypisuje dopasowane rośliny |
| `enums.py` | `Rola`, `PoziomSlonca`, `PoziomCzasu`, `Doswiadczenie` |
| `modele.py` | Klasy domenowe: `Objaw`, `Choroba`, `Roslina`, `ProfilUzytkownika`, `Uzytkownik`, `BazaRoslin` |
| `ankieta.py` | Walidacja wejścia i ankieta startowa (imię, e-mail, czas, słońce, doświadczenie) |
| `dane.py` | Przykładowe dane początkowe (3 rośliny, 2 choroby) |
| `baza_sql.py` | Warstwa SQLite: `Repozytorium` (schemat, zapis i odczyt) |
| `profil.json` | Wynik ostatniej ankiety (ignorowany przez git) |
| `oasis.db` | Plik bazy SQLite (ignorowany przez git) |

## Model domenowy

- `Choroba` ma kompozycję `Objaw` (1..*).
- `Roslina` i `Choroba` połączone asocjacją wiele-do-wielu (`dodaj_chorobe` ustawia oba kierunki).
- `Uzytkownik` ma kompozycję `ProfilUzytkownika` (0..1).
- `BazaRoslin` agreguje rośliny i choroby; zmiany tylko przez administratora (`PermissionError` w przeciwnym razie).
- Dopasowanie: roślina pasuje, gdy jej wymagane słońce, czas opieki i trudność są nie większe niż w profilu użytkownika.

## Baza SQLite

Tabele: `choroby`, `objawy`, `rosliny`, `rosliny_choroby` (łącząca), `uzytkownicy` (unikalny e-mail), `profile`.

- Enumy zapisywane są jako nazwy (np. `POLCIEN`) i odtwarzane przez `Enum[nazwa]`.
- Klucze obce włączone (`PRAGMA foreign_keys = ON`), usuwanie kaskadowe.
- Zapisy w transakcjach; błędy zgłaszane jako `BladBazy`.
- `Repozytorium` działa jako menedżer kontekstu (`with Repozytorium() as repo`).
- Ponowna ankieta z tym samym e-mailem aktualizuje użytkownika i profil.

## Konwencje

- Nazewnictwo domeny po polsku, bez komentarzy w kodzie.
- Pola prywatne z prefiksem `_`, dostęp przez właściwości.
- Importy ankiety i modeli w funkcjach są lokalne, aby uniknąć cyklu.

## Kolejne kroki

- Panel administratora (dodawanie roślin i chorób do bazy).
- Wyszukiwanie roślin (`BazaRoslin.wyszukaj`) w interfejsie.
- Testy automatyczne.
