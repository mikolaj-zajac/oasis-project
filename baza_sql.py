from __future__ import annotations

import sqlite3

from enums import Rola, PoziomSlonca, PoziomCzasu, Doswiadczenie
from modele import BazaRoslin, Choroba, ProfilUzytkownika, Roslina, Uzytkownik

SCHEMAT = """
CREATE TABLE IF NOT EXISTS choroby (
    id INTEGER PRIMARY KEY,
    nazwa TEXT NOT NULL,
    opis TEXT NOT NULL,
    procedura_leczenia TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS objawy (
    id INTEGER PRIMARY KEY,
    choroba_id INTEGER NOT NULL REFERENCES choroby(id) ON DELETE CASCADE,
    opis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rosliny (
    id INTEGER PRIMARY KEY,
    nazwa_polska TEXT NOT NULL,
    nazwa_lacinska TEXT NOT NULL,
    opis TEXT NOT NULL,
    cykl_nawadniania_dni INTEGER NOT NULL CHECK (cykl_nawadniania_dni > 0),
    instrukcja_podlewania TEXT NOT NULL,
    wymagane_slonce TEXT NOT NULL,
    instrukcja_slonca TEXT NOT NULL,
    trudnosc TEXT NOT NULL,
    czas_opieki TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rosliny_choroby (
    roslina_id INTEGER NOT NULL REFERENCES rosliny(id) ON DELETE CASCADE,
    choroba_id INTEGER NOT NULL REFERENCES choroby(id) ON DELETE CASCADE,
    PRIMARY KEY (roslina_id, choroba_id)
);
CREATE TABLE IF NOT EXISTS uzytkownicy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    rola TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profile (
    uzytkownik_id INTEGER PRIMARY KEY REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    czas_na_opieke TEXT NOT NULL,
    naslonecznienie_domu TEXT NOT NULL,
    doswiadczenie TEXT NOT NULL
);
"""


class BladBazy(RuntimeError):
    pass


class Repozytorium:
    def __init__(self, sciezka: str = "oasis.db"):
        self._sciezka = sciezka
        try:
            self._polaczenie = sqlite3.connect(sciezka)
            self._polaczenie.row_factory = sqlite3.Row
            self._polaczenie.execute("PRAGMA foreign_keys = ON")
            self._polaczenie.executescript(SCHEMAT)
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się otworzyć bazy {sciezka}: {e}") from e

    def zamknij(self) -> None:
        self._polaczenie.close()

    def __enter__(self) -> Repozytorium:
        return self

    def __exit__(self, *_) -> None:
        self.zamknij()

    def czy_pusta(self) -> bool:
        wiersz = self._polaczenie.execute("SELECT COUNT(*) FROM rosliny").fetchone()
        return wiersz[0] == 0

    def zapisz_baze(self, baza: BazaRoslin) -> None:
        try:
            with self._polaczenie:
                for c in baza.choroby:
                    self._polaczenie.execute(
                        "INSERT OR REPLACE INTO choroby VALUES (?, ?, ?, ?)",
                        (c.id, c.nazwa, c.opis, c.pobierz_procedure_leczenia()),
                    )
                    self._polaczenie.execute("DELETE FROM objawy WHERE choroba_id = ?", (c.id,))
                    self._polaczenie.executemany(
                        "INSERT INTO objawy (id, choroba_id, opis) VALUES (?, ?, ?)",
                        [(o.id, c.id, o.opis) for o in c.pobierz_objawy()],
                    )
                for r in baza.rosliny:
                    self._polaczenie.execute(
                        "INSERT OR REPLACE INTO rosliny VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            r.id, r.nazwa_polska, r.nazwa_lacinska, r.opis,
                            r.cykl_nawadniania_dni, r.instrukcja_podlewania,
                            r.wymagane_slonce.name, r.instrukcja_slonca,
                            r.trudnosc.name, r.czas_opieki.name,
                        ),
                    )
                    self._polaczenie.execute(
                        "DELETE FROM rosliny_choroby WHERE roslina_id = ?", (r.id,)
                    )
                    self._polaczenie.executemany(
                        "INSERT INTO rosliny_choroby VALUES (?, ?)",
                        [(r.id, c.id) for c in r.pobierz_choroby()],
                    )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się zapisać bazy roślin: {e}") from e

    def wczytaj_baze(self) -> BazaRoslin:
        admin = Uzytkownik(0, "Admin", "admin@oasis.pl", Rola.ADMINISTRATOR)
        baza = BazaRoslin()
        try:
            choroby: dict[int, Choroba] = {}
            for w in self._polaczenie.execute("SELECT * FROM choroby ORDER BY id"):
                c = Choroba(w["id"], w["nazwa"], w["opis"], w["procedura_leczenia"])
                for o in self._polaczenie.execute(
                    "SELECT id, opis FROM objawy WHERE choroba_id = ? ORDER BY id", (c.id,)
                ):
                    c.dodaj_objaw(o["id"], o["opis"])
                choroby[c.id] = c
                baza.dodaj_chorobe(admin, c)

            for w in self._polaczenie.execute("SELECT * FROM rosliny ORDER BY id"):
                r = Roslina(
                    w["id"], w["nazwa_polska"], w["nazwa_lacinska"], w["opis"],
                    w["cykl_nawadniania_dni"], w["instrukcja_podlewania"],
                    PoziomSlonca[w["wymagane_slonce"]], w["instrukcja_slonca"],
                    Doswiadczenie[w["trudnosc"]], PoziomCzasu[w["czas_opieki"]],
                )
                for p in self._polaczenie.execute(
                    "SELECT choroba_id FROM rosliny_choroby WHERE roslina_id = ?", (r.id,)
                ):
                    r.dodaj_chorobe(choroby[p["choroba_id"]])
                baza.dodaj_rosline(admin, r)
        except (sqlite3.Error, KeyError) as e:
            raise BladBazy(f"Nie udało się wczytać bazy roślin: {e}") from e
        return baza

    def zapisz_uzytkownika(self, uzytkownik: Uzytkownik) -> int:
        try:
            with self._polaczenie:
                self._polaczenie.execute(
                    "INSERT INTO uzytkownicy (nazwa, email, rola) VALUES (?, ?, ?) "
                    "ON CONFLICT(email) DO UPDATE SET nazwa = excluded.nazwa",
                    (uzytkownik.nazwa, uzytkownik.email, uzytkownik.rola.value),
                )
                id_uzytkownika = self._polaczenie.execute(
                    "SELECT id FROM uzytkownicy WHERE email = ?", (uzytkownik.email,)
                ).fetchone()[0]
                profil = uzytkownik.profil
                if profil is not None:
                    self._polaczenie.execute(
                        "INSERT OR REPLACE INTO profile VALUES (?, ?, ?, ?)",
                        (
                            id_uzytkownika, profil.czas_na_opieke.name,
                            profil.naslonecznienie_domu.name, profil.doswiadczenie.name,
                        ),
                    )
            return id_uzytkownika
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się zapisać użytkownika: {e}") from e

    def wczytaj_profil(self, email: str) -> ProfilUzytkownika | None:
        try:
            w = self._polaczenie.execute(
                "SELECT p.* FROM profile p JOIN uzytkownicy u ON u.id = p.uzytkownik_id "
                "WHERE u.email = ?",
                (email,),
            ).fetchone()
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się wczytać profilu: {e}") from e
        if w is None:
            return None
        return ProfilUzytkownika(
            PoziomCzasu[w["czas_na_opieke"]],
            PoziomSlonca[w["naslonecznienie_domu"]],
            Doswiadczenie[w["doswiadczenie"]],
        )
