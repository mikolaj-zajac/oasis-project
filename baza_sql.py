from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import date

from enums import Rola, PoziomSlonca, PoziomCzasu, Doswiadczenie
from modele import BazaRoslin, Choroba, ProfilUzytkownika, Roslina, RoslinaUzytkownika, Uzytkownik

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
CREATE TABLE IF NOT EXISTS hasla (
    uzytkownik_id INTEGER PRIMARY KEY REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    sol TEXT NOT NULL,
    skrot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sesje (
    token TEXT PRIMARY KEY,
    uzytkownik_id INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moje_rosliny (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uzytkownik_id INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    roslina_id INTEGER NOT NULL REFERENCES rosliny(id) ON DELETE CASCADE,
    dodano TEXT NOT NULL,
    UNIQUE (uzytkownik_id, roslina_id)
);
CREATE TABLE IF NOT EXISTS podlewania (
    moja_roslina_id INTEGER NOT NULL REFERENCES moje_rosliny(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    PRIMARY KEY (moja_roslina_id, data)
);
"""

ITERACJE_HASLA = 200_000


class BladBazy(RuntimeError):
    pass


class BladKonta(BladBazy):
    pass


def _skrot_hasla(haslo: str, sol: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", haslo.encode("utf-8"), bytes.fromhex(sol), ITERACJE_HASLA
    ).hex()


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

    def wczytaj_uzytkownika(self, email: str) -> Uzytkownik | None:
        try:
            w = self._polaczenie.execute(
                "SELECT * FROM uzytkownicy WHERE email = ?", (email,)
            ).fetchone()
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się wczytać użytkownika: {e}") from e
        if w is None:
            return None
        uzytkownik = Uzytkownik(w["id"], w["nazwa"], w["email"], Rola(w["rola"]))
        profil = self.wczytaj_profil(email)
        if profil is not None:
            uzytkownik.wypelnij_ankiete(profil)
        return uzytkownik

    def zarejestruj(self, uzytkownik: Uzytkownik, haslo: str) -> Uzytkownik:
        try:
            istnieje = self._polaczenie.execute(
                "SELECT 1 FROM hasla h JOIN uzytkownicy u ON u.id = h.uzytkownik_id "
                "WHERE u.email = ?",
                (uzytkownik.email,),
            ).fetchone()
            if istnieje:
                raise BladKonta("Konto z tym adresem e-mail już istnieje.")
            id_uzytkownika = self.zapisz_uzytkownika(uzytkownik)
            sol = secrets.token_hex(16)
            with self._polaczenie:
                self._polaczenie.execute(
                    "INSERT INTO hasla VALUES (?, ?, ?)",
                    (id_uzytkownika, sol, _skrot_hasla(haslo, sol)),
                )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się założyć konta: {e}") from e
        return self.wczytaj_uzytkownika(uzytkownik.email)

    def zaloguj(self, email: str, haslo: str) -> Uzytkownik:
        try:
            w = self._polaczenie.execute(
                "SELECT h.sol, h.skrot FROM hasla h JOIN uzytkownicy u ON u.id = h.uzytkownik_id "
                "WHERE u.email = ?",
                (email,),
            ).fetchone()
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się zalogować: {e}") from e
        if w is None or not secrets.compare_digest(_skrot_hasla(haslo, w["sol"]), w["skrot"]):
            raise BladKonta("Nieprawidłowy e-mail lub hasło.")
        return self.wczytaj_uzytkownika(email)

    def utworz_sesje(self, uzytkownik: Uzytkownik) -> str:
        token = secrets.token_urlsafe(32)
        try:
            with self._polaczenie:
                self._polaczenie.execute(
                    "INSERT INTO sesje (token, uzytkownik_id) "
                    "SELECT ?, id FROM uzytkownicy WHERE email = ?",
                    (token, uzytkownik.email),
                )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się utworzyć sesji: {e}") from e
        return token

    def uzytkownik_sesji(self, token: str) -> Uzytkownik | None:
        try:
            w = self._polaczenie.execute(
                "SELECT u.email FROM sesje s JOIN uzytkownicy u ON u.id = s.uzytkownik_id "
                "WHERE s.token = ?",
                (token,),
            ).fetchone()
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się wczytać sesji: {e}") from e
        return self.wczytaj_uzytkownika(w["email"]) if w else None

    def usun_sesje(self, token: str) -> None:
        try:
            with self._polaczenie:
                self._polaczenie.execute("DELETE FROM sesje WHERE token = ?", (token,))
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się wylogować: {e}") from e

    def dodaj_do_kolekcji(self, uzytkownik: Uzytkownik, roslina: Roslina, dzis: date) -> None:
        try:
            with self._polaczenie:
                self._polaczenie.execute(
                    "INSERT OR IGNORE INTO moje_rosliny (uzytkownik_id, roslina_id, dodano) "
                    "SELECT id, ?, ? FROM uzytkownicy WHERE email = ?",
                    (roslina.id, dzis.isoformat(), uzytkownik.email),
                )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się dodać rośliny: {e}") from e

    def usun_z_kolekcji(self, uzytkownik: Uzytkownik, moja: RoslinaUzytkownika) -> None:
        try:
            with self._polaczenie:
                self._polaczenie.execute(
                    "DELETE FROM moje_rosliny WHERE id = ? AND uzytkownik_id = "
                    "(SELECT id FROM uzytkownicy WHERE email = ?)",
                    (moja.id, uzytkownik.email),
                )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się usunąć rośliny: {e}") from e

    def zapisz_podlanie(
        self, uzytkownik: Uzytkownik, moja: RoslinaUzytkownika, dzien: date, podlana: bool
    ) -> None:
        wlasciciel = (
            "SELECT m.id FROM moje_rosliny m JOIN uzytkownicy u ON u.id = m.uzytkownik_id "
            "WHERE m.id = ? AND u.email = ?"
        )
        try:
            with self._polaczenie:
                if podlana:
                    self._polaczenie.execute(
                        f"INSERT OR IGNORE INTO podlewania SELECT id, ? FROM ({wlasciciel})",
                        (dzien.isoformat(), moja.id, uzytkownik.email),
                    )
                else:
                    self._polaczenie.execute(
                        f"DELETE FROM podlewania WHERE data = ? AND moja_roslina_id IN ({wlasciciel})",
                        (dzien.isoformat(), moja.id, uzytkownik.email),
                    )
        except sqlite3.Error as e:
            raise BladBazy(f"Nie udało się zapisać podlania: {e}") from e

    def wczytaj_kolekcje(self, uzytkownik: Uzytkownik, baza: BazaRoslin) -> list[RoslinaUzytkownika]:
        try:
            wiersze = self._polaczenie.execute(
                "SELECT m.id, m.roslina_id, m.dodano FROM moje_rosliny m "
                "JOIN uzytkownicy u ON u.id = m.uzytkownik_id WHERE u.email = ? ORDER BY m.id",
                (uzytkownik.email,),
            ).fetchall()
            kolekcja = []
            for w in wiersze:
                podlewania = [
                    date.fromisoformat(p["data"])
                    for p in self._polaczenie.execute(
                        "SELECT data FROM podlewania WHERE moja_roslina_id = ?", (w["id"],)
                    )
                ]
                kolekcja.append(RoslinaUzytkownika(
                    w["id"], baza.pobierz_rosline(w["roslina_id"]),
                    date.fromisoformat(w["dodano"]), podlewania,
                ))
        except (sqlite3.Error, KeyError, ValueError) as e:
            raise BladBazy(f"Nie udało się wczytać kolekcji: {e}") from e
        return kolekcja
