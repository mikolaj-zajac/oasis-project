from enums import Rola, PoziomSlonca, PoziomCzasu, Doswiadczenie
from modele import BazaRoslin, Choroba, Roslina, Uzytkownik


def zaladuj_przykladowa_baze() -> BazaRoslin:
    admin = Uzytkownik(0, "Admin", "admin@oasis.pl", Rola.ADMINISTRATOR)
    baza = BazaRoslin()

    zgnilizna = Choroba(1, "Zgnilizna korzeni", "Przelanie powoduje gnicie korzeni.",
                        "Wyjmij roślinę, usuń zgniłe korzenie, przesadź do suchego podłoża.")
    zgnilizna.dodaj_objaw(1, "Żółknące, miękkie liście")
    zgnilizna.dodaj_objaw(2, "Nieprzyjemny zapach ziemi")

    mszyce = Choroba(2, "Mszyce", "Małe owady wysysające soki z liści.",
                     "Opłucz liście wodą, zastosuj mydło potasowe.")
    mszyce.dodaj_objaw(3, "Lepkie, zwinięte liście")

    kaktus = Roslina(1, "Kaktus", "Cactaceae", "Odporny na suszę.", 21,
                     "Podlewaj rzadko, tylko gdy ziemia sucha.", PoziomSlonca.PELNE_SLONCE,
                     "Postaw na najjaśniejszym parapecie.", Doswiadczenie.POCZATKUJACY, PoziomCzasu.MALO)
    paproc = Roslina(2, "Paproć", "Nephrolepis exaltata", "Lubi wilgoć.", 3,
                     "Utrzymuj stale wilgotne podłoże.", PoziomSlonca.POLCIEN,
                     "Unikaj bezpośredniego słońca.", Doswiadczenie.SREDNIO, PoziomCzasu.DUZO)
    zamiokulkas = Roslina(3, "Zamiokulkas", "Zamioculcas zamiifolia", "Bardzo wytrzymały.", 14,
                          "Podlewaj co dwa tygodnie.", PoziomSlonca.CIEN,
                          "Toleruje cień.", Doswiadczenie.POCZATKUJACY, PoziomCzasu.MALO)

    kaktus.dodaj_chorobe(zgnilizna)
    paproc.dodaj_chorobe(mszyce)
    zamiokulkas.dodaj_chorobe(zgnilizna)

    for c in (zgnilizna, mszyce):
        baza.dodaj_chorobe(admin, c)
    for r in (kaktus, paproc, zamiokulkas):
        baza.dodaj_rosline(admin, r)
    return baza
