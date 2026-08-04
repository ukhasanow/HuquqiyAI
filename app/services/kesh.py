# Javob keshi: bir xil savol qayta so'ralganda LLM'ga umuman murojaat qilinmaydi.
#
# Nima uchun kerak: javob vaqtining deyarli hammasi model matn yozishiga ketadi
# (~40 token/sekund), ya'ni har bir yangi savol 10-20 sekund. Ommabop savollar
# esa qayta-qayta so'raladi — ularni keshdan qaytarish javobni bir zumda qiladi
# va AI xizmati xarajatini kamaytiradi.
#
# Kesh FAQAT mustaqil savollar uchun ishlaydi: suhbat tarixi yoki yuklangan
# hujjat bo'lsa javob kontekstga bog'liq bo'ladi va keshlanmaydi.
import re
import threading
import time
from collections import OrderedDict
from typing import Optional

from .retrieval import _APOSTROFLAR, _kirilldan_lotinga

# Yozuv qancha vaqt yaroqli (sekund). Baza o'zgarsa muddatdan qat'i nazar
# yozuv bekor bo'ladi — versiya kalitga kiradi.
MUDDAT = 6 * 3600
MAX_YOZUV = 500

_lock = threading.Lock()
# kalit -> (yaratilgan_vaqt, javob)
_yozuvlar: "OrderedDict[str, tuple]" = OrderedDict()


def kalit(savol: str, rejim: str, versiya: str, batafsil: bool = False) -> Optional[str]:
    """Savolni kesh kalitiga aylantiradi.

    Faqat yozuv farqlari o'chiriladi: katta-kichik harf, apostrof turlari,
    kirill/lotin va tinish belgilari. Shu sababli "Aliment to'lamayapti",
    "aliment tolamayapti" va "Алимент тўламаяпти" bitta yozuvga tushadi.

    MUHIM: so'z tartibi va raqamlar SAQLANADI. Qidiruvdagi normalizatsiya
    (_normalizatsiya) bu yerda ishlatilmaydi — u qisqa so'zlar bilan raqamlarni
    tashlab, so'zlarni saralaydi. Qidiruv uchun bu foydali, kesh kaliti uchun esa
    xavfli: "3 oydan beri" bilan "5 oydan beri", hatto "men uni urdim" bilan
    "u meni urdi" bir xil kalit berib, noto'g'ri javob qaytishi mumkin edi.
    """
    s = savol.lower().translate(_APOSTROFLAR)
    s = _kirilldan_lotinga(s)
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    if not s:
        return None
    # batafsil kalitga kiradi: bot va sayt javoblari hajmi bilan farq qiladi,
    # birining javobini ikkinchisiga berib bo'lmaydi.
    return f"{versiya}|{rejim}|{'batafsil' if batafsil else 'qisqa'}|{s}"


def ol(k: Optional[str]):
    """Yaroqli javob bo'lsa qaytaradi, aks holda None."""
    if not k:
        return None
    with _lock:
        yozuv = _yozuvlar.get(k)
        if yozuv is None:
            return None
        vaqt, javob = yozuv
        if time.monotonic() - vaqt > MUDDAT:
            _yozuvlar.pop(k, None)
            return None
        _yozuvlar.move_to_end(k)  # eng ko'p ishlatilgani saqlanib qolsin
        return javob


def qoy(k: Optional[str], javob) -> None:
    if not k:
        return
    with _lock:
        _yozuvlar[k] = (time.monotonic(), javob)
        _yozuvlar.move_to_end(k)
        while len(_yozuvlar) > MAX_YOZUV:
            _yozuvlar.popitem(last=False)


def tozala() -> None:
    with _lock:
        _yozuvlar.clear()


def holat() -> dict:
    with _lock:
        return {"yozuvlar": len(_yozuvlar), "chegara": MAX_YOZUV}
