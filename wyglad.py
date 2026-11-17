from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import flet as ft

from enums import Doswiadczenie, PoziomCzasu, PoziomSlonca

ZIELEN = "#2F7D4A"
WODA = ft.Colors.BLUE_600
ZAOKRAGLENIE = 18
MAKS_SZEROKOSC = 520

OPCJE = {
    PoziomCzasu: {
        PoziomCzasu.MALO: ("Mało", "Kilka minut w tygodniu", ft.Icons.HOURGLASS_BOTTOM),
        PoziomCzasu.SREDNIO: ("Średnio", "Zajrzę do roślin co kilka dni", ft.Icons.SCHEDULE),
        PoziomCzasu.DUZO: ("Dużo", "Chętnie zajmę się nimi codziennie", ft.Icons.EVENT_AVAILABLE),
    },
    PoziomSlonca: {
        PoziomSlonca.CIEN: ("Cień", "Okna na północ, mało światła", ft.Icons.NIGHTS_STAY),
        PoziomSlonca.POLCIEN: ("Półcień", "Światło rozproszone przez część dnia", ft.Icons.WB_CLOUDY),
        PoziomSlonca.JASNE: ("Jasno", "Dużo światła, ale bez ostrego słońca", ft.Icons.LIGHT_MODE),
        PoziomSlonca.PELNE_SLONCE: ("Pełne słońce", "Południowe okna, słońce przez cały dzień", ft.Icons.WB_SUNNY),
    },
    Doswiadczenie: {
        Doswiadczenie.POCZATKUJACY: ("Początkujący", "To moje pierwsze rośliny", ft.Icons.SPA),
        Doswiadczenie.SREDNIO: ("Średnio zaawansowany", "Kilka roślin już u mnie przetrwało", ft.Icons.LOCAL_FLORIST),
        Doswiadczenie.ZAAWANSOWANY: ("Zaawansowany", "Mam w domu własną dżunglę", ft.Icons.PARK),
    },
}

KROKI = [
    (PoziomCzasu, "Ile czasu masz dla roślin?", "Dobierzemy rośliny do Twojego rytmu dnia."),
    (PoziomSlonca, "Jak jasno jest u Ciebie?", "Pomyśl o miejscu, w którym postawisz rośliny."),
    (Doswiadczenie, "Jakie masz doświadczenie?", "Bez obaw, każdy kiedyś zaczynał."),
]

IKONY_ROSLIN = [ft.Icons.ECO, ft.Icons.LOCAL_FLORIST, ft.Icons.GRASS, ft.Icons.SPA, ft.Icons.PARK, ft.Icons.YARD]
KOLORY_ROSLIN = [
    (ft.Colors.PRIMARY_CONTAINER, ft.Colors.ON_PRIMARY_CONTAINER),
    (ft.Colors.TERTIARY_CONTAINER, ft.Colors.ON_TERTIARY_CONTAINER),
    (ft.Colors.SECONDARY_CONTAINER, ft.Colors.ON_SECONDARY_CONTAINER),
]

DNI_TYGODNIA = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MIESIACE = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]


def dzisiaj() -> date:
    try:
        return datetime.now(ZoneInfo("Europe/Warsaw")).date()
    except ZoneInfoNotFoundError:
        return date.today()


def data_slownie(d: date) -> str:
    return f"{DNI_TYGODNIA[d.weekday()]}, {d.day} {MIESIACE[d.month - 1]}"


def odmien(liczba: int, jedna: str, kilka: str, wiele: str) -> str:
    if liczba == 1:
        return jedna
    if 2 <= liczba % 10 <= 4 and not 12 <= liczba % 100 <= 14:
        return kilka
    return wiele


def etykieta(wartosc) -> str:
    return OPCJE[type(wartosc)][wartosc][0]


def ikona_opcji(wartosc) -> str:
    return OPCJE[type(wartosc)][wartosc][2]


def motyw() -> ft.Theme:
    return ft.Theme(color_scheme_seed=ZIELEN)


def styl_przycisku() -> ft.ButtonStyle:
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=14),
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_600),
    )


def ramka(kolor, grubosc: float = 0) -> ft.OutlineInputBorder:
    return ft.OutlineInputBorder(border_radius=14, side=ft.BorderSide(width=grubosc, color=kolor))


def pole(etykieta_pola: str, ikona: str, **kwargs) -> ft.TextField:
    return ft.TextField(
        label=etykieta_pola,
        prefix_icon=ikona,
        filled=True,
        fill_color=ft.Colors.SURFACE_CONTAINER_HIGH,
        border={
            ft.ControlState.DEFAULT: ramka(ft.Colors.TRANSPARENT),
            ft.ControlState.FOCUSED: ramka(ft.Colors.PRIMARY, 2),
            ft.ControlState.ERROR: ramka(ft.Colors.ERROR, 1.5),
        },
        **kwargs,
    )


def awatar_rosliny(roslina, rozmiar: int = 56) -> ft.Container:
    tlo, kolor = KOLORY_ROSLIN[roslina.id % len(KOLORY_ROSLIN)]
    return ft.Container(
        content=ft.Icon(IKONY_ROSLIN[roslina.id % len(IKONY_ROSLIN)], color=kolor, size=rozmiar * 0.5),
        bgcolor=tlo,
        width=rozmiar,
        height=rozmiar,
        border_radius=rozmiar * 0.3,
        alignment=ft.Alignment.CENTER,
    )


def znaczek(tekst: str, ikona: str, kolor=ft.Colors.ON_SURFACE_VARIANT, tlo=ft.Colors.SURFACE_CONTAINER_HIGHEST) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [ft.Icon(ikona, size=14, color=kolor), ft.Text(tekst, size=12, color=kolor, weight=ft.FontWeight.W_500)],
            spacing=4,
            tight=True,
        ),
        bgcolor=tlo,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=20,
    )


def karta(content: ft.Control, on_click=None, **kwargs) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=kwargs.pop("bgcolor", ft.Colors.SURFACE_CONTAINER_LOW),
        border_radius=kwargs.pop("border_radius", ZAOKRAGLENIE),
        padding=kwargs.pop("padding", 14),
        on_click=on_click,
        ink=on_click is not None,
        **kwargs,
    )


def naglowek(tytul: str, podtytul: str | None = None) -> ft.Column:
    elementy = [ft.Text(tytul, size=28, weight=ft.FontWeight.BOLD)]
    if podtytul:
        elementy.append(ft.Text(podtytul, size=15, color=ft.Colors.ON_SURFACE_VARIANT))
    return ft.Column(elementy, spacing=4)


def sekcja(tytul: str) -> ft.Text:
    return ft.Text(tytul, size=18, weight=ft.FontWeight.W_600)
