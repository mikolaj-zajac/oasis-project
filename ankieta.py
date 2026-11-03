import re
from enum import Enum

from enums import PoziomCzasu, PoziomSlonca, Doswiadczenie


class BladWalidacji(ValueError):
    """Błędne dane wpisane przez użytkownika."""


def waliduj_imie(tekst: str) -> str:
    tekst = tekst.strip()
    if not tekst:
        raise BladWalidacji("Imię nie może być puste.")
    if not 2 <= len(tekst) <= 50:
        raise BladWalidacji("Imię musi mieć od 2 do 50 znaków.")
    if not all(c.isalpha() or c in " -" for c in tekst):
        raise BladWalidacji("Imię może zawierać tylko litery, spacje i myślniki (bez cyfr).")
    return tekst.title()


def waliduj_email(tekst: str) -> str:
    tekst = tekst.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", tekst):
        raise BladWalidacji("Niepoprawny adres e-mail (np. jan@example.com).")
    return tekst.lower()


def waliduj_wybor(tekst: str, enum_cls: type[Enum]) -> Enum:
    opcje = list(enum_cls)
    try:
        numer = int(tekst.strip())
    except ValueError:
        raise BladWalidacji("Wpisz numer opcji (liczbę).") from None
    if not 1 <= numer <= len(opcje):
        raise BladWalidacji(f"Wybierz liczbę od 1 do {len(opcje)}.")
    return opcje[numer - 1]


def zapytaj(pytanie: str, walidator):
    """Pyta aż do skutku; błędy walidacji są łapane i pokazywane użytkownikowi."""
    while True:
        try:
            return walidator(input(pytanie))
        except BladWalidacji as e:
            print(f"  ! {e}")
        except (EOFError, KeyboardInterrupt):
            print("\nAnkieta przerwana.")
            raise


def zapytaj_o_wybor(pytanie: str, enum_cls: type[Enum]):
    print(pytanie)
    for i, opcja in enumerate(enum_cls, 1):
        print(f"  {i}. {opcja.name}")
    return zapytaj("> ", lambda t: waliduj_wybor(t, enum_cls))


def ankieta_profilu():
    """Ankieta dopasowania roślin -> ProfilUzytkownika."""
    from modele import ProfilUzytkownika

    czas = zapytaj_o_wybor("Ile czasu możesz poświęcić na opiekę nad roślinami?", PoziomCzasu)
    slonce = zapytaj_o_wybor("Jak nasłoneczniony jest Twój dom?", PoziomSlonca)
    dosw = zapytaj_o_wybor("Jakie masz doświadczenie z roślinami?", Doswiadczenie)
    return ProfilUzytkownika(czas, slonce, dosw)


def ankieta_startowa(id_uzytkownika: int = 1):
    """Rejestracja (imię, e-mail) + ankieta profilu. Zwraca Uzytkownik z profilem."""
    from modele import Uzytkownik

    print("=== Oasis – ankieta startowa ===")
    imie = zapytaj("Podaj imię: ", waliduj_imie)
    email = zapytaj("Podaj e-mail: ", waliduj_email)
    uzytkownik = Uzytkownik(id_uzytkownika, imie, email)
    uzytkownik.wypelnij_ankiete()
    return uzytkownik
