import os
from pathlib import Path

import flet as ft

from ankieta import BladWalidacji, waliduj_email, waliduj_imie
from baza_sql import BladBazy, Repozytorium
from dane import zaladuj_przykladowa_baze
from enums import Doswiadczenie, PoziomCzasu, PoziomSlonca
from modele import ProfilUzytkownika, Uzytkownik

KATALOG_DANYCH = Path(os.getenv("FLET_APP_STORAGE_DATA") or ".")
SCIEZKA_BAZY = str(KATALOG_DANYCH / "oasis.db")
SCIEZKA_PROFILU = str(KATALOG_DANYCH / "profil.json")

ETYKIETY = {
    PoziomCzasu.MALO: "Mało",
    PoziomCzasu.SREDNIO: "Średnio",
    PoziomCzasu.DUZO: "Dużo",
    PoziomSlonca.CIEN: "Cień",
    PoziomSlonca.POLCIEN: "Półcień",
    PoziomSlonca.JASNE: "Jasno",
    PoziomSlonca.PELNE_SLONCE: "Pełne słońce",
    Doswiadczenie.POCZATKUJACY: "Początkujący",
    Doswiadczenie.SREDNIO: "Średnio zaawansowany",
    Doswiadczenie.ZAAWANSOWANY: "Zaawansowany",
}


def pole_wyboru(etykieta: str, enum_cls) -> ft.Dropdown:
    return ft.Dropdown(
        label=etykieta,
        options=[ft.DropdownOption(key=e.name, text=ETYKIETY[e]) for e in enum_cls],
        expand=True,
    )


def karta_rosliny(r) -> ft.Card:
    choroby = [
        ft.ListTile(
            leading=ft.Icon(ft.Icons.WARNING_AMBER),
            title=ft.Text(c.nazwa),
            subtitle=ft.Text(c.pobierz_procedure_leczenia()),
        )
        for c in r.pobierz_choroby()
    ]
    return ft.Card(
        content=ft.ExpansionTile(
            leading=ft.Icon(ft.Icons.LOCAL_FLORIST),
            title=ft.Text(r.nazwa_polska),
            subtitle=ft.Text(r.nazwa_lacinska, italic=True),
            controls_padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            controls=[
                ft.Text(r.opis),
                ft.Text(r.pobierz_instrukcje()),
                *([ft.Text("Podatna na:", weight=ft.FontWeight.BOLD), *choroby] if choroby else []),
            ],
        )
    )


def main(page: ft.Page) -> None:
    page.title = "Oasis"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.GREEN)
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16

    try:
        with Repozytorium(SCIEZKA_BAZY) as repo:
            if repo.czy_pusta():
                repo.zapisz_baze(zaladuj_przykladowa_baze())
            baza = repo.wczytaj_baze()
    except BladBazy as e:
        page.add(ft.Text(f"Błąd: {e}", color=ft.Colors.ERROR))
        return

    imie = ft.TextField(label="Imię", capitalization=ft.TextCapitalization.WORDS)
    email = ft.TextField(label="E-mail", keyboard_type=ft.KeyboardType.EMAIL)
    czas = pole_wyboru("Czas na opiekę", PoziomCzasu)
    slonce = pole_wyboru("Nasłonecznienie domu", PoziomSlonca)
    dosw = pole_wyboru("Doświadczenie", Doswiadczenie)
    komunikat = ft.Text()
    wyniki = ft.Column()

    def wczytaj_zapisany_profil(_):
        try:
            adres = waliduj_email(email.value or "")
            with Repozytorium(SCIEZKA_BAZY) as repo:
                profil = repo.wczytaj_profil(adres)
        except (BladWalidacji, BladBazy):
            return
        if profil:
            czas.value = profil.czas_na_opieke.name
            slonce.value = profil.naslonecznienie_domu.name
            dosw.value = profil.doswiadczenie.name
            page.update()

    email.on_blur = wczytaj_zapisany_profil

    def dopasuj(_):
        poprawne = True
        for pole, walidator in ((imie, waliduj_imie), (email, waliduj_email)):
            try:
                pole.value = walidator(pole.value or "")
                pole.error = None
            except BladWalidacji as e:
                pole.error = str(e)
                poprawne = False
        for pole in (czas, slonce, dosw):
            pole.error_text = None if pole.value else "Wybierz opcję."
            poprawne = poprawne and bool(pole.value)
        if not poprawne:
            page.update()
            return

        profil = ProfilUzytkownika(
            PoziomCzasu[czas.value], PoziomSlonca[slonce.value], Doswiadczenie[dosw.value]
        )
        uzytkownik = Uzytkownik(1, imie.value, email.value)
        uzytkownik.wypelnij_ankiete(profil)

        uwagi = []
        try:
            with Repozytorium(SCIEZKA_BAZY) as repo:
                repo.zapisz_uzytkownika(uzytkownik)
        except BladBazy as e:
            uwagi.append(str(e))
        try:
            profil.zapisz_wynik(SCIEZKA_PROFILU)
        except IOError as e:
            uwagi.append(str(e))

        dopasowane = baza.dopasuj(profil)
        komunikat.value = f"Cześć {uzytkownik.nazwa}! Rośliny dopasowane do Ciebie:"
        wyniki.controls = [karta_rosliny(r) for r in dopasowane] or [
            ft.Text("Brak pasujących roślin.")
        ]
        if uwagi:
            wyniki.controls.append(ft.Text("Uwaga: " + "; ".join(uwagi), color=ft.Colors.ERROR))
        page.update()

    page.appbar = ft.AppBar(title=ft.Text("Oasis"), center_title=True)
    page.add(
        ft.Text("Ankieta startowa", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        imie,
        email,
        czas,
        slonce,
        dosw,
        ft.FilledButton("Dopasuj rośliny", icon=ft.Icons.SEARCH, on_click=dopasuj),
        komunikat,
        wyniki,
    )


if __name__ == "__main__":
    if os.getenv("PORT"):
        os.environ.setdefault("FLET_FORCE_WEB_SERVER", "true")
        os.environ.setdefault("FLET_SERVER_IP", "0.0.0.0")
        os.environ.setdefault("FLET_SERVER_PORT", os.environ["PORT"])
    ft.run(main)
