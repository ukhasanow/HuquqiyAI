import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .config import DATA_DIR

QONUNLAR_FAYL = DATA_DIR / "qonunlar.json"
ORGANLAR_FAYL = DATA_DIR / "organlar.json"

_lock = threading.Lock()


_kesh: Dict[str, tuple] = {}


def _fayl_belgisi(fayl: Path):
    """Fayl o'zgarganini arzon aniqlash uchun (mtime, hajm) juftligi."""
    try:
        st = fayl.stat()
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _oqi(fayl: Path, nom: str) -> list:
    belgi = _fayl_belgisi(fayl)
    saqlangan = _kesh.get(nom)
    if saqlangan is not None and saqlangan[0] == belgi:
        return saqlangan[1]
    with open(fayl, encoding="utf-8") as f:
        malumot = json.load(f)
    _kesh[nom] = (belgi, malumot, {m["id"]: m for m in malumot} if nom == "qonunlar" else None)
    return malumot


def _keshni_tozala(nom: str) -> None:
    _kesh.pop(nom, None)


def moddalarni_oqi() -> List[dict]:
    """Barcha moddalar. Qaytgan ro'yxat keshdan — uni o'zgartirmang."""
    return _oqi(QONUNLAR_FAYL, "qonunlar")


def versiya() -> str:
    """Baza holatining belgisi. Baza o'zgarsa qiymat ham o'zgaradi —
    javob keshi eskirgan javobni qaytarmasligi uchun ishlatiladi."""
    moddalarni_oqi()
    organlarni_oqi()
    return f"{_kesh['qonunlar'][0]}|{_kesh['organlar'][0]}"


def organlarni_oqi() -> List[dict]:
    return _oqi(ORGANLAR_FAYL, "organlar")


def modda_top(modda_id: str) -> Optional[dict]:
    """id bo'yicha modda — chiziqli qidiruv emas, tayyor indeksdan."""
    moddalarni_oqi()  
    indeks = _kesh["qonunlar"][2] or {}
    return indeks.get(modda_id)


def organ_top(mavzu: str) -> Optional[dict]:
    organlar = organlarni_oqi()
    for o in organlar:
        if o["mavzu"] == mavzu:
            return o
    
    for o in organlar:
        if o["mavzu"] == "umumiy":
            return o
    return None


def modda_qosh_yoki_yangila(yangi: Dict) -> dict:
    """id bo'yicha mavjud bo'lsa yangilaydi, bo'lmasa qo'shadi."""
    with _lock:
        with open(QONUNLAR_FAYL, encoding="utf-8") as f:
            moddalar = json.load(f)
        for i, m in enumerate(moddalar):
            if m["id"] == yangi["id"]:
                moddalar[i] = yangi
                break
        else:
            moddalar.append(yangi)
        with open(QONUNLAR_FAYL, "w", encoding="utf-8") as f:
            json.dump(moddalar, f, ensure_ascii=False, indent=2)
    _keshni_tozala("qonunlar")
    return yangi
