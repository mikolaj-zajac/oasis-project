from ankieta import ankieta_startowa
from baza_sql import BladBazy, Repozytorium
from dane import zaladuj_przykladowa_baze


def main() -> None:
    try:
        repo = Repozytorium()
    except BladBazy as e:
        print(f"Błąd: {e}")
        return

    with repo:
        try:
            if repo.czy_pusta():
                repo.zapisz_baze(zaladuj_przykladowa_baze())
            baza = repo.wczytaj_baze()
        except BladBazy as e:
            print(f"Błąd: {e}")
            return

        try:
            uzytkownik = ankieta_startowa()
        except (EOFError, KeyboardInterrupt):
            return

        profil = uzytkownik.profil
        try:
            repo.zapisz_uzytkownika(uzytkownik)
        except BladBazy as e:
            print(f"Uwaga: {e}")
        try:
            profil.zapisz_wynik()
        except IOError as e:
            print(f"Uwaga: {e}")

        print(f"\nCześć {uzytkownik.nazwa}! Rośliny dopasowane do Ciebie:")
        dopasowane = baza.dopasuj(profil)
        if not dopasowane:
            print("  (brak pasujących roślin)")
        for r in dopasowane:
            print(f"\n* {r}\n{r.pobierz_instrukcje()}")
            for c in r.pobierz_choroby():
                print(f"  Podatna na: {c} -> {c.pobierz_procedure_leczenia()}")


if __name__ == "__main__":
    main()
