import asyncio
import os
from pathlib import Path

import flet as ft

import wyglad as w
from ankieta import BladWalidacji, waliduj_email, waliduj_haslo, waliduj_imie
from baza_sql import BladBazy, Repozytorium
from dane import zaladuj_przykladowa_baze
from enums import Doswiadczenie, PoziomCzasu, PoziomSlonca
from modele import ProfilUzytkownika, Uzytkownik

KATALOG_DANYCH = Path(os.getenv("FLET_APP_STORAGE_DATA") or ".")
SCIEZKA_BAZY = str(KATALOG_DANYCH / "oasis.db")
KLUCZ_SESJI = "oasis_sesja"
TRASY_PANELU = ["/panel", "/odkrywaj", "/profil"]
TRASY_KREATORA = [f"/start/{nr}" for nr in range(1, len(w.KROKI) + 1)]
TRASY_PUBLICZNE = ["/", "/rejestracja"]


def repo() -> Repozytorium:
    return Repozytorium(SCIEZKA_BAZY)


def przygotuj_baze():
    with repo() as r:
        if r.czy_pusta():
            r.zapisz_baze(zaladuj_przykladowa_baze())
        return r.wczytaj_baze()


def zaloguj_w_bazie(email: str, haslo: str):
    with repo() as r:
        uzytkownik = r.zaloguj(email, haslo)
        return uzytkownik, r.utworz_sesje(uzytkownik)


def zarejestruj_w_bazie(imie: str, email: str, haslo: str):
    with repo() as r:
        uzytkownik = r.zarejestruj(Uzytkownik(0, imie, email), haslo)
        return uzytkownik, r.utworz_sesje(uzytkownik)


def niepuste_haslo(tekst: str) -> str:
    if not tekst:
        raise BladWalidacji("Podaj hasło.")
    return tekst


def baner_bledu():
    tekst = ft.Text(color=ft.Colors.ON_ERROR_CONTAINER, expand=True)
    baner = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.ON_ERROR_CONTAINER), tekst]),
        bgcolor=ft.Colors.ERROR_CONTAINER,
        border_radius=14,
        padding=12,
        visible=False,
    )

    def ustaw(komunikat: str | None) -> None:
        tekst.value = komunikat or ""
        baner.visible = bool(komunikat)

    return baner, ustaw


def waliduj_pola(pola) -> bool:
    poprawne = True
    for pole, walidator in pola:
        try:
            pole.value = walidator(pole.value or "")
            pole.error = None
        except BladWalidacji as e:
            pole.error = str(e)
            poprawne = False
    return poprawne


