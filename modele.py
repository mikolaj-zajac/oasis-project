from __future__ import annotations

import json
from pathlib import Path

from enums import Rola, PoziomSlonca, PoziomCzasu, Doswiadczenie


class Objaw:
    """Objaw choroby. Kompozycja: istnieje tylko jako część Choroby (1..*)."""

    def __init__(self, id: int, opis: str, choroba: Choroba):
        self._id = id
        self._opis = opis
        self._choroba = choroba

    @property
    def id(self) -> int:
        return self._id

    @property
    def opis(self) -> str:
        return self._opis

    def pobierz_procedure_leczenia(self) -> str:
        return self._choroba.pobierz_procedure_leczenia()

    def __str__(self) -> str:
        return self._opis


class Choroba:
    def __init__(self, id: int, nazwa: str, opis: str, procedura_leczenia: str):
        self._id = id
        self._nazwa = nazwa
        self._opis = opis
        self._procedura_leczenia = procedura_leczenia
        self._objawy: list[Objaw] = []   # kompozycja 1 -> 1..*
        self._rosliny: list[Roslina] = []  # asocjacja 0..* <-> 0..* "podatna na"

    @property
    def id(self) -> int:
        return self._id

    @property
    def nazwa(self) -> str:
        return self._nazwa

    @property
    def opis(self) -> str:
        return self._opis

    @property
    def rosliny(self) -> list[Roslina]:
        return list(self._rosliny)

    def dodaj_objaw(self, id: int, opis: str) -> Objaw:
        objaw = Objaw(id, opis, self)
        self._objawy.append(objaw)
        return objaw

    def pobierz_objawy(self) -> list[Objaw]:
        return list(self._objawy)

    def pobierz_procedure_leczenia(self) -> str:
        return self._procedura_leczenia

    def __str__(self) -> str:
        return self._nazwa


class Roslina:
    def __init__(
        self,
        id: int,
        nazwa_polska: str,
        nazwa_lacinska: str,
        opis: str,
        cykl_nawadniania_dni: int,
        instrukcja_podlewania: str,
        wymagane_slonce: PoziomSlonca,
        instrukcja_slonca: str,
        trudnosc: Doswiadczenie,
        czas_opieki: PoziomCzasu,
    ):
        self._id = id
        self.nazwa_polska = nazwa_polska
        self.nazwa_lacinska = nazwa_lacinska
        self.opis = opis
        self.cykl_nawadniania_dni = cykl_nawadniania_dni
        self.instrukcja_podlewania = instrukcja_podlewania
        self.wymagane_slonce = wymagane_slonce
        self.instrukcja_slonca = instrukcja_slonca
        self.trudnosc = trudnosc
        self.czas_opieki = czas_opieki
        self._choroby: list[Choroba] = []

    @property
    def id(self) -> int:
        return self._id

    def dodaj_chorobe(self, choroba: Choroba) -> None:
        """Wiąże roślinę z chorobą w obu kierunkach (0..* <-> 0..*)."""
        if choroba not in self._choroby:
            self._choroby.append(choroba)
            choroba._rosliny.append(self)

    def pobierz_instrukcje(self) -> str:
        return (
            f"Podlewanie (co {self.cykl_nawadniania_dni} dni): {self.instrukcja_podlewania}\n"
            f"Słońce ({self.wymagane_slonce.name}): {self.instrukcja_slonca}"
        )

    def pobierz_choroby(self) -> list[Choroba]:
        return list(self._choroby)

    def __str__(self) -> str:
        return f"{self.nazwa_polska} ({self.nazwa_lacinska})"


class ProfilUzytkownika:
    def __init__(
        self,
        czas_na_opieke: PoziomCzasu,
        naslonecznienie_domu: PoziomSlonca,
        doswiadczenie: Doswiadczenie,
    ):
        self.czas_na_opieke = czas_na_opieke
        self.naslonecznienie_domu = naslonecznienie_domu
        self.doswiadczenie = doswiadczenie

    def czy_pasuje(self, r: Roslina) -> bool:
        return (
            r.wymagane_slonce <= self.naslonecznienie_domu
            and r.czas_opieki <= self.czas_na_opieke
            and r.trudnosc <= self.doswiadczenie
        )

    def zapisz_wynik(self, plik: str = "profil.json") -> None:
        dane = {
            "czasNaOpieke": self.czas_na_opieke.name,
            "naslonecznienieDomu": self.naslonecznienie_domu.name,
            "doswiadczenie": self.doswiadczenie.name,
        }
        try:
            Path(plik).write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            raise IOError(f"Nie udało się zapisać profilu: {e}") from e


class Uzytkownik:
    def __init__(self, id: int, nazwa: str, email: str, rola: Rola = Rola.UZYTKOWNIK):
        self._id = id
        self._nazwa = nazwa
        self._email = email
        self._rola = rola
        self._profil: ProfilUzytkownika | None = None  # kompozycja 1 -> 0..1

    @property
    def id(self) -> int:
        return self._id

    @property
    def nazwa(self) -> str:
        return self._nazwa

    @property
    def email(self) -> str:
        return self._email

    @property
    def rola(self) -> Rola:
        return self._rola

    @property
    def profil(self) -> ProfilUzytkownika | None:
        return self._profil

    def wypelnij_ankiete(self) -> ProfilUzytkownika:
        from ankieta import ankieta_profilu  # lokalny import, bez cyklu

        self._profil = ankieta_profilu()
        return self._profil

    def czy_administrator(self) -> bool:
        return self._rola == Rola.ADMINISTRATOR


class BazaRoslin:
    """Agregacja: zawiera rośliny i choroby."""

    def __init__(self):
        self._rosliny: dict[int, Roslina] = {}
        self._choroby: dict[int, Choroba] = {}

    @staticmethod
    def _sprawdz_admina(admin: Uzytkownik) -> None:
        if not admin.czy_administrator():
            raise PermissionError("Tylko administrator może zmieniać bazę roślin.")

    def dodaj_rosline(self, admin: Uzytkownik, r: Roslina) -> None:
        self._sprawdz_admina(admin)
        if r.id in self._rosliny:
            raise ValueError(f"Roślina o id {r.id} już istnieje.")
        self._rosliny[r.id] = r

    def dodaj_chorobe(self, admin: Uzytkownik, c: Choroba) -> None:
        self._sprawdz_admina(admin)
        if c.id in self._choroby:
            raise ValueError(f"Choroba o id {c.id} już istnieje.")
        self._choroby[c.id] = c

    def wyszukaj(self, fraza: str) -> list[Roslina]:
        f = fraza.strip().lower()
        return [
            r for r in self._rosliny.values()
            if f in r.nazwa_polska.lower() or f in r.nazwa_lacinska.lower()
        ]

    def dopasuj(self, p: ProfilUzytkownika) -> list[Roslina]:
        return [r for r in self._rosliny.values() if p.czy_pasuje(r)]

    def pobierz_rosline(self, id: int) -> Roslina:
        try:
            return self._rosliny[id]
        except KeyError:
            raise KeyError(f"Brak rośliny o id {id}.") from None
