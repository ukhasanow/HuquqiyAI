import hashlib
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Optional

import httpx

from ..config import KESH_KV_MUDDATI, STATISTIKA_KV_TOKEN, STATISTIKA_KV_URL
from ..models import ChatJavob
from .retrieval import _APOSTROFLAR, _kirilldan_lotinga

log = logging.getLogger(__name__)


MUDDAT = 6 * 3600
MAX_YOZUV = 500


KV_MUDDATI = 3.0
KV_PREFIKS = "kesh"

_lock = threading.Lock()
# kalit -> (yaratilgan_vaqt, javob)
_yozuvlar: "OrderedDict[str, tuple]" = OrderedDict()





def tashqi_saqlash() -> bool:
    return bool(STATISTIKA_KV_URL and STATISTIKA_KV_TOKEN)


def _kv_kalit(k: str) -> str:
    """Kesh kalitini URL uchun xavfsiz va qisqa ko'rinishga keltiradi.

    Kalit ichida savol matni bor: bo'sh joy, `|` va uzun matn URL'ni buzadi.
    Hash uzunlikni ham chegaralaydi — uzun savol ham 64 belgiga sig'adi.
    """
    return f"{KV_PREFIKS}:{hashlib.sha256(k.encode('utf-8')).hexdigest()}"


def _kv_ol(k: str) -> Optional[ChatJavob]:
    if not tashqi_saqlash():
        return None
    try:
        javob = httpx.get(
            f"{STATISTIKA_KV_URL}/get/{_kv_kalit(k)}",
            headers={"Authorization": f"Bearer {STATISTIKA_KV_TOKEN}"},
            timeout=KV_MUDDATI,
        )
        javob.raise_for_status()
        xom = javob.json().get("result")
        return ChatJavob.model_validate_json(xom) if xom else None
    except Exception as e:
        # Kesh yo'qligi xato emas — javob baribir LLM'dan olinadi.
        log.warning("Keshni tashqi ombordan o'qib bo'lmadi: %s", e)
        return None


def _kv_qoy(k: str, javob: ChatJavob) -> bool:
    if not tashqi_saqlash():
        return False
    try:
        r = httpx.post(
            f"{STATISTIKA_KV_URL}/setex/{_kv_kalit(k)}/{KESH_KV_MUDDATI}",
            headers={"Authorization": f"Bearer {STATISTIKA_KV_TOKEN}"},
            content=javob.model_dump_json().encode("utf-8"),
            timeout=KV_MUDDATI,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning("Keshni tashqi omborga yozib bo'lmadi: %s", e)
        return False


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


def _xotiradan(k: str):
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


def _xotiraga(k: str, javob) -> None:
    with _lock:
        _yozuvlar[k] = (time.monotonic(), javob)
        _yozuvlar.move_to_end(k)
        while len(_yozuvlar) > MAX_YOZUV:
            _yozuvlar.popitem(last=False)


def ol(k: Optional[str]):
    """Yaroqli javob bo'lsa qaytaradi, aks holda None.

    Avval xotira (tarmoqsiz, ~0 ms), keyin tashqi ombor. Tashqidan topilsa
    xotiraga ko'chiriladi — o'sha savol qayta so'ralganda tarmoq kerak bo'lmaydi.
    """
    if not k:
        return None
    javob = _xotiradan(k)
    if javob is not None:
        return javob
    javob = _kv_ol(k)
    if javob is not None:
        _xotiraga(k, javob)
    return javob


def qoy(k: Optional[str], javob) -> None:
    """Ikkala qavatga ham yozadi. Tashqi ombor yiqilsa xotira baribir ishlaydi."""
    if not k:
        return
    _xotiraga(k, javob)
    _kv_qoy(k, javob)


def tozala() -> None:
    """Faqat xotirani tozalaydi (testlar uchun) — tashqi omborga tegmaydi."""
    with _lock:
        _yozuvlar.clear()


def holat() -> dict:
    """Kesh holati. `saqlash` eng muhimi: "xotira" bo'lsa isitilgan kesh
    Render uyg'onishi bilan yo'qoladi va isitish behuda ketgan bo'ladi."""
    with _lock:
        return {
            "yozuvlar": len(_yozuvlar),
            "chegara": MAX_YOZUV,
            "saqlash": "tashqi" if tashqi_saqlash() else "xotira",
        }