class Aplikacja:
    def __init__(self, page: ft.Page, baza):
        self.page = page
        self.baza = baza
        self.prefs = ft.SharedPreferences()
        self.uzytkownik: Uzytkownik | None = None
        self.token: str | None = None
        self.kreator: dict = {}
        self.fraza = ""
        self.tylko_dopasowane = True

    async def start(self) -> None:
        token = await self.prefs.get(KLUCZ_SESJI)
        if isinstance(token, str) and token:
            try:
                with repo() as r:
                    self.uzytkownik = r.uzytkownik_sesji(token)
                self.token = token if self.uzytkownik else None
            except BladBazy:
                self.uzytkownik = None
        self.page.on_route_change = self.pokaz
        self.page.on_resize = self.dopasuj_marginesy
        self.pokaz()

    def idz(self, trasa: str) -> None:
        self.page.navigate(trasa)

    def margines(self) -> ft.Padding:
        szerokosc = self.page.width or 0
        poziomo = max(20, (szerokosc - w.MAKS_SZEROKOSC) / 2)
        return ft.Padding.only(left=poziomo, right=poziomo, top=12, bottom=24)

    def dopasuj_marginesy(self, e=None) -> None:
        if self.page.views:
            self.page.views[-1].padding = self.margines()
            self.page.update()

    def przekierowanie(self, trasa: str) -> str | None:
        if self.uzytkownik is None:
            return None if trasa in TRASY_PUBLICZNE else "/"
        if trasa in TRASY_KREATORA:
            if self.uzytkownik.profil is not None and not self.kreator:
                self.kreator = {
                    PoziomCzasu: self.uzytkownik.profil.czas_na_opieke,
                    PoziomSlonca: self.uzytkownik.profil.naslonecznienie_domu,
                    Doswiadczenie: self.uzytkownik.profil.doswiadczenie,
                }
            for nr, (enum_cls, *_) in enumerate(w.KROKI):
                if TRASY_KREATORA[nr] == trasa:
                    return None
                if enum_cls not in self.kreator:
                    return TRASY_KREATORA[nr]
        if self.uzytkownik.profil is None:
            return TRASY_KREATORA[0]
        return None if trasa in TRASY_PANELU else TRASY_PANELU[0]

    def pokaz(self, e=None) -> None:
        trasa = self.page.route or "/"
        cel = self.przekierowanie(trasa)
        if cel is not None and cel != trasa:
            self.idz(cel)
            return
        if trasa == "/":
            widok = self.widok_logowania()
        elif trasa == "/rejestracja":
            widok = self.widok_rejestracji()
        elif trasa in TRASY_KREATORA:
            widok = self.widok_kroku(TRASY_KREATORA.index(trasa) + 1)
        elif trasa == "/odkrywaj":
            widok = self.widok_odkrywania()
        elif trasa == "/profil":
            widok = self.widok_profilu()
        else:
            widok = self.widok_panelu()
        self.page.views.clear()
        self.page.views.append(widok)
        self.page.update()

    def widok(self, trasa: str, elementy: list, **kwargs) -> ft.View:
        return ft.View(
            route=trasa,
            controls=[ft.SafeArea(content=ft.Column(
                elementy, spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ))],
            padding=self.margines(),
            scroll=ft.ScrollMode.AUTO,
            bgcolor=ft.Colors.SURFACE,
            **kwargs,
        )

    def komunikat(self, tekst: str, akcja: str | None = None, trasa: str | None = None) -> None:
        self.page.show_dialog(ft.SnackBar(
            content=ft.Text(tekst),
            action=akcja,
            on_action=(lambda e: self.idz(trasa)) if trasa else None,
            behavior=ft.SnackBarBehavior.FLOATING,
            duration=2500,
        ))

    async def otworz_sesje(self, uzytkownik: Uzytkownik, token: str) -> None:
        await self.prefs.set(KLUCZ_SESJI, token)
        self.uzytkownik = uzytkownik
        self.token = token
        self.kreator = {}
        self.fraza = ""
        self.tylko_dopasowane = True
        await self.page.push_route(TRASY_PANELU[0] if uzytkownik.profil else TRASY_KREATORA[0])

    async def wyloguj(self, e=None) -> None:
        if self.token:
            try:
                with repo() as r:
                    r.usun_sesje(self.token)
            except BladBazy:
                pass
        await self.prefs.remove(KLUCZ_SESJI)
        self.uzytkownik = None
        self.token = None
        self.kreator = {}
        await self.page.push_route("/")

    def logo(self) -> ft.Row:
        return ft.Row([ft.Container(
            content=ft.Icon(ft.Icons.ECO, size=44, color=ft.Colors.ON_PRIMARY),
            bgcolor=ft.Colors.PRIMARY,
            width=88,
            height=88,
            border_radius=28,
            alignment=ft.Alignment.CENTER,
        )], alignment=ft.MainAxisAlignment.CENTER)

    def widok_logowania(self) -> ft.View:
        email = w.pole("E-mail", ft.Icons.EMAIL_OUTLINED, keyboard_type=ft.KeyboardType.EMAIL)
        haslo = w.pole("Hasło", ft.Icons.LOCK_OUTLINE, password=True, can_reveal_password=True)
        baner, pokaz_blad = baner_bledu()

        async def zaloguj(e=None):
            pokaz_blad(None)
            if not waliduj_pola([(email, waliduj_email), (haslo, niepuste_haslo)]):
                self.page.update()
                return
            try:
                uzytkownik, token = await asyncio.to_thread(zaloguj_w_bazie, email.value, haslo.value)
            except BladBazy as ex:
                pokaz_blad(str(ex))
                self.page.update()
                return
            await self.otworz_sesje(uzytkownik, token)

        haslo.on_submit = zaloguj
        return self.widok("/", [
            ft.Container(height=32),
            self.logo(),
            ft.Text("Oasis", size=34, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Text(
                "Twoje rośliny zawsze zadbane",
                size=16, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=12),
            email,
            haslo,
            baner,
            ft.FilledButton("Zaloguj się", on_click=zaloguj, style=w.styl_przycisku()),
            ft.Row(
                [
                    ft.Text("Nie masz konta?", color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.TextButton("Załóż je", on_click=lambda e: self.idz("/rejestracja")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0,
            ),
        ])

    def widok_rejestracji(self) -> ft.View:
        imie = w.pole("Imię", ft.Icons.PERSON_OUTLINE, capitalization=ft.TextCapitalization.WORDS)
        email = w.pole("E-mail", ft.Icons.EMAIL_OUTLINED, keyboard_type=ft.KeyboardType.EMAIL)
        haslo = w.pole(
            "Hasło", ft.Icons.LOCK_OUTLINE, password=True, can_reveal_password=True,
            helper="Co najmniej 6 znaków",
        )
        baner, pokaz_blad = baner_bledu()

        async def zaloz(e=None):
            pokaz_blad(None)
            if not waliduj_pola([(imie, waliduj_imie), (email, waliduj_email), (haslo, waliduj_haslo)]):
                self.page.update()
                return
            try:
                uzytkownik, token = await asyncio.to_thread(
                    zarejestruj_w_bazie, imie.value, email.value, haslo.value
                )
            except BladBazy as ex:
                pokaz_blad(str(ex))
                self.page.update()
                return
            await self.otworz_sesje(uzytkownik, token)

        haslo.on_submit = zaloz
        return self.widok("/rejestracja", [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.idz("/"))]),
            w.naglowek("Załóż konto", "Potem trzy krótkie pytania i gotowe."),
            ft.Container(height=4),
            imie,
            email,
            haslo,
            baner,
            ft.FilledButton("Dalej", icon=ft.Icons.ARROW_FORWARD, on_click=zaloz, style=w.styl_przycisku()),
        ])

    def karta_opcji(self, wartosc, wybrana: bool, wybierz) -> ft.Container:
        nazwa, opis, ikona = w.OPCJE[type(wartosc)][wartosc]
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ikona, color=ft.Colors.ON_PRIMARY if wybrana else ft.Colors.PRIMARY),
                    bgcolor=ft.Colors.PRIMARY if wybrana else ft.Colors.PRIMARY_CONTAINER,
                    width=52,
                    height=52,
                    border_radius=16,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(nazwa, size=17, weight=ft.FontWeight.W_600),
                        ft.Text(opis, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if wybrana else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=ft.Colors.PRIMARY if wybrana else ft.Colors.OUTLINE,
                ),
            ], spacing=14),
            padding=16,
            border_radius=w.ZAOKRAGLENIE,
            bgcolor=ft.Colors.SECONDARY_CONTAINER if wybrana else ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(2, ft.Colors.PRIMARY if wybrana else ft.Colors.TRANSPARENT),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=lambda e: wybierz(wartosc),
        )

    def widok_kroku(self, nr: int) -> ft.View:
        enum_cls, pytanie, podpowiedz = w.KROKI[nr - 1]
        ostatni = nr == len(w.KROKI)
        edycja = self.uzytkownik.profil is not None
        opcje = ft.Column(spacing=12)
        dalej = ft.FilledButton(
            "Zaczynamy!" if ostatni and not edycja else "Zapisz" if ostatni else "Dalej",
            icon=ft.Icons.CHECK if ostatni else ft.Icons.ARROW_FORWARD,
            style=w.styl_przycisku(),
        )

        def odswiez():
            wybrana = self.kreator.get(enum_cls)
            opcje.controls = [self.karta_opcji(o, o == wybrana, wybierz) for o in enum_cls]
            dalej.disabled = wybrana is None

        def wybierz(wartosc):
            self.kreator[enum_cls] = wartosc
            odswiez()
            self.page.update()

        def dalej_klik(e=None):
            if ostatni:
                self.zakoncz_kreator()
            else:
                self.idz(TRASY_KREATORA[nr])

        def wstecz(e=None):
            if nr > 1:
                self.idz(TRASY_KREATORA[nr - 2])
            else:
                self.kreator = {}
                self.idz("/profil")

        dalej.on_click = dalej_klik
        odswiez()
        pasek = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=wstecz, visible=nr > 1 or edycja),
            ft.Container(
                content=ft.ProgressBar(value=nr / len(w.KROKI), bar_height=8, border_radius=8),
                expand=True,
            ),
        ], spacing=12, height=48)
        return self.widok(TRASY_KREATORA[nr - 1], [
            pasek,
            ft.Container(height=8),
            ft.Text(f"Krok {nr} z {len(w.KROKI)}", color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_600),
            w.naglowek(pytanie, podpowiedz),
            opcje,
            ft.Container(height=4),
            dalej,
        ])

    def zakoncz_kreator(self) -> None:
        edycja = self.uzytkownik.profil is not None
        profil = ProfilUzytkownika(
            self.kreator[PoziomCzasu], self.kreator[PoziomSlonca], self.kreator[Doswiadczenie]
        )
        self.uzytkownik.wypelnij_ankiete(profil)
        try:
            with repo() as r:
                r.zapisz_uzytkownika(self.uzytkownik)
        except BladBazy as e:
            self.komunikat(str(e))
            return
        self.kreator = {}
        self.tylko_dopasowane = True
        if edycja:
            self.idz("/profil")
            self.komunikat("Zapisano preferencje")
        else:
            self.idz("/odkrywaj")
            self.komunikat("Oto rośliny dopasowane do Ciebie")

    def nawigacja(self, trasa: str) -> ft.NavigationBar:
        return ft.NavigationBar(
            selected_index=TRASY_PANELU.index(trasa),
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.YARD_OUTLINED, selected_icon=ft.Icons.YARD, label="Moje rośliny"),
                ft.NavigationBarDestination(icon=ft.Icons.EXPLORE_OUTLINED, selected_icon=ft.Icons.EXPLORE, label="Odkrywaj"),
                ft.NavigationBarDestination(icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label="Profil"),
            ],
            on_change=lambda e: self.idz(TRASY_PANELU[e.control.selected_index]),
        )

    def wczytaj_kolekcje(self):
        try:
            with repo() as r:
                return r.wczytaj_kolekcje(self.uzytkownik, self.baza)
        except BladBazy as e:
            self.komunikat(str(e))
            return []

    def pusto(self, ikona: str, tytul: str, opis: str, przycisk: ft.Control | None = None) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(ikona, size=44, color=ft.Colors.ON_PRIMARY_CONTAINER),
                        bgcolor=ft.Colors.PRIMARY_CONTAINER,
                        width=96,
                        height=96,
                        border_radius=48,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(tytul, size=18, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                    ft.Text(opis, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                    *([przycisk] if przycisk else []),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            padding=ft.Padding.symmetric(vertical=32, horizontal=12),
        )

    def podsumowanie(self, do_podlania: int) -> ft.Container:
        if do_podlania:
            tytul = f"{do_podlania} {w.odmien(do_podlania, 'roślina czeka', 'rośliny czekają', 'roślin czeka')} na wodę"
            opis = "Kliknij kroplę, gdy podlejesz roślinę."
            ikona, kolory = ft.Icons.WATER_DROP, ["#1565C0", "#42A5F5"]
        else:
            tytul = "Wszystko podlane!"
            opis = "Twoje rośliny mają się świetnie."
            ikona, kolory = ft.Icons.CHECK_CIRCLE, ["#2F7D4A", "#5DB37E"]
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ikona, size=30, color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                    width=56,
                    height=56,
                    border_radius=18,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(tytul, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(opis, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ], spacing=16),
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=kolory),
            border_radius=24,
            padding=20,
        )

    def status_podlewania(self, moja, dzis):
        if moja.czy_podlana(dzis):
            return "Podlana dziś", ft.Colors.PRIMARY, ft.Icons.CHECK_CIRCLE
        dni = moja.dni_do_podlania(dzis)
        if dni < 0:
            return f"Spóźniona o {-dni} {w.odmien(-dni, 'dzień', 'dni', 'dni')}", ft.Colors.ERROR, ft.Icons.WARNING_AMBER
        if dni == 0:
            return "Podlej dziś", ft.Colors.ORANGE_800, ft.Icons.WATER_DROP
        if dni == 1:
            return "Podlej jutro", ft.Colors.ON_SURFACE_VARIANT, ft.Icons.SCHEDULE
        return f"Podlej za {dni} dni", ft.Colors.ON_SURFACE_VARIANT, ft.Icons.SCHEDULE

    def karta_mojej(self, moja, dzis, przelacz, usunieto) -> ft.Container:
        r = moja.roslina
        podlana = moja.czy_podlana(dzis)
        status, kolor, ikona = self.status_podlewania(moja, dzis)
        nawodnienie = min(1.0, max(0.04, moja.dni_do_podlania(dzis) / r.cykl_nawadniania_dni))
        przycisk = ft.IconButton(
            icon=ft.Icons.WATER_DROP_OUTLINED,
            selected_icon=ft.Icons.WATER_DROP,
            selected=podlana,
            icon_size=28,
            icon_color=w.WODA,
            selected_icon_color=ft.Colors.WHITE,
            tooltip="Cofnij podlanie" if podlana else "Oznacz jako podlaną",
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.SELECTED: w.WODA,
                    ft.ControlState.DEFAULT: ft.Colors.with_opacity(0.12, w.WODA),
                },
                shape=ft.RoundedRectangleBorder(radius=18),
                padding=14,
            ),
            on_click=lambda e: przelacz(moja),
        )
        return w.karta(
            ft.Row([
                w.awatar_rosliny(r),
                ft.Column(
                    [
                        ft.Text(r.nazwa_polska, size=17, weight=ft.FontWeight.W_600),
                        ft.Row(
                            [ft.Icon(ikona, size=15, color=kolor), ft.Text(status, size=13, color=kolor, weight=ft.FontWeight.W_500)],
                            spacing=4,
                        ),
                        ft.ProgressBar(
                            value=nawodnienie,
                            color=w.WODA,
                            bgcolor=ft.Colors.with_opacity(0.15, w.WODA),
                            bar_height=6,
                            border_radius=6,
                        ),
                    ],
                    spacing=6,
                    expand=True,
                ),
                przycisk,
            ], spacing=14),
            on_click=lambda e: self.szczegoly(r, moja, usunieto),
        )

    def widok_panelu(self) -> ft.View:
        dzis = w.dzisiaj()
        kolekcja = sorted(
            self.wczytaj_kolekcje(),
            key=lambda m: (m.czy_podlana(dzis), m.dni_do_podlania(dzis)),
        )
        podsumowanie = ft.Container()
        lista = ft.Column(spacing=12)

        def odswiez():
            do_podlania = sum(1 for m in kolekcja if not m.czy_podlana(dzis) and m.dni_do_podlania(dzis) <= 0)
            podsumowanie.content = self.podsumowanie(do_podlania) if kolekcja else None
            lista.controls = [self.karta_mojej(m, dzis, przelacz, usunieto) for m in kolekcja] or [self.pusto(
                ft.Icons.LOCAL_FLORIST,
                "Nie masz jeszcze roślin",
                "Dodaj pierwszą roślinę, a przypomnimy Ci o podlewaniu.",
                ft.FilledButton("Znajdź rośliny", icon=ft.Icons.EXPLORE, on_click=lambda e: self.idz("/odkrywaj")),
            )]

        def przelacz(moja):
            podlana = not moja.czy_podlana(dzis)
            try:
                with repo() as r:
                    r.zapisz_podlanie(self.uzytkownik, moja, dzis, podlana)
            except BladBazy as e:
                self.komunikat(str(e))
                return
            if podlana:
                moja.podlej(dzis)
            else:
                moja.cofnij_podlanie(dzis)
            odswiez()
            self.page.update()
            self.komunikat(f"{moja.roslina.nazwa_polska}: podlana" if podlana else "Cofnięto podlanie")

        def usunieto(moja):
            kolekcja.remove(moja)
            odswiez()
            self.page.update()

        odswiez()
        return self.widok(
            "/panel",
            [
                w.naglowek(f"Cześć, {self.uzytkownik.nazwa}!", w.data_slownie(dzis).capitalize()),
                podsumowanie,
                *([w.sekcja("Moje rośliny")] if kolekcja else []),
                lista,
                ft.Container(height=64),
            ],
            navigation_bar=self.nawigacja("/panel"),
            floating_action_button=ft.FloatingActionButton(
                icon=ft.Icons.ADD, tooltip="Dodaj roślinę", on_click=lambda e: self.idz("/odkrywaj"),
            ),
        )

    def karta_katalogu(self, r, posiadana: bool, pasuje: bool, dodaj) -> ft.Container:
        if posiadana:
            przycisk = ft.FilledTonalButton("W kolekcji", icon=ft.Icons.CHECK, disabled=True)
        else:
            przycisk = ft.FilledButton("Dodaj", icon=ft.Icons.ADD, on_click=lambda e: dodaj(r))
        znaczki = [
            w.znaczek(f"co {r.cykl_nawadniania_dni} {w.odmien(r.cykl_nawadniania_dni, 'dzień', 'dni', 'dni')}", ft.Icons.WATER_DROP),
            w.znaczek(w.etykieta(r.wymagane_slonce), w.ikona_opcji(r.wymagane_slonce)),
            w.znaczek(w.etykieta(r.trudnosc), w.ikona_opcji(r.trudnosc)),
        ]
        if pasuje:
            znaczki.insert(0, w.znaczek(
                "Pasuje do Ciebie", ft.Icons.AUTO_AWESOME,
                kolor=ft.Colors.ON_PRIMARY_CONTAINER, tlo=ft.Colors.PRIMARY_CONTAINER,
            ))
        return w.karta(
            ft.Column([
                ft.Row([
                    w.awatar_rosliny(r),
                    ft.Column(
                        [
                            ft.Text(r.nazwa_polska, size=17, weight=ft.FontWeight.W_600),
                            ft.Text(r.nazwa_lacinska, size=13, italic=True, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    przycisk,
                ], spacing=14),
                ft.Text(r.opis, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row(znaczki, wrap=True, spacing=6, run_spacing=6),
            ], spacing=10),
            on_click=lambda e: self.szczegoly(r),
        )

    def widok_odkrywania(self) -> ft.View:
        posiadane = {m.roslina.id for m in self.wczytaj_kolekcje()}
        profil = self.uzytkownik.profil
        lista = ft.Column(spacing=12)

        def odswiez():
            rosliny = self.baza.wyszukaj(self.fraza) if self.fraza.strip() else self.baza.rosliny
            if self.tylko_dopasowane:
                rosliny = [r for r in rosliny if profil.czy_pasuje(r)]
            lista.controls = [
                self.karta_katalogu(r, r.id in posiadane, profil.czy_pasuje(r), dodaj) for r in rosliny
            ] or [self.pusto(
                ft.Icons.SEARCH_OFF,
                "Nic nie znaleziono",
                "Spróbuj innej nazwy albo pokaż wszystkie rośliny.",
            )]

        def dodaj(r):
            try:
                with repo() as rp:
                    rp.dodaj_do_kolekcji(self.uzytkownik, r, w.dzisiaj())
            except BladBazy as e:
                self.komunikat(str(e))
                return
            posiadane.add(r.id)
            odswiez()
            self.page.update()
            self.komunikat(f"Dodano: {r.nazwa_polska}", akcja="Moje rośliny", trasa="/panel")

        def szukaj(e):
            self.fraza = e.control.value or ""
            odswiez()
            self.page.update()

        def filtruj(e):
            self.tylko_dopasowane = e.control.selected == ["dla_mnie"]
            odswiez()
            self.page.update()

        odswiez()
        return self.widok(
            "/odkrywaj",
            [
                w.naglowek("Odkrywaj", "Znajdź rośliny, które u Ciebie przetrwają."),
                w.pole("Szukaj rośliny", ft.Icons.SEARCH, value=self.fraza, on_change=szukaj),
                ft.SegmentedButton(
                    segments=[
                        ft.Segment(value="dla_mnie", label=ft.Text("Dla mnie"), icon=ft.Icon(ft.Icons.AUTO_AWESOME)),
                        ft.Segment(value="wszystkie", label=ft.Text("Wszystkie"), icon=ft.Icon(ft.Icons.GRID_VIEW)),
                    ],
                    selected=["dla_mnie" if self.tylko_dopasowane else "wszystkie"],
                    show_selected_icon=False,
                    on_change=filtruj,
                ),
                lista,
            ],
            navigation_bar=self.nawigacja("/odkrywaj"),
        )

    def widok_profilu(self) -> ft.View:
        u = self.uzytkownik
        p = u.profil
        liczba = len(self.wczytaj_kolekcje())
        preferencje = [
            ("Czas na opiekę", p.czas_na_opieke),
            ("Nasłonecznienie", p.naslonecznienie_domu),
            ("Doświadczenie", p.doswiadczenie),
        ]

        def zmien(e):
            self.kreator = {}
            self.idz(TRASY_KREATORA[0])

        return self.widok(
            "/profil",
            [
                ft.Row([
                    ft.CircleAvatar(
                        content=ft.Text(u.nazwa[:1].upper(), size=30, weight=ft.FontWeight.W_600),
                        radius=38,
                        bgcolor=ft.Colors.PRIMARY_CONTAINER,
                        color=ft.Colors.ON_PRIMARY_CONTAINER,
                    ),
                    ft.Column(
                        [
                            ft.Text(u.nazwa, size=24, weight=ft.FontWeight.BOLD),
                            ft.Text(u.email, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ], spacing=16),
                w.karta(ft.Row([
                    ft.Icon(ft.Icons.YARD, color=ft.Colors.PRIMARY),
                    ft.Text(
                        f"{liczba} {w.odmien(liczba, 'roślina', 'rośliny', 'roślin')} w kolekcji",
                        size=16, weight=ft.FontWeight.W_500,
                    ),
                ], spacing=12), padding=18),
                w.sekcja("Twoje preferencje"),
                w.karta(ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(w.ikona_opcji(wartosc), color=ft.Colors.PRIMARY),
                        title=ft.Text(tytul),
                        subtitle=ft.Text(w.etykieta(wartosc)),
                    )
                    for tytul, wartosc in preferencje
                ], spacing=0), padding=4),
                ft.FilledTonalButton("Zmień preferencje", icon=ft.Icons.TUNE, on_click=zmien, style=w.styl_przycisku()),
                ft.OutlinedButton(
                    "Wyloguj się",
                    icon=ft.Icons.LOGOUT,
                    on_click=self.wyloguj,
                    style=ft.ButtonStyle(
                        color=ft.Colors.ERROR,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
                    ),
                ),
            ],
            navigation_bar=self.nawigacja("/profil"),
        )

    def wiersz_info(self, ikona: str, tytul: str, opis: str) -> ft.Row:
        return ft.Row([
            ft.Container(
                content=ft.Icon(ikona, size=20, color=ft.Colors.PRIMARY),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                width=40,
                height=40,
                border_radius=12,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column(
                [ft.Text(tytul, weight=ft.FontWeight.W_600), ft.Text(opis, color=ft.Colors.ON_SURFACE_VARIANT)],
                spacing=2,
                expand=True,
            ),
        ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)

    def szczegoly(self, r, moja=None, usunieto=None) -> None:
        cykl = r.cykl_nawadniania_dni
        elementy = [
            ft.Row([
                w.awatar_rosliny(r, 64),
                ft.Column(
                    [
                        ft.Text(r.nazwa_polska, size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(r.nazwa_lacinska, italic=True, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ], spacing=16),
            ft.Text(r.opis, size=15),
            self.wiersz_info(
                ft.Icons.WATER_DROP, f"Podlewanie co {cykl} {w.odmien(cykl, 'dzień', 'dni', 'dni')}", r.instrukcja_podlewania
            ),
            self.wiersz_info(
                w.ikona_opcji(r.wymagane_slonce), f"Światło: {w.etykieta(r.wymagane_slonce)}", r.instrukcja_slonca
            ),
            self.wiersz_info(
                w.ikona_opcji(r.trudnosc), f"Poziom: {w.etykieta(r.trudnosc)}", f"Czas opieki: {w.etykieta(r.czas_opieki)}"
            ),
        ]
        choroby = r.pobierz_choroby()
        if choroby:
            elementy.append(w.sekcja("Na co uważać"))
            for c in choroby:
                objawy = ", ".join(o.opis for o in c.pobierz_objawy())
                elementy.append(w.karta(ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.HEALING, color=ft.Colors.ERROR, size=20),
                        ft.Text(c.nazwa, weight=ft.FontWeight.W_600),
                    ], spacing=8),
                    ft.Text(f"Objawy: {objawy}", size=14),
                    ft.Text(f"Leczenie: {c.pobierz_procedure_leczenia()}", size=14),
                ], spacing=6), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=16))
        if moja is not None:
            ostatnie = moja.ostatnie_podlanie
            elementy.append(self.wiersz_info(
                ft.Icons.CALENDAR_TODAY,
                "Ostatnie podlanie",
                w.data_slownie(ostatnie) if ostatnie else "Jeszcze nie podlewana",
            ))
            elementy.append(ft.TextButton(
                "Usuń z kolekcji",
                icon=ft.Icons.DELETE_OUTLINE,
                style=ft.ButtonStyle(color=ft.Colors.ERROR),
                on_click=lambda e: self.potwierdz_usuniecie(moja, usunieto),
            ))
        self.page.show_dialog(ft.BottomSheet(
            content=ft.Container(
                content=ft.Column(elementy, spacing=16, tight=True, scroll=ft.ScrollMode.AUTO),
                padding=ft.Padding.only(left=24, right=24, top=4, bottom=32),
            ),
            show_drag_handle=True,
            scrollable=True,
        ))

    def potwierdz_usuniecie(self, moja, usunieto) -> None:
        self.page.pop_dialog()

        def usun(e):
            self.page.pop_dialog()
            try:
                with repo() as r:
                    r.usun_z_kolekcji(self.uzytkownik, moja)
            except BladBazy as ex:
                self.komunikat(str(ex))
                return
            usunieto(moja)
            self.komunikat(f"Usunięto: {moja.roslina.nazwa_polska}")

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"Usunąć {moja.roslina.nazwa_polska}?"),
            content=ft.Text("Roślina i historia jej podlewania znikną z Twojej kolekcji."),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Usuń", on_click=usun, style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR)),
            ],
        ))


async def main(page: ft.Page) -> None:
    page.title = "Oasis"
    page.theme = w.motyw()
    page.dark_theme = w.motyw()
    page.padding = 0
    try:
        baza = przygotuj_baze()
    except BladBazy as e:
        page.add(ft.SafeArea(content=ft.Text(f"Błąd bazy: {e}", color=ft.Colors.ERROR)))
        return
    await Aplikacja(page, baza).start()


if __name__ == "__main__":
    if os.getenv("PORT"):
        os.environ.setdefault("FLET_FORCE_WEB_SERVER", "true")
        os.environ.setdefault("FLET_SERVER_IP", "0.0.0.0")
        os.environ.setdefault("FLET_SERVER_PORT", os.environ["PORT"])
    ft.run(main)
