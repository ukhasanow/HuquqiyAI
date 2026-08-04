# Foydalanuvchi holati va so'rov cheklovlari (xotirada).
#
# Ma'lumot diskka yozilmaydi: Render bepul tierda jarayon qayta ishga
# tushganda rejim standart holatga qaytadi — bu yo'qotish arzimas, buning
# uchun baza qo'shish esa ortiqcha murakkablik.
import time
from typing import Dict, Optional, Tuple

REJIMLAR = ("oddiy", "pro")
STANDART_REJIM = "oddiy"

# Bir foydalanuvchi uchun: DAVR soniyada eng ko'pi bilan CHEGARA ta so'rov.
# Maqsad — bitta odam butun AI byudjetini yoqib yuborishining oldini olish.
CHEKLOV_DAVRI = 600
CHEKLOV_CHEGARASI = 20

_rejimlar: Dict[int, str] = {}
_ovoz_yoqilgan: Dict[int, bool] = {}
_oxirgi_javob: Dict[int, dict] = {}
_sorovlar: Dict[int, list] = {}
_band: Dict[int, float] = {}

# Bitta so'rov shuncha soniyadan uzoq davom etsa, "band" belgisi eskirgan
# hisoblanadi (masalan jarayon xato bergan). Aks holda foydalanuvchi bot
# bilan butunlay ishlay olmay qoladi.
BAND_MUDDATI = 180


def rejim(foydalanuvchi_id: int) -> str:
    return _rejimlar.get(foydalanuvchi_id, STANDART_REJIM)


def rejim_belgila(foydalanuvchi_id: int, yangi: str) -> str:
    _rejimlar[foydalanuvchi_id] = yangi if yangi in REJIMLAR else STANDART_REJIM
    return _rejimlar[foydalanuvchi_id]


def ovoz_yoqilgan(foydalanuvchi_id: int) -> bool:
    """Ovozli javob yoqilganmi (5-bosqich). Standart holat: o'chiq —
    ovozli savolga ovoz bilan javob berish alohida hal qilinadi."""
    return _ovoz_yoqilgan.get(foydalanuvchi_id, False)


def ovoz_almashtir(foydalanuvchi_id: int) -> bool:
    _ovoz_yoqilgan[foydalanuvchi_id] = not ovoz_yoqilgan(foydalanuvchi_id)
    return _ovoz_yoqilgan[foydalanuvchi_id]


def javobni_saqla(foydalanuvchi_id: int, savol: str, javob) -> None:
    """Ariza tuzish uchun oxirgi javobning modda va mavzusi kerak bo'ladi."""
    _oxirgi_javob[foydalanuvchi_id] = {
        "savol": savol,
        "modda_idlari": [m.id for m in javob.moddalar][:3],
        "murojaat_mavzusi": javob.murojaat_mavzusi,
    }


def oxirgi_javob(foydalanuvchi_id: int) -> Optional[dict]:
    return _oxirgi_javob.get(foydalanuvchi_id)


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
    for saqlagich in (_rejimlar, _ovoz_yoqilgan, _oxirgi_javob, _sorovlar, _band):
        saqlagich.clear()
