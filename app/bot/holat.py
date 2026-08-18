import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

REJIMLAR = ("oddiy", "pro")
STANDART_REJIM = "oddiy"


OVOZ_TANLOVLARI = ("avto", "doim", "yoq")
STANDART_OVOZ = "avto"


CHEKLOV_DAVRI = 600
CHEKLOV_CHEGARASI = 20

_rejimlar: Dict[int, str] = {}
_ovoz_sozlamalari: Dict[int, str] = {}
_sorovlar: Dict[int, list] = {}
_band: Dict[int, float] = {}

_javoblar: "OrderedDict[str, dict]" = OrderedDict()
JAVOB_XOTIRASI = 50
_javob_sanagichi = 0


BAND_MUDDATI = 180


def rejim(foydalanuvchi_id: int) -> str:
    return _rejimlar.get(foydalanuvchi_id, STANDART_REJIM)


def rejim_belgila(foydalanuvchi_id: int, yangi: str) -> str:
    _rejimlar[foydalanuvchi_id] = yangi if yangi in REJIMLAR else STANDART_REJIM
    return _rejimlar[foydalanuvchi_id]


def ovoz_sozlamasi(foydalanuvchi_id: int) -> str:
    return _ovoz_sozlamalari.get(foydalanuvchi_id, STANDART_OVOZ)


def ovoz_belgila(foydalanuvchi_id: int, yangi: str) -> str:
    _ovoz_sozlamalari[foydalanuvchi_id] = (
        yangi if yangi in OVOZ_TANLOVLARI else STANDART_OVOZ
    )
    return _ovoz_sozlamalari[foydalanuvchi_id]


def ovoz_kerakmi(foydalanuvchi_id: int, ovozli_savol: bool) -> bool:
    """Shu javobga ovoz qo'shiladimi.

    Standart "avto" mantiqi: ovozli savol bergan odam javobni ham quloqqa
    kutadi (ehtimol qo'li band yoki o'qishga qiynaladi), matn yozgan odam esa
    kutmagan ovozdan bezovta bo'ladi.
    """
    sozlama = ovoz_sozlamasi(foydalanuvchi_id)
    if sozlama == "doim":
        return True
    if sozlama == "yoq":
        return False
    return ovozli_savol


def javobni_saqla(foydalanuvchi_id: int, savol: str, javob) -> str:
    """Javobni saqlaydi va uning kalitini qaytaradi.

    Kalit inline tugmalarning callback_data'sida yuradi: moddalarni ochish ham,
    ariza tuzish ham AYNAN o'sha javobga tegishli bo'lishi kerak.
    """
    global _javob_sanagichi
    _javob_sanagichi += 1
    kalit = f"{foydalanuvchi_id}-{_javob_sanagichi}"
    _javoblar[kalit] = {
        "savol": savol,
        "modda_idlari": [m.id for m in javob.moddalar][:3],
        "murojaat_mavzusi": javob.murojaat_mavzusi,
    }
    while len(_javoblar) > JAVOB_XOTIRASI:
        _javoblar.popitem(last=False)
    return kalit


def javob_malumoti(kalit: str) -> Optional[dict]:
    return _javoblar.get(kalit)


def cheklovdan_otdi(foydalanuvchi_id: int) -> Tuple[bool, int]:
    """(ruxsat, necha soniyadan keyin qayta urinish mumkin) qaytaradi."""
    hozir = time.time()
    vaqtlar = [t for t in _sorovlar.get(foydalanuvchi_id, []) if hozir - t < CHEKLOV_DAVRI]
    _sorovlar[foydalanuvchi_id] = vaqtlar
    if len(vaqtlar) >= CHEKLOV_CHEGARASI:
        return False, int(CHEKLOV_DAVRI - (hozir - vaqtlar[0])) + 1
    vaqtlar.append(hozir)
    return True, 0


def band_qil(foydalanuvchi_id: int) -> bool:
    """So'rovni band deb belgilaydi. Oldingisi tugamagan bo'lsa False.

    Bitta foydalanuvchining ketma-ket yuborgan savollari navbatsiz
    bajarilsa, ular bir vaqtda LLM'ga borib javoblar aralashib ketadi.
    """
    hozir = time.time()
    boshlangan = _band.get(foydalanuvchi_id)
    if boshlangan is not None and hozir - boshlangan < BAND_MUDDATI:
        return False
    _band[foydalanuvchi_id] = hozir
    return True


def bandni_bosat(foydalanuvchi_id: int) -> None:
    _band.pop(foydalanuvchi_id, None)


def tozala() -> None:
    """Testlar uchun."""
    for saqlagich in (_rejimlar, _ovoz_sozlamalari, _javoblar, _sorovlar, _band):
        saqlagich.clear()
