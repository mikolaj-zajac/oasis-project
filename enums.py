from enum import Enum, IntEnum


class Rola(Enum):
    UZYTKOWNIK = "użytkownik"
    ADMINISTRATOR = "administrator"


class PoziomSlonca(IntEnum):
    CIEN = 1
    POLCIEN = 2
    JASNE = 3
    PELNE_SLONCE = 4


class PoziomCzasu(IntEnum):
    MALO = 1
    SREDNIO = 2
    DUZO = 3


class Doswiadczenie(IntEnum):
    POCZATKUJACY = 1
    SREDNIO = 2
    ZAAWANSOWANY = 3
